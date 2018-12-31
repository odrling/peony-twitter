# -*- coding: utf-8 -*-

import asyncio
from unittest.mock import patch

import pytest

from peony import oauth
from tests import dummy
from tests.tests_client import DummyPeonyClient


class RequestTest:

    def __init__(self, expected_url, expected_method):
        self.expected_url = expected_url
        self.expected_method = expected_method

    async def __call__(self, *args, url=None, method=None,
                       future=None, **kwargs):
        assert url == self.expected_url
        assert method == self.expected_method
        future.set_result(True)
        return True


request_test = RequestTest


@pytest.mark.asyncio
async def test_peony_client_get_user():
    async with DummyPeonyClient() as client:
        url = client.api.account.verify_credentials.url()
        request = request_test(url, 'get')

        with patch.object(client, 'request', side_effect=request) as req:
            await client.user
            assert req.called
            assert client.user.done()
            await client.close()


@pytest.mark.asyncio
async def test_peony_client_get_twitter_configuration():
    async with DummyPeonyClient() as client:
        request = request_test(client.api.help.configuration.url(), 'get')

        with patch.object(client, 'request', side_effect=request) as req:
            await client.twitter_configuration
            assert req.called
            assert client.twitter_configuration.done()
            await client.close()


@pytest.mark.asyncio
async def test_peony_client_get_user_oauth2():
    async with DummyPeonyClient(auth=oauth.OAuth2Headers) as client:
        client.request = dummy
        assert not isinstance(client.user, asyncio.Future)


@pytest.mark.asyncio
async def test_peony_client_get_twitter_configuration_oauth2():
    async with DummyPeonyClient(auth=oauth.OAuth2Headers) as client:
        client.headers.token = "token"
        request = request_test(client.api.help.configuration.url(), 'get')

        with patch.object(client, 'request', side_effect=request) as req:
            await client.twitter_configuration
            assert req.called
            assert client.twitter_configuration.done()
            await client.close()
