# -*- coding: utf-8 -*-

import asyncio
import json

import aiohttp

from . import utils
from .exceptions import StreamLimit, PeonyException
from .general import rate_limit_notices


class StreamResponse:
    """
        Asynchronous iterator for streams
    """

    def __init__(self, *args, _headers,
                 session=None,
                 reconnect=150,
                 loads=utils.loads,
                 **kwargs):
        """ keep the arguments as instance attributes """
        self.session = session or aiohttp.ClientSession()
        self.reconnect = reconnect
        self.headers = _headers
        self.args = args
        self.kwargs = kwargs
        self.loads = loads

    async def __aiter__(self):
        """ create the connection """
        kwargs = self.headers.prepare_request(**self.kwargs)
        print(kwargs)

        self.response = await self.session.request(*self.args, **kwargs)
        if self.response.status == 200:
            return self
        else:
            try:
                raise await utils.throw(self.response)
            except PeonyException as e:
                if self.reconnect:
                    await self.restartStream(error=e)

    async def __anext__(self):
        """ decode each line using json """
        try:
            line = b''

            while not line:
                line = await self.response.content.__aiter__().__anext__()
                line = line.rstrip(b'\r\n')

            if line in rate_limit_notices:
                raise StreamLimit(line)

            return self.loads(line)

        except StreamLimit as error:
            print("Error:", line)
            return await self.restartStream(error=error)

        except StopAsyncIteration as error:
            print("Stream stopped")
            return await self.restartStream(error=error)

        except json.decoder.JSONDecodeError as error:
            print("Decode error:", line)
            return await self.restartStream(error=error)

        except GeneratorExit:
            await self.response.release()
            self.session.close()

        except KeyboardInterrupt:
            await self.response.release()
            self.session.close()

        except Exception as e:
            str(e) and print(e)
            await self.response.release()
            self.session.close()
            raise

    async def restartStream(self, reconnect=None, error=None):
        """ restart the stream on error """

        if error:
            print(error)

        await self.response.release()

        if reconnect or self.reconnect:
            print("restarting stream in %ss" % (reconnect or self.reconnect))
            await asyncio.sleep(reconnect or self.reconnect)
            print("restarting stream")
            await self.__aiter__()
            return await self.__anext__()
        else:
            raise error


class StreamContext:
    """ A context that should close the session on exit """

    def __init__(self, *args, **kwargs):
        """ keep the arguments as instance attributes """
        self.args = args
        self.kwargs = kwargs

    async def __aenter__(self):
        """ create stream and return it """
        self.stream = StreamResponse(*self.args, **self.kwargs)

        return self.stream

    async def __aexit__(self, *args, **kwargs):
        """ release the response and close the session """

        if hasattr(self.stream, "response"):
            await self.stream.response.release()
        if hasattr(self.stream, "session"):
            self.stream.session.close()

        return True
