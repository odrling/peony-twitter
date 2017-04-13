# -*- coding: utf-8 -*-
""" load the module at the root of the repository """

import inspect
import json
import os.path
import sys

file_ = os.path.abspath(inspect.getfile(inspect.currentframe()))
test_dir = os.path.dirname(file_)

sys.path.insert(0, os.path.dirname(test_dir))


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
            # well that would be funny if it happened
            raise TypeError("Could not create mock response. "
                            "Wrong data type %s" % type(data))

        self.status = status
        if headers is None:
            self.headers = {}
        else:
            self.headers = headers

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


class MockRequest():

    def __init__(self, ids=range(1000)):
        self.ids = ids

    async def __call__(self, since_id=None, max_id=None, cursor=None, count=10):
        if max_id is not None:
            if max_id < 0:
                return []

            max_id = min(max_id, len(self.ids)-1)

            end = max_id-count
            if since_id is not None and end < since_id:
                end = since_id

            if end < 0:
                return [{'id': i} for i in self.ids[max_id::-1]]
            else:
                return [{'id': i} for i in self.ids[max_id:end:-1]]

        elif cursor is not None:
            if cursor == -1:
                cursor = 0

            next_cursor = cursor+count
            if next_cursor >= len(self.ids):
                next_cursor = 0

            return {'ids': self.ids[cursor:cursor+count],
                    'next_cursor': next_cursor}

        else:
            if since_id is None or since_id < len(self.ids) - count:
                return [{'id': i} for i in
                        self.ids[:len(self.ids) - count - 1:-1]]
            else:
                return [{'id': i} for i in self.ids[:since_id:-1]]
