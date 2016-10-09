# -*- coding: utf-8 -*-

import asyncio
import json

import aiohttp

from . import exceptions, utils
from .exceptions import PeonyException, StreamLimit
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

    def __init__(self, *args, _headers,
                 session=None,
                 reconnect=150,
                 loads=utils.loads,
                 timeout=10,
                 _timeout=90,
                 _error_handler=None,
                 **kwargs):

        self.session = session or aiohttp.ClientSession()
        self.reconnect = reconnect
        self.headers = _headers
        self.loads = loads
        self.timeout = timeout
        self._timeout = _timeout
        self.error_handler = _error_handler
        self.args = args
        self.kwargs = kwargs

    async def connect(self):
        """
            Connect to the stream

        Returns
        -------
        aiohttp.StreamReader
            The streaming response
        """
        kwargs = self.headers.prepare_request(**self.kwargs)
        request = self.error_handler(self.session.request)

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
                await exceptions.throw(self.response)
            except PeonyException as e:
                utils.print_error()
                if self.reconnect:
                    await self.restart_stream(error=e)

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
            while not line:
                with aiohttp.Timeout(self._timeout):
                    line = await self.response.content.__aiter__().__anext__()
                    line = line.rstrip(b'\r\n')

            if line in rate_limit_notices:
                raise StreamLimit(line)

            return self.loads(line)

        except StreamLimit:
            return await self.restart_stream(error=True)

        except StopAsyncIteration:
            return await self.restart_stream(error=True)

        except json.decoder.JSONDecodeError:
            return await self.restart_stream(error=True)

        except asyncio.TimeoutError:
            return await self.restart_stream(reconnect=0, error=True)

        except aiohttp.errors.ContentEncodingError:
            return await self.restart_stream(reconnect=0, error=True)

    async def restart_stream(self, reconnect=None, error=None):
        """
            Restart the stream on error

        Parameters
        ----------
        reconnect : :obj:`int`, optional
            Time to wait for before reconnecting
        error : bool
            Whether to print the error or not
        """

        if error is not None:
            utils.print_error()

        reconnect = reconnect is None and self.reconnect or reconnect

        self.response.close()

        if reconnect is not None:
            if reconnect > 0:
                print("restarting stream in %ss" % reconnect)
                await asyncio.sleep(reconnect)

            print("restarting stream")
            await self.__aiter__()
            return await self.__anext__()
        else:
            raise error


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

    def __init__(self, method, url, *args, **kwargs):
        self.method = method
        self.url = url
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
        self.stream = StreamResponse(method=self.method, url=self.url,
                                     *self.args, **self.kwargs)

        return self.stream

    async def __aexit__(self, *args, **kwargs):
        """
            Close the response and the session on error
        """

        if hasattr(self.stream, "response"):
            self.stream.response.close()
        if hasattr(self.stream, "session"):
            self.stream.session.close()
