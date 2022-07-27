# -*- coding: utf-8 -*-

import json
from time import time
from unittest.mock import patch

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
            response = MockResponse(
                data=b"", content_type="application/octet-stream", status=status
            )
            await exceptions.throw(response)


@pytest.mark.asyncio
async def test_error():
    with pytest.raises(exceptions.errors[32]):
        data = json.dumps({"error": {"code": 32, "message": MockResponse.message}})
        response = MockResponse(data=data)
        await exceptions.throw(response)


@pytest.mark.asyncio
async def test_unicode_decode_error():
    with pytest.raises(exceptions.PeonyDecodeError):
        response = MockResponse(b"\x80")
        await exceptions.throw(response)


@pytest.mark.asyncio
async def test_json_decode_error():
    with pytest.raises(exceptions.PeonyDecodeError):
        response = MockResponse(b"{")
        await exceptions.throw(response)


@pytest.mark.asyncio
async def test_rate_limit():
    t = time()

    with patch.object(exceptions, "time", return_value=t):
        try:
            headers = {"X-Rate-Limit-Reset": t + 50}
            response = MockResponse(error=88, headers=headers)
            await exceptions.throw(response)

        except exceptions.RateLimitExceeded as e:
            assert int(t + 50) == e.reset
            assert int(t + 50) == round(t + e.reset_in)

        else:
            pytest.fail("RateLimitExceeded wasn't raised")


@pytest.mark.asyncio
async def test_peony_exception():
    with pytest.raises(exceptions.PeonyException):
        # there is no error 0 this should raise a generic PeonyException
        response = MockResponse(error=0)
        await exceptions.throw(response)


def test_get_error_not_dict():
    assert exceptions.get_error({"error": 1}) is None


def test_custom_peony_exception_message():

    try:
        exceptions.PeonyException(message=MockResponse.message)
    except exceptions.PeonyException as e:
        assert str(e) == MockResponse.message


def test_exception_url():
    try:
        exceptions.PeonyException(
            message=MockResponse.message, url="http://whatever.com"
        )
    except exceptions.PeonyException as e:
        assert e.url == "http://whatever.com"
        assert str(e).endswith(e.url)
