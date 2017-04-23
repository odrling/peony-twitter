
import os

import pytest
from peony import BasePeonyClient, oauth

oauth2_keys = 'PEONY_CONSUMER_KEY', 'PEONY_CONSUMER_SECRET'
oauth2 = all(key in os.environ for key in oauth2_keys)

creds_keys = 'consumer_key', 'consumer_secret'


def oauth2_decorator(func):
    decorator = pytest.mark.asyncio(
        pytest.mark.skipif(not oauth2, reason="no credentials found")
    )

    return decorator(func)


def get_oauth2_client(**kwargs):
    creds = {creds_keys[i]: os.environ[oauth2_keys[i]] for i in range(2)}
    return BasePeonyClient(**creds, auth=oauth.OAuth2Headers, **kwargs)


@pytest.fixture
def oauth2_client(event_loop):
    if oauth2:
        return get_oauth2_client(loop=event_loop)


@oauth2_decorator
async def test_oauth2_get_token(oauth2_client):
    if 'Authorization' in oauth2_client.headers:
        del oauth2_client.headers['Authorization']

    await oauth2_client.headers.sign()


@oauth2_decorator
async def test_oauth2_request(oauth2_client):
    await oauth2_client.api.search.tweets.get(q="@twitter hello :)")


@oauth2_decorator
async def test_oauth2_invalidate_token(oauth2_client):
    await oauth2_client.headers.sign()  # make sure there is a token
    await oauth2_client.headers.invalidate_token()


@oauth2_decorator
async def test_oauth2_bearer_token(oauth2_client, event_loop):
    await oauth2_client.headers.sign()

    auth = 'Authorization'
    token = oauth2_client.headers[auth][len("Bearer "):]

    client = get_oauth2_client(loop=event_loop, bearer_token=token)
    assert client.headers[auth] == oauth2_client.headers[auth]
