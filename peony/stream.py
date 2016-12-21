# -*- coding: utf-8 -*-

import asyncio
from pprint import pprint

import aiohttp

from . import exceptions, utils
from .exceptions import StreamLimit, EnhanceYourCalm
from .general import rate_limit_notices


class StreamResponse:
    """
        Asynchronous iterator for streams

    Parameters
    ----------
    *args : optional
        Positional arguments
    _headers : dict
        Headers to authorize the request
    session : :obj:`aiohttp.Session`, optional
        Session used by the request
    reconnect : :obj:`int`, optional
        Time to wait for on error
    loads : function, optional
        function used to decode the JSON data received
    timeout : :obj:`int`, optional
        Timeout for requests
    _timeout : :obj:`int`, optional
        Stream timeout, the connection will be closed if this timeout
        is exceeded
    _error_handler : function, optional
        Request's error handler
    **kwargs
        Keyword parameters of the request
    """

    def __init__(self, *args,
                 client,
                 session,
                 reconnect=150,
                 loads=utils.loads,
                 timeout=10,
                 _timeout=90,
                 **kwargs):

        self.client = client
        self.session = session
        self.reconnect = reconnect
        self.loads = loads
        self.timeout = timeout
        self._timeout = _timeout
        self.args = args
        self.kwargs = kwargs
        self.reconnecting = False

    async def connect(self):
        """
            Connect to the stream

        Returns
        -------
        aiohttp.StreamReader
            The streaming response
        """
        kwargs = self.client.headers.prepare_request(**self.kwargs)
        request = self.client.error_handler(self.session.request)

        return await request(*self.args, timeout=self.timeout, **kwargs)

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
        self.response = await self.connect()
        if self.response.status == 200:
            return self
        else:
            try:
                raise await exceptions.throw(self.response)
            except EnhanceYourCalm as e:
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
            if self.response.status != 200:
                raise await exceptions.throw(self.response)

            if self.reconnecting:
                return await self.restart_stream()

            while not line:
                with aiohttp.Timeout(self._timeout):
                    line = await self.response.content.readline()
                    line = line.rstrip(b'\r\n')

            if line in rate_limit_notices:
                raise StreamLimit(line)

            return self.loads(line)

        except asyncio.TimeoutError:
            return await self.restart_stream(reconnect=0)

        except aiohttp.errors.ContentEncodingError:
            return await self.restart_stream(reconnect=0)

        except Exception as e:
            return await self.restart_stream(error=e)

    async def restart_stream(self, reconnect=None, error=None):
        """
            Restart the stream on error

        Parameters
        ----------
        reconnect : :obj:`int`, optional
            Time to wait for before reconnecting
        error : :class:`Exception`, optional
            Whether to print the error or not
        """

        reconnect = self.reconnect if (reconnect is None) else reconnect

        self.response.close()

        if reconnect is not None:
            if reconnect > 0 and self.reconnecting is False:
                if error:
                    utils.print_error()

                self.reconnecting = reconnect
                return {
                    'reconnecting_in': reconnect,
                    'error': error
                }
            else:
                await asyncio.sleep(self.reconnecting)
                await self.__aiter__()
                self.reconnecting = False
                return {'stream_restart': True}
        else:
            raise


class StreamContext:
    """
        A context that should close the session on exit

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
            Close the response and the session on error
        """

        if hasattr(self.stream, "response"):
            self.stream.response.close()
