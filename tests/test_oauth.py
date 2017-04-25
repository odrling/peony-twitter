
import random
from time import time
from unittest.mock import patch

import pytest
from peony import oauth


@pytest.fixture
def oauth1_headers():
    return oauth.OAuth1Headers("1234567890", "0987654321")


def test_oauth1_gen_nonce(oauth1_headers):
    assert oauth1_headers.gen_nonce() != oauth1_headers.gen_nonce()


def test_oauth1_signature(oauth1_headers):
    signature = oauth1_headers.gen_signature(method='GET',
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

    assert "yeNM+4SgurRymgAuOCbQTGLeDbQ=" == signature


def test_oauth1_sign(oauth1_headers):
    t = time()

    with patch.object(oauth.time, 'time', return_value=t):
        random.seed(0)
        headers = oauth1_headers.sign(method='GET',
                                      url='http://whatever.com',
                                      params={'hello': "world"})

    random.seed(0)
    nonce = oauth1_headers.gen_nonce()
    oauth_headers = {
        'oauth_consumer_key': oauth1_headers.consumer_key,
        'oauth_nonce': nonce,
        'oauth_signature_method': 'HMAC-SHA1',
        'oauth_timestamp': str(int(t)),
        'oauth_version': '1.0'
    }

    signature = oauth1_headers.gen_signature(method='GET',
                                             url='http://whatever.com',
                                             params={'hello': "world"},
                                             skip_params=False,
                                             oauth=oauth_headers)

    expected = ('OAuth oauth_consumer_key="1234567890", '
                'oauth_nonce="{nonce}", '
                'oauth_signature="{signature}", '
                'oauth_signature_method="HMAC-SHA1", '
                'oauth_timestamp="{time}", '
                'oauth_version="1.0"'.format(nonce=nonce,
                                             signature=oauth.quote(signature),
                                             time=int(t)))

    assert expected == headers['Authorization']
