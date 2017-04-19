# -*- coding: utf-8 -*-

import json
from time import time

import pytest

from peony import exceptions
from . import MockResponse


@pytest.mark.asyncio
async def test_errors():
    # twitter errors
    for code, error in exceptions.errors.items():
        with pytest.raises(error):
            response = MockResponse(error=code)
            await exceptions.throw(response)

    # status code exceptions
    for status, exception in exceptions.statuses.items():
        with pytest.raises(exception):
            response = MockResponse(data=b"",
                                    content_type="application/octet-stream",
                                    status=status)
            await exceptions.throw(response)


@pytest.mark.asyncio
async def test_error():
    with pytest.raises(exceptions.errors[32]):
        data = json.dumps({'error': {'code': 32,
                                     'message': MockResponse.message}})
        response = MockResponse(data=data)
        await exceptions.throw(response)


@pytest.mark.asyncio
async def test_unicode_decode_error():
    with pytest.raises(exceptions.PeonyException):
        response = MockResponse(b"\x80")
        await exceptions.throw(response)


@pytest.mark.asyncio
async def test_json_decode_error():
    with pytest.raises(exceptions.PeonyException):
        response = MockResponse(b"{")
        await exceptions.throw(response)


@pytest.mark.asyncio
async def test_rate_limit():
    try:
        headers = {'X-Rate-Limit-Reset': time() + 50}
        response = MockResponse(error=88, headers=headers)
        await exceptions.throw(response)
    except exceptions.RateLimitExceeded as e:
        assert e.reset - time() == pytest.approx(e.reset_in)
