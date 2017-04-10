# -*- coding: utf-8 -*-

from abc import ABC, abstractmethod

from . import iterators


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
        
    """

    def _get_params(self, _suffix=None, **kwargs):
        if _suffix is None:
            _suffix = self.api.suffix

        kwargs, skip_params = self.api.sanitize_params(self.method, **kwargs)

        return kwargs, skip_params, self.api.url(_suffix)

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

        client_request = self.api.client.request

        if self.api.client.error_handler and _error_handling:
            client_request = self.api.client.error_handler(client_request)

        return client_request(**kwargs)


class StreamingRequest(AbstractRequest):
    """
        Requests to Streaming APIs
    """

    def __call__(self, **kwargs):
        kwargs, skip_params, url = self._get_params(**kwargs)

        return self.api.client.stream_request(self.method, url=url,
                                              skip_params=skip_params,
                                              **kwargs)
