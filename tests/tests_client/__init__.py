import functools
from unittest import mock

import aiohttp
import asyncio
import async_timeout

from peony import BasePeonyClient, PeonyClient
from .. import MockResponse


class MockSessionRequest:

    def __init__(self, status=200, data=MockResponse.message,
                 content_type="plain/text"):
        self.status = status
        self.data = data
        self.ctype = content_type

    async def __aenter__(self, *args, **kwargs):
        return MockResponse(status=self.status, data=self.data,
                            content_type=self.ctype)

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    def __call__(self, *args, **kwargs):
        return self


class MockSession:

    def __init__(self, request=None):
        if request is None:
            self.request = MockSessionRequest()
        else:
            self.request = request


def dummy_error_handler(request):

    @functools.wraps(request)
    async def decorated_request(url=None, **kwargs):
        async with async_timeout.timeout(2):
            return await request(url=url, **kwargs)

    return decorated_request


class DummyClient(BasePeonyClient):

    def __init__(self, *args, **kwargs):
        super().__init__("", "", error_handler=dummy_error_handler,
                         *args, **kwargs)

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        self.patch = mock.patch.object(self.session, 'request')
        self.patch.__enter__()

        return await super().__aenter__()

    async def __aexit__(self, *args):
        await super().__aexit__(*args)
        self.patch.__exit__()


class DummyPeonyClient(DummyClient, PeonyClient):
    pass


class TaskContext:

    def __init__(self, coro):
        self.coro = coro

    async def __aenter__(self):
        self.task = asyncio.get_event_loop().create_task(self.coro)
        return self.task

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if not self.task.done():
            self.task.cancel()
            try:
                await self.task
            except:
                pass
