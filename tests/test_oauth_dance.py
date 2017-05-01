
import io
from contextlib import redirect_stdout
from unittest.mock import patch

import pytest
from peony import oauth, oauth_dance, utils

alphabet = ''.join(chr(i) for i in range(ord('a'), ord('a') + 26))


class MockOAuth2Headers(oauth.OAuth2Headers):

    def __init__(self, consumer_key, consumer_secret, client=None, **kwargs):
        assert consumer_key == "a"
        assert consumer_secret == "b"
        super().__init__(consumer_key, consumer_secret, client)

    async def sign(self, *args, **kwargs):
        self.token = alphabet
        return self.copy()


def test_oauth2_dance(event_loop):
    with patch.object(oauth_dance.oauth, 'OAuth2Headers',
                      side_effect=MockOAuth2Headers):
        args = 'consumer_key', 'consumer_secret'
        with patch.object(utils, 'get_args', return_value=args):
            assert alphabet == oauth_dance.oauth2_dance("a", "b", event_loop)


@pytest.mark.asyncio
async def test_get_oauth_token():
    async def request(method, url, *args, **kwargs):
        assert method == 'post'
        assert url == "https://api.twitter.com/oauth/request_token"
        return "oauth_token=abc&hello=world"

    with patch.object(oauth_dance.BasePeonyClient, 'request',
                      side_effect=request):
        data = await oauth_dance.get_oauth_token("", "")
        assert data == {'oauth_token': "abc", 'hello': "world"}


async def dummy(*args, **kwargs):
    pass


@pytest.mark.asyncio
async def test_get_oauth_verifier():
    def test_url(url):
        assert url == "https://api.twitter.com/oauth/authorize?oauth_token=abc"
        return True

    with patch.object(oauth_dance.webbrowser, 'open', side_effect=test_url):
        with patch.object(oauth_dance.asyncio, 'sleep', side_effect=dummy):
            with patch.object(oauth_dance, 'input', return_value="12345"):
                assert await oauth_dance.get_oauth_verifier("abc") == "12345"


@pytest.mark.asyncio
async def test_get_oauth_verifier_no_browser():
    stream = io.StringIO()
    url = "https://api.twitter.com/oauth/authorize?oauth_token=abc"

    with patch.object(oauth_dance.asyncio, 'sleep', side_effect=dummy):
        with patch.object(oauth_dance.webbrowser, 'open', return_value=False):
            with patch.object(oauth_dance, 'input', return_value="12345"):
                with redirect_stdout(stream):
                    await oauth_dance.get_oauth_verifier("abc")

                stream.seek(0)
                assert url in stream.read()


@pytest.mark.asyncio
async def test_get_oauth_verifier_browser_error():
    def error(url):
        raise RuntimeError

    stream = io.StringIO()
    url = "https://api.twitter.com/oauth/authorize?oauth_token=abc"

    with patch.object(oauth_dance.asyncio, 'sleep', side_effect=dummy):
        with patch.object(oauth_dance.webbrowser, 'open', side_effect=error):
            with patch.object(oauth_dance, 'input', return_value="12345"):
                with redirect_stdout(stream):
                    await oauth_dance.get_oauth_verifier("abc")

                stream.seek(0)
                assert url in stream.read()


@pytest.mark.asyncio
async def test_get_access_token():
    async def request(method, url, params, *args, **kwargs):
        assert method == 'get'
        assert url == "https://api.twitter.com/oauth/access_token"
        assert params['oauth_verifier'] == "12345"
        return "access_token=abc&access_secret=cba"

    with patch.object(oauth_dance.BasePeonyClient, 'request',
                      side_effect=request):
        data = await oauth_dance.get_access_token("", "", "", "", "12345")
        assert data == {'access_token': "abc", 'access_secret': "cba"}


@pytest.mark.asyncio
async def test_async_oauth_dance():
    with patch.object(oauth_dance, 'get_oauth_token') as get_oauth_token:
        with patch.object(oauth_dance,
                          'get_oauth_verifier') as get_oauth_verifier:
            with patch.object(oauth_dance,
                              'get_access_token') as get_access_token:
                async def oauth_token(consumer_key, consumer_secret,
                                      callback_uri):
                    assert consumer_key == 'a'
                    assert consumer_secret == 'b'
                    assert callback_uri == "oob"

                    assert not get_oauth_verifier.called
                    assert not get_access_token.called

                    return {'oauth_token': alphabet,
                            'another': "cba"}

                async def oauth_verifier(oauth_token):
                    assert oauth_token == alphabet

                    assert get_oauth_token.called
                    assert not get_access_token.called
                    return "12345"

                async def access_token(consumer_key,
                                       consumer_secret,
                                       oauth_verifier,
                                       oauth_token,
                                       another):
                    assert consumer_key == 'a'
                    assert consumer_secret == 'b'
                    assert oauth_verifier == "12345"
                    assert oauth_token == alphabet
                    assert another == "cba"

                    assert get_access_token.called
                    assert get_oauth_verifier.called

                    return {'consumer_key': consumer_key,
                            'consumer_secret': consumer_secret,
                            'oauth_token': "abcdef",
                            'oauth_token_secret': "ghijkl",
                            'hello': "world"}

                get_oauth_verifier.side_effect = oauth_verifier
                get_oauth_token.side_effect = oauth_token
                get_access_token.side_effect = access_token

                tokens = await oauth_dance.async_oauth_dance('a', 'b')

                assert tokens == {'consumer_key': 'a',
                                  'consumer_secret': 'b',
                                  'access_token': "abcdef",
                                  'access_token_secret': "ghijkl"}


def test_oauth_dance(event_loop):
    data = {'consumer_key': "abc",
            'consumer_secret': "def",
            'access_token': "ghi",
            'access_token_secret': "jkl"}

    async def async_oauth_dance(consumer_key, consumer_secret, callback_uri):
        return data

    with patch.object(oauth_dance, 'async_oauth_dance',
                      side_effect=async_oauth_dance) as async_dance:
        assert oauth_dance.oauth_dance('a', 'b', loop=event_loop) == data
        assert async_dance.called_with('a', 'b', "oob")
