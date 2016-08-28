# -*- coding: utf-8 -*-

import oauthlib.oauth1
from oauthlib.common import add_params_to_uri
from urllib.parse import quote
import base64

from . import __version__


class PeonyHeaders(dict):
    """
        Dynamic headers for Peony
    """

    def __init__(self, **kwargs):
        """ Add a nice User-Agent """
        super().__init__()

        self['User-Agent'] = "peony v%s" % __version__

    def prepare_request(self, method, url, headers={},
                        skip_params=False, **kwargs):
        """ prepare all the arguments for the request """

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
                                              skip_params=skip_params)
        request_params['headers'].update(headers)

        kwargs.update(request_params)

        return kwargs

    async def prepare_headers(self):
        pass

    def sign(self, *args, **kwargs):
        return self.copy()


class OAuth1Headers(PeonyHeaders):
    """
        Dynamic headers for OAuth1

    sign needs to be called before each request
    """

    def __init__(self, consumer_key, consumer_secret,
                 access_token=None, access_token_secret=None, **kwargs):
        """ create the OAuth1 client """
        super().__init__()

        self.oauthclient = oauthlib.oauth1.Client(
            client_key=consumer_key,
            client_secret=consumer_secret,
            resource_owner_key=access_token,
            resource_owner_secret=access_token_secret
        )

    def sign(self, method, url,
             data={},
             params={},
             skip_params=False,
             **kwargs):
        """ sign, that is, generate the `Authorization` headers """

        headers = self.copy()

        if data:
            if skip_params:
                default = "application/octet-stream"
            else:
                default = "application/x-www-form-urlencoded"

            headers['Content-Type'] = headers.get('Content-Type', default)

            body = data
        else:
            if params:
                url = add_params_to_uri(url, params.items())

            body = None

        uri, headers, body = self.oauthclient.sign(
            uri=url, http_method=method, headers=headers, body=body, **kwargs)

        return headers


class OAuth2Headers(PeonyHeaders):

    def __init__(self, consumer_key, consumer_secret, client,
                 bearer_token=None,
                 encoding="utf-8",
                 **kwargs):
        super().__init__()
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.client = client
        self.encoding = encoding
        if bearer_token:
            self.set_token(bearer_token)
        else:
            self.prepare_headers = self.refresh_token

        self.basic_authorization = self.get_basic_authorization()

    def get_basic_authorization(self):
        encoded_keys = map(quote, (self.consumer_key, self.consumer_secret))
        creds = ':'.join(encoded_keys).encode(self.encoding)

        auth = "Basic " + base64.b64encode(creds).decode(self.encoding)

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
                              _json=True)

        self.set_token(token['access_token'])
