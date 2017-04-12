# -*- coding: utf-8 -*-

import asyncio
import json
from time import time

import pytest

from peony import exceptions

loop = asyncio.get_event_loop()
message = "to err is human, to arr is pirate"


class MockResponse:

    def __init__(self, data=None, error=None,
                 content_type="application/json", headers=None, status=200):

        if error is not None:
            data = json.dumps({'errors': [{'code': error,
                                           'message': message}]})

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


def test_errors():
    # twitter errors
    for code, error in exceptions.errors.items():
        with pytest.raises(error):
            response = MockResponse(error=code)
            loop.run_until_complete(exceptions.throw(response))

    # status code exceptions
    for status, exception in exceptions.statuses.items():
        with pytest.raises(exception):
            response = MockResponse(data=b"",
                                    content_type="application/octet-stream",
                                    status=status)
            loop.run_until_complete(exceptions.throw(response))


def test_error():
    with pytest.raises(exceptions.errors[32]):
        data = json.dumps({'error': {'code': 32, 'message': message}})
        response = MockResponse(data=data)
        loop.run_until_complete(exceptions.throw(response))


def test_unicode_decode_error():
    with pytest.raises(exceptions.PeonyException):
        response = MockResponse(b"\x80")
        loop.run_until_complete(exceptions.throw(response))


def test_json_decode_error():
    with pytest.raises(exceptions.PeonyException):
        response = MockResponse(b"{")
        loop.run_until_complete(exceptions.throw(response))


def test_rate_limit():
    try:
        headers = {'X-Rate-Limit-Reset': time() + 50}
        response = MockResponse(error=88, headers=headers)
        loop.run_until_complete(exceptions.throw(response))
    except exceptions.RateLimitExceeded as e:
        assert e.reset - time() == pytest.approx(e.reset_in)
