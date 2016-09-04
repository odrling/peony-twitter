# -*- coding: utf-8 -*-

import asyncio
import json
import sys

import aiohttp

from . import exceptions, utils
from .exceptions import PeonyException, StreamLimit
from .general import rate_limit_notices


class StreamResponse:
    """
        Asynchronous iterator for streams
    """

    def __init__(self, *args, _headers,
                 session=None,
                 reconnect=150,
                 loads=utils.loads,
                 timeout=90,
                 _error_handler=None,
                 **kwargs):
        """ keep the arguments as instance attributes """
        self.session = session or aiohttp.ClientSession()
        self.reconnect = reconnect
        self.headers = _headers
        self.loads = loads
        self.timeout = timeout
        self.error_handler = _error_handler
        self.args = args
        self.kwargs = kwargs

    async def __aiter__(self):
        """ create the connection """
        kwargs = self.headers.prepare_request(**self.kwargs)
        request = self.error_handler(self.session.request)

        self.response = await request(*self.args, **kwargs)
        if self.response.status == 200:
            return self
        else:
            try:
                await exceptions.throw(self.response)
            except PeonyException as e:
                print(e, file=sys.stderr)
                if self.reconnect:
                    await self.restart_stream(error=e)

    async def __anext__(self):
        """ decode each line using json """
        line = b''
        try:
            while not line:
                coro = self.response.content.__aiter__().__anext__()
                line = await asyncio.wait_for(coro, self.timeout)
                line = line.rstrip(b'\r\n')

            if line in rate_limit_notices:
                raise StreamLimit(line)

            return self.loads(line)

        except StreamLimit as error:
            print("Error:", line, file=sys.stderr)
            return await self.restart_stream(error=error)

        except StopAsyncIteration as error:
            print("Stream stopped", file=sys.stderr)
            return await self.restart_stream(error=error)

        except json.decoder.JSONDecodeError as error:
            print("Decode error:", line, file=sys.stderr)
            return await self.restart_stream(error=error)

        except asyncio.TimeoutError as error:
            print("Timeout reached", file=sys.stderr)
            return await self.restart_stream(reconnect=0, error=error)

        except GeneratorExit:
            self.response.close()
            self.session.close()

        except KeyboardInterrupt:
            self.response.close()
            self.session.close()

        except Exception as e:
            str(e) and print(e, file=sys.stderr)
            self.response.close()
            self.session.close()
            raise

    async def restart_stream(self, reconnect=None, error=None):
        """ restart the stream on error """

        if error is not None:
            print(error, file=sys.stderr)

        reconnect = reconnect is None and self.reconnect or reconnect

        try:
            self.response.close()
        except Exception as e:
            print(e, file=sys.stderr)

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
    """ A context that should close the session on exit """

    def __init__(self, method, url, *args, **kwargs):
        """ keep the arguments as instance attributes """
        self.method = method
        self.url = url
        self.args = args
        self.kwargs = kwargs

    async def __aenter__(self):
        """ create stream and return it """
        self.stream = StreamResponse(method=self.method,
                                     url=self.url,
                                     *self.args, **self.kwargs)

        return self.stream

    async def __aexit__(self, *args, **kwargs):
        """ close the response and the session """
        if hasattr(self.stream, "response"):
            self.stream.response.close()
        if hasattr(self.stream, "session"):
            self.stream.session.close()

        return True
