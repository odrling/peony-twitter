# -*- coding: utf-8 -*-

import asyncio
import logging
import sys

import aiohttp
import async_timeout

if sys.version_info < (3, 8):  # pragma: no cover
    from concurrent.futures import CancelledError
else:
    from asyncio.exceptions import CancelledError

from . import data_processing, exceptions, utils
from .exceptions import StreamLimit
from .general import rate_limit_notices

ClientPayloadError = aiohttp.ClientPayloadError
ClientConnectionError = aiohttp.ClientConnectionError

RECONNECTION_TIMEOUT = 5
MAX_RECONNECTION_TIMEOUT = 320
DISCONNECTION_TIMEOUT = 0.25
ERROR_TIMEOUT = DISCONNECTION_TIMEOUT
MAX_DISCONNECTION_TIMEOUT = 16
ENHANCE_YOUR_CALM_TIMEOUT = 60

NORMAL = 0
DISCONNECTION = 1
ERROR = DISCONNECTION
RECONNECTION = 2
ENHANCE_YOUR_CALM = 3
EOF = 4

HandledErrors = asyncio.TimeoutError, ClientPayloadError, TimeoutError

logger = logging.getLogger(__name__)


class StreamResponse:
    """
        Asynchronous iterator for streams

    Parameters
    ----------
    *args : list, optional
        Positional arguments of the request
    client : .client.BasePeonyClient
        client used to make the request
    session : aiohttp.ClientSession, optional
        Session used by the request
    loads : function, optional
        function used to decode the JSON data received
    timeout : int, optional
        Timeout on connection
    kwargs : dict, optional
        Keyword parameters of the request
    """

    def __init__(self,
                 client,
                 session=None,
                 loads=data_processing.loads,
                 timeout=10,
                 **kwargs):

        self.client = client
        self.session = session
        self.loads = loads
        self.timeout = timeout
        self.kwargs = kwargs

        self.response = None
        self._reconnecting = False
        self._state = NORMAL
        self._error_timeout = 0

    async def _connect(self):
        """
            Connect to the stream

        Returns
        -------
        asyncio.coroutine
            The streaming response
        """
        logger.debug("connecting to the stream")
        await self.client.setup
        if self.session is None:
            self.session = self.client._session
        kwargs = await self.client.headers.prepare_request(**self.kwargs)
        request = self.client.error_handler(self.session.request)

        return await request(timeout=0, **kwargs)

    async def connect(self):
        """
            Create the connection

        Returns
        -------
        self

        Raises
        ------
        exception.PeonyException
            On a response status in 4xx that are not status 420 or 429
            Also on statuses in 1xx or 3xx since this should not be the status
            received here
        """
        with async_timeout.timeout(self.timeout):
            self.response = await self._connect()

        if self.response.status in range(200, 300):
            self._error_timeout = 0
            self.state = NORMAL
        elif self.response.status == 500:
            self.state = DISCONNECTION
        elif self.response.status in range(501, 600):
            self.state = RECONNECTION
        elif self.response.status in (420, 429):
            self.state = ENHANCE_YOUR_CALM
        else:
            logger.debug("raising error during stream connection")
            raise await exceptions.throw(self.response,
                                         loads=self.client._loads,
                                         url=self.kwargs['url'])

        logger.debug("stream state: %d" % self.state)

    def __aiter__(self):
        return self

    if sys.version_info < (3, 5, 2):  # pragma: no cover
        __aiter__ = asyncio.coroutine(__aiter__)

    async def __anext__(self):
        """
            Decode each line using json

        Returns
        -------
        dict
            Decoded JSON data
        """
        if self.response is None:
            logger.info("first connection to the stream")
            await self.connect()
            return {'connected': True}

        line = b''
        try:
            if self.state != NORMAL:
                if self._reconnecting:
                    return await self.restart_stream()
                else:
                    return await self.init_restart()

            while not line:
                if self.response.content.at_eof():
                    logger.debug("Received EOF")
                    self.state = EOF
                    return await self.init_restart()

                with async_timeout.timeout(90):
                    line = await self.response.content.readline()
                    line = line.strip(b'\r\n')
                    logger.debug("received data: %s" % line)

            if line in rate_limit_notices:
                logger.debug("raising StreamLimit")
                raise StreamLimit(line)

            logger.debug("decoding data")
            return self.loads(line)

        except HandledErrors as e:
            logger.debug("handling error %s: %s" % (e.__class__.__name__, e))
            self.state = ERROR
            return await self.init_restart()

        except ClientConnectionError:
            logger.debug("Disconnected from stream")
            self.state = DISCONNECTION
            return await self.init_restart()

        except CancelledError:
            logger.debug("Stopping stream")
            raise

        except Exception as e:
            self.state = ERROR
            return await self.init_restart(error=e)

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, value):
        if value == NORMAL or self.state < value:
            self._state = value

    async def init_restart(self, error=None):
        """
            Restart the stream on error

        Parameters
        ----------
        error : bool, optional
            Whether to print the error or not
        """
        if error:
            utils.log_error(logger=logger)

        if self.state == DISCONNECTION:
            if self._error_timeout < MAX_DISCONNECTION_TIMEOUT:
                self._error_timeout += DISCONNECTION_TIMEOUT

            logger.info("The stream was disconnected, will reconnect in %ss"
                        % self._error_timeout)

        elif self.state == RECONNECTION:
            if self._error_timeout < RECONNECTION_TIMEOUT:
                self._error_timeout = RECONNECTION_TIMEOUT
            elif self._error_timeout < MAX_RECONNECTION_TIMEOUT:
                self._error_timeout *= 2

            logger.info("Could not connect to the stream, reconnection in %ss"
                        % self._error_timeout)

        elif self.state == ENHANCE_YOUR_CALM:
            if self._error_timeout < ENHANCE_YOUR_CALM_TIMEOUT:
                self._error_timeout = ENHANCE_YOUR_CALM_TIMEOUT
            else:
                self._error_timeout *= 2

            logger.warning("Enhance Your Calm response received from Twitter. "
                           "If you didn't restart your program frenetically "
                           "then there is probably something wrong with it. "
                           "Make sure you are not opening too many connections"
                           " to the endpoint you are currently using by "
                           "checking out Twitter's Streaming API "
                           "documentation: "
                           "https://dev.twitter.com/streaming/overview\n"
                           "The stream will restart in %ss."
                           % self._error_timeout)
        elif self.state == EOF:
            pass  # no timeout
        else:
            raise RuntimeError("Incorrect state: %d" % self.state)

        self._reconnecting = True
        return {'reconnecting_in': self._error_timeout, 'error': error}

    async def restart_stream(self):
        """
            Restart the stream on error
        """
        await self.response.release()
        await asyncio.sleep(self._error_timeout)
        await self.connect()

        logger.info("Reconnected to the stream")
        self._reconnecting = False
        return {'stream_restart': True}

    def __enter__(self):
        """
            Prepare the stream

        Returns
        -------
        StreamResponse
            The stream iterator
        """
        return self

    async def __aenter__(self):
        """
            Prepare the stream

        Returns
        -------
        StreamResponse
            The stream iterator
        """
        await self.client.setup
        return self

    def __exit__(self, *args):
        """ Close the response on error """
        if getattr(self, 'response', None) is not None:
            if not self.response.closed:
                logger.debug("Closing the stream")
                self.response.close()

    async def __aexit__(self, *args):
        """ Close the response on error """
        self.__exit__(*args)
