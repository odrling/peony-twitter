# -*- coding: utf-8 -*-

import asyncio
import json
from time import time

import pytest

from peony import exceptions
from . import MockResponse

loop = asyncio.get_event_loop()


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
        data = json.dumps({'error': {'code': 32,
                                     'message': MockResponse.message}})
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
