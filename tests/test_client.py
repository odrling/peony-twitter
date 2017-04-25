# -*- coding: utf-8 -*-

import os

import peony
import peony.api
import pytest
from peony import BasePeonyClient, oauth
from peony.general import twitter_api_version, twitter_base_api_url

oauth2_keys = 'PEONY_CONSUMER_KEY', 'PEONY_CONSUMER_SECRET'
oauth2 = all(key in os.environ for key in oauth2_keys)

creds_keys = 'consumer_key', 'consumer_secret'
token = None


@pytest.fixture
def dummy_client():
    return peony.BasePeonyClient("", "", loop=False)


def test_create_endpoint(dummy_client):
    base_url = twitter_base_api_url.format(api='api',
                                           version=twitter_api_version)

    client_endpoint = dummy_client.api.test.endpoint.url()
    api = peony.api.APIPath([base_url], '.json', dummy_client)
    assert client_endpoint == api.test.endpoint.url()


def oauth2_decorator(func):

    @pytest.mark.asyncio
    @pytest.mark.skipif(not oauth2, reason="no credentials found")
    async def decorator():
        global token

        client = get_oauth2_client(bearer_token=token)
        await func(client)

        # keep the token for the next test
        token = client.headers.token

    return decorator


def get_oauth2_client(**kwargs):
    creds = {creds_keys[i]: os.environ[oauth2_keys[i]] for i in range(2)}
    return BasePeonyClient(auth=oauth.OAuth2Headers, loop=False,
                           **creds, **kwargs)


@pytest.fixture
def oauth2_client(event_loop):
    if oauth2:
        return get_oauth2_client(loop=event_loop)


@oauth2_decorator
async def test_oauth2_get_token(client):
    if 'Authorization' in client.headers:
        del client.headers['Authorization']

    await client.headers.sign()


@oauth2_decorator
async def test_oauth2_request(client):
    await client.api.search.tweets.get(q="@twitter hello :)")


@oauth2_decorator
async def test_oauth2_invalidate_token(client):
    await client.headers.sign()  # make sure there is a token
    await client.headers.invalidate_token()
    assert client.headers.token is None


@oauth2_decorator
async def test_oauth2_bearer_token(client):
    await client.headers.sign()

    token = client.headers.token

    client2 = get_oauth2_client(bearer_token=token)
    assert client2.headers.token == client.headers.token
