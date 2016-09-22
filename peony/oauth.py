# -*- coding: utf-8 -*-

import asyncio
import base64
from urllib.parse import quote

import oauthlib.oauth1
from oauthlib.common import add_params_to_uri

from . import __version__
from . import utils


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
        url str
            The url to request
        headers : :obj:`dict`, optional
            Additionnal headers
        skip_params : bool
            Don't use the parameters to sign the request

        Returns:
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
                                              skip_params=skip_params)
        if headers is not None:
            request_params['headers'].update(headers)

        kwargs.update(request_params)

        return kwargs

    async def prepare_headers(self):
        pass

    def sign(self, *args, **kwargs):
        return self.copy()


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

        self.oauthclient = oauthlib.oauth1.Client(
            client_key=consumer_key,
            client_secret=consumer_secret,
            resource_owner_key=access_token,
            resource_owner_secret=access_token_secret
        )

    def sign(self, method, url,
             data=None,
             params=None,
             skip_params=False,
             **kwargs):
        """ sign, that is, generate the `Authorization` headers """

        headers = super().sign()

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

        ___, headers, ____ = self.oauthclient.sign(
            uri=url, http_method=method, headers=headers, body=body, **kwargs)

        return headers


class OAuth2Headers(PeonyHeaders):
    """
        Dynamic headers implementing OAuth2

    Parameters
    ----------
    consumer_key : str
        Your consumer key
    consumer_secret : str
        Your consumer secret
    client : Client
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
                              _json=True)

        self.set_token(token['access_token'])


class Client:
    """
        A authenticated client

    This class should not be used directly as it has no way to make a
    request

    Parameters
    ----------
    consumer_key : str
        Your consumer key
    consumer_secret : str
        Your consumer secret
    access_token : :obj:`str`, optional
        Your access token
    access_token_secret : :obj:`str`, optional
        Your access token secret
    bearer_token : :obj:`str`, optional
        Your bearer_token
    auth : PeonyHeaders
        The authentication headers to use
    headers : dict
        Additional headers
    loop : event loop, optional
        An event loop, if not specified :func:`asyncio.get_event_loop`
        is called
    """

    def __init__(self, consumer_key, consumer_secret,
                 access_token=None,
                 access_token_secret=None,
                 bearer_token=None,
                 auth=OAuth1Headers,
                 headers=None,
                 loop=None):
        if headers is None:
            headers = {}

        # all the possible args required by headers in :mod:`peony.oauth`
        kwargs = {
            'consumer_key': consumer_key,
            'consumer_secret': consumer_secret,
            'access_token': access_token,
            'access_token_secret': access_token_secret,
            'bearer_token': bearer_token,
            'client': self
        }

        # get the args needed by the auth parameter on initialization
        args = utils.get_args(auth.__init__, skip=1)

        # keep only the arguments required by auth on init
        kwargs = {key: value for key, value in kwargs.items()
                  if key in args}

        self.headers = auth(**kwargs, **headers)

        self.loop = loop or asyncio.get_event_loop()

        self.loop.run_until_complete(self.headers.prepare_headers())
