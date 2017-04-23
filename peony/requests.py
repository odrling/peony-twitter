# -*- coding: utf-8 -*-

from abc import ABC, abstractmethod
from types import GeneratorType

from . import iterators

iterable = (list, set, tuple, GeneratorType)


class Endpoint():
    """
        A class representing an endpoint

    Parameters
    ----------
    api : api.AbstractAPIPath
        API path of the request
    method : str
        HTTP method to be used by the request
    """

    def __init__(self, api, method):
        self.api = api
        self.method = method


class AbstractRequest(ABC, Endpoint):
    """
        A function that makes a request when called
    """

    def _get_params(self, _suffix=None, **kwargs):
        if _suffix is None:
            _suffix = self.api._suffix

        kwargs, skip_params = self.sanitize_params(self.method, **kwargs)

        return kwargs, skip_params, self.api.url(_suffix)

    @staticmethod
    def sanitize_params(method, **kwargs):
        """
            Request params can be extracted from the ``**kwargs``

        Arguments starting with `_` will be stripped from it, so they
        can be used as an argument for the request
        (eg. "_headers" → "headers" in the kwargs returned by this
        function while "headers" would be inserted into the parameters
        of the request)

        Parameters
        ----------
        method : str
            method to use to make the request
        kwargs : dict
            Keywords arguments given to the request

        Returns
        -------
        dict
            New requests parameters, correctly formatted
        """
        # items which does not have a key starting with `_`
        items = [(key, value) for key, value in kwargs.items()
                 if not key.startswith("_")]
        params, skip_params = {}, False

        for key, value in items:
            # binary data
            if hasattr(value, 'read') or isinstance(value, bytes):
                params[key] = value
                # The params won't be used to make the signature
                skip_params = True

            # booleans conversion
            elif isinstance(value, bool):
                params[key] = value and "true" or "false"

            # integers conversion
            elif isinstance(value, int):
                params[key] = str(value)

            # iterables conversion
            elif isinstance(value, iterable):
                params[key] = ",".join(map(str, value))

            # skip params with value None
            elif value is None:
                pass

            # the rest is sent as is
            else:
                params[key] = value

        # dict with other items (+ strip "_" from keys)
        kwargs = {key[1:]: value for key, value in kwargs.items()
                  if key.startswith("_")}

        if method == "post" and not kwargs.get('data', None) and params:
            kwargs['data'] = params  # post requests use the data argument

        elif not kwargs.get('params', None) and params:
            kwargs['params'] = params

        return kwargs, skip_params

    @abstractmethod
    def __call__(self, **kwargs):
        pass


class Iterators(Endpoint):
    """
    Access the iterators from :mod:`peony.iterators` right from a
    request object
    """

    def _get_iterator(self, iterator):
        def iterate(**kwargs):
            request = getattr(self.api, self.method)
            return iterator(request, **kwargs)
        return iterate

    def __getattr__(self, key):
        return self._get_iterator(getattr(iterators, key))


class Request(AbstractRequest):
    """
        Requests to REST APIs

    Parameters
    ----------
    api : api.AbstractAPIPath
        API path of the request
    method : str
        HTTP method to be used by the request
    """

    def __init__(self, api, method):
        super().__init__(api, method)
        self.iterator = Iterators(api, method)

    def __call__(self, _skip_params=None, _error_handling=True, **kwargs):
        kwargs, skip_params, url = self._get_params(**kwargs)

        skip_params = skip_params if _skip_params is None else _skip_params
        kwargs.update(method=self.method, url=url, skip_params=skip_params)

        client_request = self.api._client.request

        if self.api._client.error_handler and _error_handling:
            client_request = self.api._client.error_handler(client_request)

        return client_request(**kwargs)


class StreamingRequest(AbstractRequest):
    """
        Requests to Streaming APIs
    """

    def __call__(self, **kwargs):
        kwargs, skip_params, url = self._get_params(**kwargs)

        return self.api._client.stream_request(self.method, url=url,
                                               skip_params=skip_params,
                                               **kwargs)
