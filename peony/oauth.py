# -*- coding: utf-8 -*-

import base64
import hmac
import random
import string
import time
from hashlib import sha1
import urllib.parse

from . import __version__

quote = lambda s: urllib.parse.quote(s, safe="")


class PeonyHeaders(dict):
    """
        Dynamic headers for Peony

    This is the base class of :class:`OAuth1Headers` and
    :class:`OAuth2Headers`.
    """

    def __init__(self, **kwargs):
        """ Add a nice User-Agent """
        self['User-Agent'] = "peony v%s" % __version__

        super().__init__(**kwargs)

    def prepare_request(self, method, url,
                        headers=None,
                        skip_params=False,
                        **kwargs):
        """
        prepare all the arguments for the request

        Parameters
        ----------
        method : str
            HTTP method used by the request
        url : str
            The url to request
        headers : :obj:`dict`, optional
            Additionnal headers
        skip_params : bool
            Don't use the parameters to sign the request

        Returns
        -------
        dict
            Parameters of the request correctly formatted
        """

        if method.lower() == "post":
            key = "data"
        else:
            key = "params"

        if key in kwargs and not skip_params:
            request_params = {key: kwargs.pop(key)}
        else:
            request_params = {}

        request_params.update(dict(method=method.upper(), url=url))

        request_params['headers'] = self.sign(**request_params,
                                              skip_params=skip_params,
                                              headers=headers)

        if headers is not None:
            request_params['headers'].update(headers)

        kwargs.update(request_params)

        return kwargs

    def prepare_headers(self):
        pass

    def sign(self, *args, headers=None, **kwargs):
        if headers is None:
            return self.copy()
        else:
            return self.copy().update(headers)


class OAuth1Headers(PeonyHeaders):
    """
        Dynamic headers implementing OAuth1

    :meth:`sign` is called before each request

    Parameters
    ----------
    consumer_key : str
        Your consumer key
    consumer_secret : str
        Your consumer secret
    access_token : str
        Your access token
    access_token_secret : str
        Your access token secret
    **kwargs
        Other headers
    """

    def __init__(self, consumer_key, consumer_secret,
                 access_token=None, access_token_secret=None, **kwargs):
        """ create the OAuth1 client """
        super().__init__(**kwargs)

        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.access_token = access_token
        self.access_token_secret = access_token_secret

        self.alphabet = string.ascii_letters + string.digits

    def sign(self, method='GET', url=None,
             data=None,
             params=None,
             skip_params=False,
             headers=None,
             **kwargs):
        """ sign, that is, generate the `Authorization` headers """

        headers = super().sign(headers=headers)

        if data:
            if skip_params:
                default = "application/octet-stream"
            else:
                default = "application/x-www-form-urlencoded"

            if not 'Content-Type' in headers:
                headers['Content-Type'] = default

            params = data

        oauth = {
            'oauth_consumer_key': self.consumer_key,
            'oauth_nonce': self.gen_nonce(),
            'oauth_signature_method': 'HMAC-SHA1',
            'oauth_timestamp': str(int(time.time())),
            'oauth_version': '1.0'
        }

        if self.access_token is not None:
            oauth['oauth_token'] = self.access_token

        oauth['oauth_signature'] = self.gen_signature(method=method, url=url,
                                                      params=params,
                                                      skip_params=skip_params,
                                                      oauth=oauth)

        headers['Authorization'] = "OAuth "

        for key, value in sorted(oauth.items(), key=lambda i: i[0]):
            if len(headers['Authorization']) > len("OAuth "):
                headers['Authorization'] += ", "

            headers['Authorization'] += quote(key) + '="' + quote(value) + '"'

        return headers

    def gen_nonce(self):
        return ''.join(random.choice(self.alphabet) for i in range(32))

    def gen_signature(self, method, url, params, skip_params, oauth):
        signature = method.upper() + "&" + quote(url) + "&"

        if skip_params:
            params = oauth
        else:
            params.update(oauth)

        param_string = ""

        for key, value in sorted(params.items(), key=lambda i: i[0]):
            if param_string:
                param_string += "&"

            if key == "q":
                encoded_value = urllib.parse.quote(value, safe="$:!?")
                param_string += quote(key) + "=" + encoded_value
            else:
                param_string += quote(key) + "=" + quote(value)

        signature += quote(param_string)

        key = quote(self.consumer_secret).encode() + b"&"
        if self.access_token_secret is not None:
            key += quote(self.access_token_secret).encode()

        signature = hmac.new(key, signature.encode(), sha1)

        signature = base64.b64encode(signature.digest()).decode().rstrip("\n")
        return signature


class OAuth2Headers(PeonyHeaders):
    """
        Dynamic headers implementing OAuth2

    Parameters
    ----------
    consumer_key : str
        Your consumer key
    consumer_secret : str
        Your consumer secret
    client : peony.BasePeonyClient
        The client to authenticate
    bearer_token : :obj:`str`, optional
        Your bearer_token
    **kwargs
        Other headers
    """

    def __init__(self, consumer_key, consumer_secret, client,
                 bearer_token=None,
                 **kwargs):
        super().__init__(**kwargs)
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.client = client
        if bearer_token:
            self.set_token(bearer_token)
        else:
            self.prepare_headers = self.refresh_token

        self.basic_authorization = self.get_basic_authorization()

    def get_basic_authorization(self):
        encoded_keys = map(quote, (self.consumer_key, self.consumer_secret))
        creds = ':'.join(encoded_keys).encode('utf-8')

        auth = "Basic " + base64.b64encode(creds).decode('utf-8')

        return {'Authorization': auth}

    def set_token(self, access_token):
        self['Authorization'] = "Bearer " + access_token

    async def invalidate_token(self, token=None):
        token = token or self.pop('Authorization')[len("Bearer "):]
        request = self.client['api', '', ''].oauth2.invalidate_token.post
        await request(access_token=token, _headers=self.basic_authorization)

    async def refresh_token(self):
        if 'Authorization' in self:
            await self.invalidate_token()

        request = self.client['api', "", ""].oauth2.token.post
        token = await request(grant_type="client_credentials",
                              _headers=self.basic_authorization,
                              _json=True,
                              _is_init_task=True)

        self.set_token(token['access_token'])
