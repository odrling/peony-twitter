
import os
import time

import aiohttp
import pytest

from peony import PeonyClient, oauth
from . import medias

oauth2_keys = 'PEONY_CONSUMER_KEY', 'PEONY_CONSUMER_SECRET'
oauth2 = all(key in os.environ for key in oauth2_keys)

oauth1_keys = *oauth2_keys, 'PEONY_ACCESS_TOKEN', 'PEONY_ACCESS_TOKEN_SECRET'
oauth1 = all(key in os.environ for key in oauth1_keys)

oauth2_creds = 'consumer_key', 'consumer_secret'
oauth1_creds = *oauth2_creds, 'access_token', 'access_token_secret'
token = None


def oauth2_decorator(func):

    @pytest.mark.asyncio
    @pytest.mark.twitter
    @pytest.mark.oauth2
    @pytest.mark.skipif(not oauth2, reason="no credentials found")
    async def decorator():
        global token

        client = get_oauth2_client(bearer_token=token)
        try:
            await func(client)
            # keep the token for the next test
            token = client.headers.token
        finally:
            client.close()

    return decorator


def oauth1_decorator(func):

    @pytest.mark.asyncio
    @pytest.mark.twitter
    @pytest.mark.oauth1
    @pytest.mark.skipif(not oauth1, reason="no credentials found")
    async def decorator():
        client = get_oauth1_client()
        try:
            await func(client)
        finally:
            client.close()

    return decorator


def get_oauth2_client(**kwargs):
    creds = {k: os.environ[envk] for k, envk in zip(oauth2_creds, oauth2_keys)}
    return PeonyClient(auth=oauth.OAuth2Headers, loop=False,
                       **creds, **kwargs)


def get_oauth1_client(**kwargs):
    creds = {k: os.environ[envk] for k, envk in zip(oauth1_creds, oauth1_keys)}
    return PeonyClient(auth=oauth.OAuth1Headers, loop=False,
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


@pytest.mark.invalidate_token
@oauth2_decorator
async def test_oauth2_invalidate_token(client):
    if 'Authorization' not in client.headers:  # make sure there is a token
        await client.headers.sign()

    await client.headers.invalidate_token()
    assert client.headers.token is None


@oauth2_decorator
async def test_oauth2_bearer_token(client):
    await client.headers.sign()

    token = client.headers.token

    client2 = get_oauth2_client(bearer_token=token)
    assert client2.headers.token == client.headers.token


@oauth1_decorator
async def test_search(client):
    await client.api.search.tweets.get(q="@twitter hello :)")


@oauth1_decorator
async def test_user_timeline(client):
    req = client.api.statuses.user_timeline.get(screen_name="twitter",
                                                count=20)
    responses = req.iterator.with_max_id()

    all_tweets = set()
    async for tweets in responses:
        # no duplicates
        assert not any(tweet.id in all_tweets for tweet in tweets)
        all_tweets |= set(tweet.id for tweet in tweets)

        if len(all_tweets) > 20:
            break


@oauth1_decorator
async def test_home_timeline(client):
    await client.api.statuses.home_timeline.get(count=20)


@oauth1_decorator
async def test_upload_media(client):
    async with aiohttp.ClientSession() as session:
        media = await medias['lady_peony'].download(session=session)
        assert 'media_id' in await client.upload_media(media)


@oauth1_decorator
async def test_upload_tweet(client):
    status = "%d Living in the limelight the universal dream " \
             "for those who wish to seem" % time.time()
    await client.api.statuses.update.post(status=status)


@oauth1_decorator
async def test_upload_tweet_with_media(client):
    media = await client.upload_media(await medias['seismic_waves'].download())
    await client.api.statuses.update.post(status="", media_ids=media.media_id)


@oauth1_decorator
async def test_upload_tweet_with_media_chunked(client):
    for media in medias.values():
        media = await client.upload_media(await media.download(), chunked=True)

        await client.api.statuses.update.post(status="",
                                              media_ids=media.media_id)


@oauth1_decorator
async def test_direct_message(client):
    await client.setup()  # needed to get the user
    message = {
        'event': {
            'type': "message_create",
            'message_create': {
                'target': {'recipient_id': client.user.id},
                'message_data': {
                    'text': "test %d" % time.time(),
                    'quick_reply': {
                        'type': "options",
                        'options': [
                            {'label': "Hello",
                             'description': "Hello",
                             'metadata': "foo"},
                            {'label': "World",
                             'description': "World",
                             'metadata': "bar"}
                        ]
                    }
                }
            }
        }
    }
    await client.api.direct_messages.events.new.post(_json=message)
