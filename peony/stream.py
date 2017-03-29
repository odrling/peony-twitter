# -*- coding: utf-8 -*-

import asyncio
import sys

import aiohttp

from . import exceptions, utils
from .exceptions import StreamLimit
from .general import rate_limit_notices

if int(aiohttp.__version__.split('.')[0]) < 2:
    ClientPayloadError = aiohttp.errors.ContentEncodingError
    ClientConnectionError = aiohttp.errors.ClientDisconnectedError
else:
    ClientPayloadError = aiohttp.ClientPayloadError
    ClientConnectionError = aiohttp.ClientConnectionError

RECONNECTION_TIMEOUT = 5
MAX_RECONNECTION_TIMEOUT = 320
DISCONNECTION_TIMEOUT = 0.25
MAX_DISCONNECTION_TIMEOUT = 16
ENHANCE_YOUR_CALM_TIMEOUT = 60


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
                 loads=utils.loads,
                 timeout=10,
                 **kwargs):

        self.client = client
        self.session = self.client._session if session is None else session
        self.loads = loads
        self.timeout = timeout
        self.args = args
        self.kwargs = kwargs
        self.reconnecting = False
        self.reconnection = 0
        self.enhance_calm = 0
        self.disconnection = 0

    def connect(self):
        """
            Connect to the stream

        Returns
        -------
        asyncio.coroutine
            The streaming response
        """
        kwargs = self.client.headers.prepare_request(**self.kwargs)
        request = self.client.error_handler(self.session.request)

        if 'proxy' not in kwargs:
            kwargs['proxy'] = self.client.proxy

        return request(*self.args, timeout=0, **kwargs)

    def initialize_timeouts(self):
        self.reconnection = 0
        self.enhance_calm = 0
        self.disconnection = 0

    async def __aiter__(self):
        """
            Create the connection

        Returns
        -------
        self

        Raises
        ------
        exception.PeonyException
            On a response status != 2xx
        """
        with aiohttp.Timeout(self.timeout):
            self.response = await self.connect()

        if self.response.status == 200:
            self.initialize_timeouts()
        elif self.response.status == 500:
            self.increase_disconnetion_timeout()
        elif self.response.status in range(501, 600):
            self.increase_reconnection_timeout()
        elif self.response.status in (420, 429):
            self.increase_enhance_calm_timeout()

            print("Enhance Your Calm response received from Twitter. "
                  "If you didn't restart your program frenetically "
                  "then there is probably something wrong with it. "
                  "Make sure you are not opening too many connections to "
                  "the endpoint you are currently using by checking "
                  "Twitter's Streaming API documentation out: "
                  "https://dev.twitter.com/streaming/overview\n"
                  "The stream will restart in %ss." % self.enhance_calm,
                  file=sys.stderr)
        else:
            raise await exceptions.throw(self.response)

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
            timeouts = self.disconnection, self.reconnection, self.enhance_calm
            reconnect = max(timeouts)

            if self.reconnecting is not False:
                return await self.restart_stream()
            elif reconnect:
                return await self.initialize_restart(reconnect=reconnect)

            while not line:
                with aiohttp.Timeout(90):
                    line = await self.response.content.readline()
                    line = line.rstrip(b'\r\n')

            if line in rate_limit_notices:
                raise StreamLimit(line)

            return self.loads(line)

        except asyncio.TimeoutError:
            return await self.initialize_restart()

        except ClientPayloadError:
            return await self.initialize_restart()

        except ClientConnectionError:
            self.increase_disconnetion_timeout()
            return await self.initialize_restart(reconnect=self.disconnection)

        except Exception as e:
            return await self.initialize_restart(error=e)

    def increase_disconnetion_timeout(self):
        if not self.disconnection >= MAX_DISCONNECTION_TIMEOUT:
            self.disconnection += DISCONNECTION_TIMEOUT

    def increase_reconnection_timeout(self):
        if self.reconnection == 0:
            self.reconnection = RECONNECTION_TIMEOUT
        elif not self.reconnection >= MAX_RECONNECTION_TIMEOUT:
            self.reconnection *= 2

    def increase_enhance_calm_timeout(self):
        if self.enhance_calm == 0:
            self.enhance_calm = ENHANCE_YOUR_CALM_TIMEOUT
        else:
            self.enhance_calm *= 2

    async def initialize_restart(self, reconnect=0, error=None):
        """
            Restart the stream on error

        Parameters
        ----------
        reconnect : :obj:`int`, optional
            Time to wait for before reconnecting
        error : :class:`Exception`, optional
            Whether to print the error or not
        """
        if reconnect is not None:
            if error:
                utils.print_error()

            self.reconnecting = reconnect
            return {
                'reconnecting_in': reconnect,
                'error': error
            }
        else:
            if error is not None:
                raise error

    async def restart_stream(self):
        """
            Restart the stream on error
        """
        await self.response.release()
        await asyncio.sleep(self.reconnecting)
        await self.__aiter__()
        self.reconnecting = False
        return {'stream_restart': True}


class StreamContext:
    """
        A context that should close the request on exit

    Parameters
    ----------
    method : str
        HTTP method used to make the request
    url : str
        The API endpoint
    *args : optional
        Positional arguments
    **kwargs
        Keyword parameters of the request and of :class:`StreamResponse`
    """

    def __init__(self, method, url, client, *args, **kwargs):
        self.method = method
        self.url = url
        self.client = client
        self.args = args
        self.kwargs = kwargs

    async def __aenter__(self):
        """
            Create stream

        Returns
        -------
        StreamResponse
            The stream iterator
        """
        await self.client.setup()
        self.stream = StreamResponse(method=self.method, url=self.url,
                                     *self.args, client=self.client,
                                     **self.kwargs)

        return self.stream

    async def __aexit__(self, *args, **kwargs):
        """
            Close the response on error
        """

        if hasattr(self.stream, "response"):
            self.stream.response.close()
