# -*- coding: utf-8 -*-

import asyncio
import sys
from concurrent.futures import CancelledError

import aiohttp

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

HandledErrors = asyncio.TimeoutError, ClientPayloadError, TimeoutError


class StreamResponse:
    """
        Asynchronous iterator for streams

    Parameters
    ----------
    *args : optional
        Positional arguments
    client : peony.BasePeonyClient
        client used to make the request
    session : :obj:`aiohttp.Session`, optional
        Session used by the request
    loads : function, optional
        function used to decode the JSON data received
    timeout : :obj:`int`, optional
        Timeout on connection
    **kwargs
        Keyword parameters of the request
    """

    def __init__(self, *args,
                 client,
                 session=None,
                 loads=data_processing.loads,
                 timeout=10,
                 **kwargs):

        self.client = client
        self.session = self.client._session if session is None else session
        self.loads = loads
        self.timeout = timeout
        self.args = args
        self.kwargs = kwargs

        self.response = None
        self._reconnecting = False
        self._state = NORMAL
        self._error_timeout = 0

    async def connect(self):
        """
            Connect to the stream

        Returns
        -------
        asyncio.coroutine
            The streaming response
        """
        await self.client.setup()
        kwargs = await self.client.headers.prepare_request(**self.kwargs)
        request = self.client.error_handler(self.session.request)

        return await request(*self.args, timeout=0, **kwargs)

    async def __aiter__(self):
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
        with aiohttp.Timeout(self.timeout):
            self.response = await self.connect()

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
            raise await exceptions.throw(self.response,
                                         loads=self.client._loads)

        return self

    async def __anext__(self):
        """
            Decode each line using json

        Returns
        -------
        dict
            Decoded JSON data
        """
        line = b''
        try:
            if self.state != NORMAL:
                if self._reconnecting:
                    return await self.restart_stream()
                else:
                    return await self.init_restart()

            while not line:
                with aiohttp.Timeout(90):
                    line = await self.response.content.readline()
                    line = line.strip(b'\r\n')

            if line in rate_limit_notices:
                raise StreamLimit(line)

            return self.loads(line)

        except HandledErrors:
            self.state = ERROR
            return await self.init_restart()

        except ClientConnectionError:
            self.state = DISCONNECTION
            return await self.init_restart()

        except CancelledError:
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
        error : :obj:`bool`, optional
            Whether to print the error or not
        """

        if error:
            print(error.__class__)
            utils.log_error()

        if self.state == DISCONNECTION:
            if self._error_timeout < MAX_DISCONNECTION_TIMEOUT:
                self._error_timeout += DISCONNECTION_TIMEOUT

        elif self.state == RECONNECTION:
            if self._error_timeout < RECONNECTION_TIMEOUT:
                self._error_timeout = RECONNECTION_TIMEOUT
            elif self._error_timeout < MAX_RECONNECTION_TIMEOUT:
                self._error_timeout *= 2

        elif self.state == ENHANCE_YOUR_CALM:
            if self._error_timeout < ENHANCE_YOUR_CALM_TIMEOUT:
                self._error_timeout = ENHANCE_YOUR_CALM_TIMEOUT
            else:
                self._error_timeout *= 2

            print("Enhance Your Calm response received from Twitter. "
                  "If you didn't restart your program frenetically "
                  "then there is probably something wrong with it. "
                  "Make sure you are not opening too many connections to "
                  "the endpoint you are currently using by checking "
                  "Twitter's Streaming API documentation out: "
                  "https://dev.twitter.com/streaming/overview\n"
                  "The stream will restart in %ss." % self._error_timeout,
                  file=sys.stderr)
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
        await self.__aiter__()

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
        await self.client.setup()
        return self

    def __exit__(self, *args):
        """ Close the response on error """
        if getattr(self, 'response', None) is not None:
            if not self.response.closed:
                self.response.close()

    async def __aexit__(self, *args):
        """ Close the response on error """
        self.__exit__(*args)
