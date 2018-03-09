
import asyncio
import base64
import random
from time import time
from unittest.mock import patch

import pytest

from peony import exceptions, oauth

from . import dummy


@pytest.fixture
def oauth1_headers():
    return oauth.OAuth1Headers("1234567890", "0987654321", "aaaa", "bbbb")


def dummy_func(arg, **kwargs):
    return arg


class MockClient:

    def __init__(self):
        self.count = 0

    def __getitem__(self, key):
        return self

    def __getattr__(self, key):
        return self

    async def post(self, _data=None, _headers=None, **kwargs):
        self.count += 1

        if _data is not None:
            with patch.object(oauth.aiohttp.payload, 'BytesPayload',
                              side_effect=dummy_func):
                assert _data._gen_form_urlencoded() == b"access_token=abc"

        if _headers is not None:
            key = "1234567890:0987654321"
            auth = base64.b64encode(key.encode('utf-8')).decode('utf-8')
            assert _headers['Authorization'] == 'Basic ' + auth

        # This is needed to run `test_oauth2_concurrent_refreshes`
        # without that, refresh tasks would be executed sequentially
        # In a sense it is a simulation of a request being fetched
        await asyncio.sleep(0.001)
        return {'access_token': "abc"}

    def url(self):
        return ""


@pytest.fixture
def oauth2_headers():
    return oauth.OAuth2Headers("1234567890", "0987654321", client=MockClient())


def test_oauth1_gen_nonce(oauth1_headers):
    assert oauth1_headers.gen_nonce() != oauth1_headers.gen_nonce()


def test_oauth1_signature(oauth1_headers):
    signature = oauth1_headers.gen_signature(method='GET',
                                             url="http://whatever.com",
                                             params={'hello': "world"},
                                             skip_params=False,
                                             oauth={})

    assert "v3nfF8OWWLfGTuKhi7075R1BBGE=" == signature


def test_oauth1_signature_no_token():
    headers = oauth.OAuth1Headers("1234567890", "0987654321")

    signature = headers.gen_signature(method='GET',
                                      url="http://whatever.com",
                                      params={'hello': "world"},
                                      skip_params=False,
                                      oauth={})

    assert "Q9XX4OvdvoOb8ZJyXPrhWiYwOzk=" == signature


def test_oauth1_signature_queries_safe_chars(oauth1_headers):
    query = "@twitter hello :) $:!?/()'*@"

    signature = oauth1_headers.gen_signature(method='GET',
                                             url="http://whatever.com",
                                             params={'q': query},
                                             skip_params=False,
                                             oauth={'Header': "hello"})

    assert "ah8dUnveaRVMFisNXKScS6Wy2kU=" == signature


def test_oauth1_sign(oauth1_headers):
    t = time()

    with patch.object(oauth.time, 'time', return_value=t):
        random.seed(0)
        headers = oauth1_headers.sign(method='POST',
                                      url='http://whatever.com',
                                      data={'hello': "world"})

    random.seed(0)
    nonce = oauth1_headers.gen_nonce()
    oauth_headers = {
        'oauth_consumer_key': oauth1_headers.consumer_key,
        'oauth_nonce': nonce,
        'oauth_signature_method': 'HMAC-SHA1',
        'oauth_timestamp': str(int(t)),
        'oauth_version': '1.0',
        'oauth_token': "aaaa"
    }

    signature = oauth1_headers.gen_signature(method='POST',
                                             url='http://whatever.com',
                                             params={'hello': "world"},
                                             skip_params=False,
                                             oauth=oauth_headers)

    expected = ('OAuth oauth_consumer_key="1234567890", '
                'oauth_nonce="{nonce}", '
                'oauth_signature="{signature}", '
                'oauth_signature_method="HMAC-SHA1", '
                'oauth_timestamp="{time}", '
                'oauth_token="aaaa", '
                'oauth_version="1.0"'.format(nonce=nonce,
                                             signature=oauth.quote(signature),
                                             time=int(t)))

    assert expected == headers['Authorization']


@pytest.mark.parametrize('headers,key', [
    (None, 'data'),
    (None, 'params'),
    ({'Content-Type': "application/x-www-form-urlencoded"}, 'data')
])
def test_oauth1_sign_skip_params(oauth1_headers, headers, key):
    t = time()

    with patch.object(oauth.time, 'time', return_value=t):
        random.seed(0)
        kwargs = {
            'method': 'POST',
            'url': "http://whatever.com",
            key: {'hello': "world"},
            'skip_params': True,
            'headers': headers
        }
        headers = oauth1_headers.sign(**kwargs)

    random.seed(0)
    nonce = oauth1_headers.gen_nonce()
    oauth_headers = {
        'oauth_consumer_key': oauth1_headers.consumer_key,
        'oauth_nonce': nonce,
        'oauth_signature_method': 'HMAC-SHA1',
        'oauth_timestamp': str(int(t)),
        'oauth_version': '1.0',
        'oauth_token': "aaaa"
    }

    signature = oauth1_headers.gen_signature(method='POST',
                                             url='http://whatever.com',
                                             params={'hello': "world"},
                                             skip_params=True,
                                             oauth=oauth_headers)

    expected = ('OAuth oauth_consumer_key="1234567890", '
                'oauth_nonce="{nonce}", '
                'oauth_signature="{signature}", '
                'oauth_signature_method="HMAC-SHA1", '
                'oauth_timestamp="{time}", '
                'oauth_token="aaaa", '
                'oauth_version="1.0"'.format(nonce=nonce,
                                             signature=oauth.quote(signature),
                                             time=int(t)))

    assert expected == headers['Authorization']


