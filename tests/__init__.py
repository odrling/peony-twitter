# -*- coding: utf-8 -*-
""" load the module at the root of the repository """

import asyncio
import inspect
import json
import os.path
import pathlib
import aiofiles
import sys

file_ = pathlib.Path(inspect.getfile(inspect.currentframe()))
test_dir = file_.absolute().parent

sys.path.insert(0, os.path.dirname(str(test_dir)))


class Media:
    cache_dir = test_dir / "cache"

    def __init__(self, filename, mimetype, content_length, category=None,
                 base="https://tests.odrling.xyz/peony/"):
        self.filename = filename
        self.url = base + filename
        self.type = mimetype
        self.category = category
        self.content = b""
        self.content_length = content_length

    @property
    def cache(self):
        return Media.cache_dir / self.filename

    async def download(self, session=None, chunk=-1):
        if self.content:
            if chunk < 0:
                return self.content
            else:
                return self.content[:chunk]

        Media.cache_dir.mkdir(exist_ok=True)

        if self.cache.exists():
            async with aiofiles.open(str(self.cache), mode='rb') as stream:
                self.content = await stream.read()
                if self.content_length == len(self.content):
                    return self.content

        if session is None:
            raise RuntimeError("No session")

        async with session.get(self.url) as response:
            print("downloading", self.filename)
            self.content = await response.read()
            async with aiofiles.open(str(self.cache), mode='wb') as stream:
                await stream.write(self.content)

            return self.content

    def __str__(self):
        return "<Media name={}>".format(self.filename)

    def __repr__(self):
        return str(self)


medias = {
    'lady_peony': Media(
        filename="lady_peony.jpg",
        mimetype="image/jpeg",
        category="tweet_image",
        content_length=302770
    ),
    'pink_queen': Media(
        filename="pink_queen.jpg",
        mimetype="image/jpeg",
        category="tweet_image",
        content_length=62183
    ),
    'bloom': Media(
        filename="bloom.gif",
        mimetype="image/gif",
        category="tweet_gif",
        content_length=503407
    ),
    'video': Media(
        filename="peony.mp4",
        mimetype="video/mp4",
        category="tweet_video",
        content_length=9773437
    ),
    'seismic_waves': Media(
        filename="seismic_waves.png",
        mimetype="image/png",
        category="tweet_image",
        content_length=43262
    )
}


class MockResponse:
    message = "to err is human, to arr is pirate"

    def __init__(self, data=None, error=None,
                 content_type="application/json", headers=None, status=200):

        if error is not None:
            data = json.dumps({'errors': [{'code': error,
                                           'message': self.message}]})

        if isinstance(data, str):
            self.data = data.encode(encoding='utf-8')
        elif isinstance(data, bytes):
            self.data = data
        else:
            self.data = b""
            content_type = "text/plain"

        self.status = status
        self.headers = {} if headers is None else headers

        self.headers['Content-Type'] = content_type
        self.url = ''  # quite irrelevant here
        self._closed = False

    async def read(self):
        return self.data

    async def text(self, encoding=None):
        if encoding is None:
            encoding = 'utf-8'

        return self.data.decode(encoding=encoding)

    async def json(self, encoding=None, loads=json.loads):
        if encoding is None:
            encoding = 'utf-8'

        return loads(self.data, encoding=encoding)

    async def readline(self):
        if self.data:
            if b'\n' in self.data:
                i = self.data.index(b'\n')
                line = self.data[:i + 1]
                self.data = self.data[i + 1:]
            else:
                line = self.data
                self.data = ""

            # needed to test the cancellation of the task
            await asyncio.sleep(0.001)

            return line

        raise StopAsyncIteration

    async def __aenter__(self):
        return self

    async def __aexit__(self):
        pass

    async def release(self):
        pass

    def close(self):
        if self.closed:
            raise RuntimeError

        self._closed = True

    @property
    def closed(self):
        return self._closed

    @property
    def content(self):
        return self


class MockIteratorRequest:
    ids = range(1000)
    kwargs = {}

    def __init__(self, since_id=None,
                 max_id=None,
                 cursor=None,
                 count=10):
        self.since_id = since_id
        self.max_id = max_id
        self.cursor = cursor
        self.count = count

    def __await__(self):
        return self.request().__await__()

    def __call__(self, **kwargs):
        return MockIteratorRequest(**kwargs)

    async def request(self):
        since_id = self.since_id
        max_id = self.max_id
        cursor = self.cursor
        count = self.count

        if max_id is not None:
            if max_id < 0:
                return []

            max_id = min(max_id, len(self.ids) - 1)

            end = max_id - self.count
            if since_id is not None and end < self.since_id:
                end = since_id

            if end < 0:
                return [{'id': i} for i in self.ids[max_id::-1]]
            else:
                return [{'id': i} for i in self.ids[max_id:end:-1]]

        elif cursor is not None:
            if cursor == -1:
                cursor = 0

            next_cursor = cursor + count
            if next_cursor >= len(self.ids):
                next_cursor = 0

            return {'ids': self.ids[cursor:cursor + count],
                    'next_cursor': next_cursor}

        else:
            last_chunk_start = len(self.ids) - count
            if since_id is None or since_id < last_chunk_start:
                return [{'id': i} for i in
                        self.ids[:len(self.ids) - count - 1:-1]]
            else:
                return [{'id': i} for i in self.ids[:since_id:-1]]


class Data:

    def __init__(self, data):
        self._data = data

    async def data(self):
        return self._data

    def __call__(self, *args, **kwargs):
        return self.data()


async def dummy(*args, future=None, **kwargs):
    if future is not None:
        future.set_result(None)


def async_test(func):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(func())


if sys.version_info < (3, 5, 2):
    def create_future(loop):
        return asyncio.Future(loop=loop)
else:
    def create_future(loop):
        return loop.create_future()
