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

import aiohttp

from . import __version__, utils


def quote(s):
    return urllib.parse.quote(s, safe="")


class PeonyHeaders(ABC, dict):
    """
        Dynamic headers for Peony

    This is the base class of :class:`OAuth1Headers` and
    :class:`OAuth2Headers`.

    Parameters
    ----------
    compression : bool, optional
        If set to True the client will be able to receive compressed
        responses else it should not happen unless you provide the
        corresponding header when you make a request. Defaults to True.
    user_agent : str, optional
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

    async def prepare_request(self, method, url,
                              headers=None,
                              skip_params=False,
                              proxy=None,
                              **kwargs):
        """
        prepare all the arguments for the request

        Parameters
        ----------
        method : str
            HTTP method used by the request
        url : str
            The url to request
        headers : dict, optional
            Additionnal headers
        proxy : str
            proxy of the request
        skip_params : bool
            Don't use the parameters to sign the request

        Returns
        -------
        dict
            Parameters of the request correctly formatted
        """

        if method.lower() == "post":
            key = 'data'
        else:
            key = 'params'

        if key in kwargs and not skip_params:
            request_params = {key: kwargs.pop(key)}
        else:
            request_params = {}

        request_params.update(dict(method=method.upper(), url=url))

        coro = self.sign(**request_params, skip_params=skip_params,
                         headers=headers)
        request_params['headers'] = await utils.execute(coro)
        request_params['proxy'] = proxy

        kwargs.update(request_params)

        return kwargs

    def _user_headers(self, headers=None):
        """ Make sure the user doesn't override the Authorization header """
        h = self.copy()

        if headers is not None:
            keys = set(headers.keys())
            if h.get('Authorization', False):
                keys -= {'Authorization'}

            for key in keys:
                h[key] = headers[key]

        return h

    @abstractmethod
    def sign(self, *args, headers=None, **kwargs):
        """
            sign, that is, generate the `Authorization` headers before making
            a request
        """


class OAuth1Headers(PeonyHeaders):
    """
        Dynamic headers implementing OAuth1

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
                 compression=True, user_agent=None, headers=None):
        super().__init__(compression, user_agent, headers)

        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.access_token = access_token
        self.access_token_secret = access_token_secret

        self.alphabet = string.ascii_letters + string.digits

    @staticmethod
    def _default_content_type(skip_params):
        if skip_params:
            return "application/octet-stream"
        else:
            return "application/x-www-form-urlencoded"

    def sign(self, method='GET', url=None,
             data=None,
             params=None,
             skip_params=False,
             headers=None,
             **kwargs):

        headers = self._user_headers(headers)

        if data:
            if 'Content-Type' not in headers:
                default = self._default_content_type(skip_params)
                headers['Content-Type'] = default

            params = data.copy()
        elif params:
            params = params.copy()

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
        signature = method.upper() + '&' + quote(url) + '&'

        if params is None or skip_params:
            params = oauth
        else:
            params.update(oauth)

        param_string = ""

        for key, value in sorted(params.items(), key=lambda i: i[0]):
            if param_string:
                param_string += '&'

            param_string += quote(key) + '='

            if key == "q":
                encoded_value = urllib.parse.quote(value, safe="$:!?/()'*@")
                param_string += encoded_value
            else:
                param_string += quote(value)

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
    client : .client.BasePeonyClient
        The client to authenticate
    bearer_token : :obj:`str`, optional
        Your bearer_token
    **kwargs
        Other headers
    """

    def __init__(self, consumer_key, consumer_secret, client,
                 bearer_token=None, compression=True, user_agent=None,
                 headers=None):
        super().__init__(compression, user_agent, headers)

        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.client = client
        self.basic_authorization = self.get_basic_authorization()
        self._refreshing = asyncio.Event()
        self._refreshing.clear()

        if bearer_token is not None:
            self.token = bearer_token

    async def sign(self, url=None, *args, headers=None, **kwargs):
        if url == self._invalidate_token.url():
            del self.token
        elif 'Authorization' not in self:
            await self.refresh_token()

        return self._user_headers(headers)

    def get_basic_authorization(self):
        creds = quote(self.consumer_key), quote(self.consumer_secret)
        keys = ':'.join(creds).encode('utf-8')

        auth = "Basic " + base64.b64encode(keys).decode('utf-8')

        return {'Authorization': auth,
                'Content-Type': "application/x-www-form-urlencoded;"
                                "charset=UTF-8"}

    @property
    def token(self):
        print("setting token")
        if 'Authorization' in self:
            return self['Authorization'][len("Bearer "):]

    @token.setter
    def token(self, access_token):
        self['Authorization'] = "Bearer " + access_token

    @token.deleter
    def token(self):
        del self['Authorization']

    @property
    def _invalidate_token(self):
        return self.client['api', '', ''].oauth2.invalidate_token

    async def invalidate_token(self):
        if 'Authorization' not in self:
            raise RuntimeError('There is no token to invalidate')

        token = self.token

        try:
            request = self._invalidate_token.post
            data = RawFormData({'access_token': token}, quote_fields=False)

            await request(_data=data, _headers=self.basic_authorization)
        except:
            self.token = token
            raise

    async def refresh_token(self):
        if self._refreshing.is_set():
            return await self._refreshing.wait()

        self._refreshing.set()

        request = self.client['api', "", ""].oauth2.token.post
        token = await request(grant_type="client_credentials",
                              _headers=self.basic_authorization,
                              _oauth2_pass=True)

        self.token = token['access_token']

        self._refreshing.clear()

    async def prepare_request(self, *args, oauth2_pass=False, **kwargs):
        """
        prepare all the arguments for the request

        Parameters
        ----------
        oauth2_pass : bool
            For oauth2 authentication only (don't use it)

        Returns
        -------
        dict
            Parameters of the request correctly formatted
        """
        if not oauth2_pass:
            await self.sign()

        return await super().prepare_request(*args, **kwargs)


class RawFormData(aiohttp.FormData):

    def _gen_form_urlencoded(self):
        def key(item):
            return item[0]['name']

        data = ""
        for type_options, _, value in sorted(self._fields, key=key):
            if data:
                data += "&"

            data += "%s=%s" % (type_options['name'], value)

        charset = self._charset if self._charset is not None else 'utf-8'
        content_type = "application/x-www-form-urlencoded;charset=" + charset

        return aiohttp.payload.BytesPayload(data.encode(),
                                            content_type=content_type)
