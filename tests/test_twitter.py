
import os
import time

import aiohttp
import pytest

from peony import PeonyClient, oauth

oauth2_keys = 'PEONY_CONSUMER_KEY', 'PEONY_CONSUMER_SECRET'

oauth1_keys = *oauth2_keys, 'PEONY_ACCESS_TOKEN', 'PEONY_ACCESS_TOKEN_SECRET'

keys_oauth = {1: oauth1_keys,
              2: oauth2_keys}

# test if the keys are in the environment variables
test_oauth = {i: all(key in os.environ for key in keys_oauth[i])
              for i in keys_oauth}

oauth2_creds = 'consumer_key', 'consumer_secret'
oauth1_creds = *oauth2_creds, 'access_token', 'access_token_secret'

creds_oauth = {1: oauth1_creds,
               2: oauth2_creds}


clients = {1: None,
           2: None}

headers = {1: oauth.OAuth1Headers,
           2: oauth.OAuth2Headers}


def client_oauth(key, event_loop):
    global clients

    if clients[key] is None:
        creds = {k: os.environ[envk]
                 for k, envk in zip(creds_oauth[key], keys_oauth[key])}

        clients[key] = PeonyClient(auth=headers[key], **creds)

    clients[key].loop = event_loop
    clients[key]._session = aiohttp.ClientSession(loop=event_loop)
    return clients[key]


@pytest.fixture
def oauth1_client(event_loop):
    return client_oauth(1, event_loop)


@pytest.fixture
def oauth2_client(event_loop):
    return client_oauth(2, event_loop)


def decorator_oauth(key):

    def oauth_decorator(func):

        # very dirty don't do this at home
        return pytest.mark.asyncio(
            pytest.mark.twitter(
                pytest.mark.skipif(not test_oauth[key],
                                   reason="no credentials found")(func)
            )
        )

    return oauth_decorator


oauth1_decorator = decorator_oauth(1)
oauth2_decorator = decorator_oauth(2)


@oauth2_decorator
async def test_oauth2_get_token(oauth2_client):
    if 'Authorization' in oauth2_client.headers:
        del oauth2_client.headers['Authorization']

    await oauth2_client.headers.sign()


@oauth2_decorator
async def test_oauth2_request(oauth2_client):
    await oauth2_client.api.search.tweets.get(q="@twitter hello :)")


@pytest.mark.invalidate_token
@oauth2_decorator
async def test_oauth2_invalidate_token(oauth2_client):
    # make sure there is a token
    if 'Authorization' not in oauth2_client.headers:
        await oauth2_client.headers.sign()

    await oauth2_client.headers.invalidate_token()
    assert oauth2_client.headers.token is None


@oauth2_decorator
async def test_oauth2_bearer_token(oauth2_client):
    await oauth2_client.headers.sign()

    token = oauth2_client.headers.token

    client2 = PeonyClient("", "", bearer_token=token,
                          auth=oauth.OAuth2Headers)
    assert client2.headers.token == oauth2_client.headers.token


@oauth1_decorator
async def test_search(oauth1_client):
    await oauth1_client.api.search.tweets.get(q="@twitter hello :)")


@oauth1_decorator
async def test_user_timeline(oauth1_client):
    req = oauth1_client.api.statuses.user_timeline.get(screen_name="twitter",
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
async def test_home_timeline(oauth1_client):
    await oauth1_client.api.statuses.home_timeline.get(count=20)


@oauth1_decorator
async def test_upload_media(oauth1_client, medias):
    media = await medias['lady_peony'].download()
    media = await oauth1_client.upload_media(media)

    await oauth1_client.api.statuses.update.post(status="",
                                                 media_ids=media.media_id)


@oauth1_decorator
async def test_upload_tweet(oauth1_client):
    status = "%d Living in the limelight the universal dream " \
             "for those who wish to seem" % time.time()
    await oauth1_client.api.statuses.update.post(status=status)


@oauth1_decorator
async def test_upload_tweet_with_media(oauth1_client, medias):
    data = await medias['seismic_waves'].download()
    media = await oauth1_client.upload_media(data)
    await oauth1_client.api.statuses.update.post(status="",
                                                 media_ids=media.media_id)


@oauth1_decorator
async def test_upload_tweet_with_media_chunked(oauth1_client, medias):
    for media in (medias[key] for key in ('pink_queen', 'bloom', 'video')):
        data = await media.download()
        media = await oauth1_client.upload_media(data, chunked=True)

        await oauth1_client.api.statuses.update.post(status="",
                                                     media_ids=media.media_id)


@oauth1_decorator
async def test_upload_tweet_with_media_from_url(oauth1_client, medias):
    for media in (medias[key] for key in ('pink_queen', 'bloom', 'video')):
        media = await oauth1_client.upload_media(media.url, chunked=True)

        await oauth1_client.api.statuses.update.post(status="",
                                                     media_ids=media.media_id)


@oauth1_decorator
async def test_direct_message(oauth1_client):
    await oauth1_client.setup  # needed to get the user
    message = {
        'event': {
            'type': "message_create",
            'message_create': {
                'target': {'recipient_id': oauth1_client.user.id},
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
    await oauth1_client.api.direct_messages.events.new.post(_json=message)
