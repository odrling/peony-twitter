# -*- coding: utf-8 -*-
""" load the module at the root of the repository """

import inspect
import json
import os.path
import sys

file_ = os.path.abspath(inspect.getfile(inspect.currentframe()))
test_dir = os.path.dirname(file_)

sys.path.insert(0, os.path.dirname(test_dir))


class Media:

    def __init__(self, filename, mimetype, category, content_length):
        self.filename = filename
        self.url = "http://static.odrling.xyz/peony/tests/" + filename
        self.type = mimetype
        self.category = category
        self.content_length = content_length
        self._accept_bytes_range = None
        self._cache = b""

    async def download(self, session, chunk=-1):
        if self._accept_bytes_range is None:
            async with session.head(self.url) as response:
                accept = response.headers.get('Accept-Ranges', "")
                self._accept_bytes_range = "bytes" in accept

        if 0 <= chunk <= len(self._cache):
            return self._cache[:chunk]

        elif self._accept_bytes_range and self._cache:
            byte_range = "bytes={cached}-{chunk}".format(
                cached=len(self._cache),
                chunk=chunk if chunk > -1 else self.content_length
            )
            headers = {'Range': byte_range}

            async with session.get(self.url, headers=headers) as response:
                self._cache += await response.read()
                return self._cache

        else:
            async with session.get(self.url) as response:
                self._cache = await response.content.read(chunk)
                return self._cache


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

        self.status = status
        self.headers = {} if headers is None else headers

        self.headers['Content-Type'] = content_type
        self.url = ''  # quite irrelevant here

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


class MockIteratorRequest:

    def __init__(self, ids=range(1000)):
        self.ids = ids

    async def __call__(self,
                       since_id=None,
                       max_id=None,
                       cursor=None,
                       count=10):
        if max_id is not None:
            if max_id < 0:
                return []

            max_id = min(max_id, len(self.ids) - 1)

            end = max_id - count
            if since_id is not None and end < since_id:
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
            if since_id is None or since_id < len(self.ids) - count:
                return [{'id': i} for i in
                        self.ids[:len(self.ids) - count - 1:-1]]
            else:
                return [{'id': i} for i in self.ids[:since_id:-1]]