def test_headers_options():
    client = oauth.OAuth1Headers("", "",
                                 user_agent="Awesome app",
                                 compression=False,
                                 headers={'Custom': "abc"})
    assert client['User-Agent'] == "Awesome app"
    assert 'Accept-Encoding' not in client
    assert client['Custom'] == "abc"


@pytest.mark.asyncio
async def test_prepare_request(oauth1_headers):
    async def mock_sign():  # no need to test sign again here
        return oauth1_headers.copy()

    with patch.object(oauth1_headers, 'sign') as sign:
        sign.return_value = mock_sign()
        kwargs = await oauth1_headers.prepare_request(
            method='GET', url="http://whatever.com", params={'test': 'hello'}
        )

        sign.return_value = mock_sign()
        kwargs_post = await oauth1_headers.prepare_request(
            method='POST', url="http://whatever.com", data={'test': 'hello'}
        )

        sign.return_value = mock_sign()
        kwargs_no_params = await oauth1_headers.prepare_request(
            method='get', url="http://whatever.com"
        )

    assert 'params' in kwargs
    assert 'data' in kwargs_post

    assert kwargs['method'] == 'GET'
    assert kwargs_post['method'] == 'POST'

    assert kwargs['url'] == kwargs['url'] == "http://whatever.com"

    assert kwargs_post['headers'] == kwargs['headers'] == oauth1_headers.copy()
    assert kwargs_post['data'] == kwargs['params'] == {'test': 'hello'}

    assert 'data' not in kwargs
    assert 'params' not in kwargs_post
    assert 'data' not in kwargs_no_params and 'params' not in kwargs_no_params


def test_user_headers(oauth2_headers):
    oauth2_headers.token = "abc"
    headers = oauth2_headers._user_headers({'Authorization': "cba"})
    assert headers['Authorization'] == "Bearer abc"

    del oauth2_headers.token
    headers = oauth2_headers._user_headers({'Authorization': "cba"})
    assert headers['Authorization'] == "cba"


def test_oauth2_set_token():
    oauth2 = oauth.OAuth2Headers("123", "456", client=None, bearer_token="abc")
    assert oauth2.token == "abc"


@pytest.mark.asyncio
async def test_oauth2_refresh_token(oauth2_headers):
    assert oauth2_headers.token is None

    await oauth2_headers.refresh_token()
    assert oauth2_headers.token == "abc"
    with patch.object(oauth2_headers, 'invalidate_token',
                      side_effect=dummy) as invalidate_token:
        await oauth2_headers.refresh_token()
        assert invalidate_token.called


@pytest.mark.asyncio
async def test_oauth2_sign(oauth2_headers):
    with patch.object(oauth2_headers, 'refresh_token',
                      side_effect=dummy) as refresh_token:
        await oauth2_headers.sign(url='http://whatever.com')
        assert refresh_token.called

    await oauth2_headers.sign(url='http://whatever.com')
    assert oauth2_headers.token == "abc"
    with patch.object(oauth2_headers, 'refresh_token') as refresh_token:
        await oauth2_headers.sign(url='http://whatever.com')
        assert not refresh_token.called


@pytest.mark.asyncio
async def test_oauth2_sign_url_invalidate(oauth2_headers):
    oauth2_headers.token = "test"
    await oauth2_headers.sign(url=oauth2_headers._invalidate_token.url())
    assert oauth2_headers.token is None


@pytest.mark.asyncio
async def test_oauth2_concurrent_refreshes(oauth2_headers):
    assert oauth2_headers.client.count == 0

    async def refresh():
        await oauth2_headers.refresh_token()

    await asyncio.gather(refresh(), refresh())
    assert oauth2_headers.client.count == 1


def test_raw_form_data():

    with patch.object(oauth.aiohttp.payload, 'BytesPayload',
                      side_effect=dummy_func):
        formdata = oauth.RawFormData({'access_token': "a%20bc%25",
                                      'access_token_secret': "cba"},
                                     quote_fields=False)
        data = formdata._gen_form_urlencoded()
        assert data == b"access_token=a%20bc%25&access_token_secret=cba"


@pytest.mark.asyncio
async def test_oauth2_invalidate_token_no_token(oauth2_headers):
    with pytest.raises(RuntimeError):
        await oauth2_headers.invalidate_token()


@pytest.mark.asyncio
async def test_oauth2_invalidate_token_exception(oauth2_headers):
    def rexc(**kwargs):
        raise exceptions.PeonyException

    with pytest.raises(exceptions.PeonyException):
        with patch.object(oauth2_headers.client, 'post', side_effect=rexc):
            oauth2_headers.token = "abc"
            await oauth2_headers.invalidate_token()
