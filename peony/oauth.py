
import oauthlib.oauth1
from oauthlib.common import add_params_to_uri

from . import __version__


class OAuth1Headers(dict):
    """
        Dynamic headers for OAuth1

    sign needs to be called before each request
    """

    def __init__(self, consumer_key, consumer_secret,
                 access_token=None, access_token_secret=None, **kwargs):
        """ create the OAuth1 client and a nice User-Agent """
        self.oauthclient = oauthlib.oauth1.Client(
            client_key=consumer_key,
            client_secret=consumer_secret,
            resource_owner_key=access_token,
            resource_owner_secret=access_token_secret,
            **kwargs
        )
        self['User-Agent'] = "peony v%s" % __version__

    def sign(self, method, url, data={}, params={}, **kwargs):
        """ sign, that is, generate the `Authorization` headers """

        headers = dict(**self)

        if data:
            headers['Content-Type'] = "application/x-www-form-urlencoded"
            body = data
        else:
            if params:
                url = add_params_to_uri(url, params.items())

            body = None

        uri, headers, body = self.oauthclient.sign(
            uri=url, http_method=method, headers=headers, body=body, **kwargs)

        return headers

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

        request_params['headers'] = self.sign(**request_params)
        request_params['headers'].update(headers)

        kwargs.update(request_params)

        return kwargs
