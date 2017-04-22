# -*- coding: utf-8 -*-

import asyncio
import base64
import hmac
import random
import string
import time
import urllib.parse
from abc import ABC, abstractmethod
from hashlib import sha1

from . import __version__


def quote(s):
    return urllib.parse.quote(s, safe="")


class PeonyHeaders(ABC, dict):
    """
        Dynamic headers for Peony

    This is the base class of :class:`OAuth1Headers` and
    :class:`OAuth2Headers`.

    Parameters
    ----------
    compression : :obj:`bool`, optional
        If set to True the client will be able to receive compressed
        responses else it should not happen unless you provide the
        corresponding header when you make a request. Defaults to True.
    user_agent : :obj:`str`, optional
        The user agent set in the headers. Defaults to
        "peony v{version number}"
    headers : dict
        dict containing custom headers
    """

    def __init__(self, compression=True, user_agent=None, headers=None):
        """ Add a nice User-Agent """
        super().__init__()

        if user_agent is None:
            self['User-Agent'] = "peony v" + __version__
        else:
            self['User-Agent'] = user_agent

        if compression:
            self['Accept-Encoding'] = "deflate, gzip"

        if headers is not None:
            for key, value in headers.items():
                self[key] = value

    def __setitem__(self, key, value):
        super().__setitem__(key.title(), value)

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

    def _user_headers(self, headers=None):
        """ Make sure the user doesn't override the Authorization header """
        h = self.copy()

        if headers is not None:
            for key in set(headers.keys()) - {'Authorization'}:
                h[key] = headers[key]

        return h

    @abstractmethod
    async def prepare_headers(self):
        """
            prepare the headers, after creating an instance of PeonyHeaders
        """

    @abstractmethod
    def sign(self, *args, headers=None, **kwargs):
        """
            sign, that is, generate the `Authorization` headers before making
            a request
        """


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
                 access_token=None, access_token_secret=None,
                 compression=True, user_agent=None):
        super().__init__(compression, user_agent)

        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.access_token = access_token
        self.access_token_secret = access_token_secret

        self.alphabet = string.ascii_letters + string.digits

    async def prepare_headers(self):
        """ There is nothing to do for OAuth1 headers """

    def sign(self, method='GET', url=None,
             data=None,
             params=None,
             skip_params=False,
             headers=None,
             **kwargs):

        headers = self._user_headers(headers)

        if data:
            if skip_params:
                default = "application/octet-stream"
            else:
                default = "application/x-www-form-urlencoded"

            if 'Content-Type' not in headers:
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
                encoded_value = urllib.parse.quote(value, safe="$:!?/()'*@")
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
                 bearer_token=None, compression=True, user_agent=None):
        super().__init__(compression, user_agent)

        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.client = client
        self.basic_authorization = self.get_basic_authorization()
        self._refreshed = asyncio.Event()

        if bearer_token is not None:
            self.set_token(bearer_token)

    async def prepare_headers(self):
        if 'Authorization' not in self:
            await self.refresh_token()

    async def sign(self, headers=None, **kwargs):
        self.prepare_headers()

        return self._user_headers(headers)

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
        if not self._refreshed.is_set():
            return await self._refreshed.wait()

        self._refreshed.clear()

        if 'Authorization' in self:
            await self.invalidate_token()

        request = self.client['api', "", ""].oauth2.token.post
        token = await request(grant_type="client_credentials",
                              _headers=self.basic_authorization,
                              _json=True,
                              _is_init_task=True)

        self.set_token(token['access_token'])

        self._refreshed.set()
