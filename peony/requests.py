# -*- coding: utf-8 -*-

import asyncio
from abc import ABC, abstractmethod
from types import GeneratorType

from . import iterators, utils

iterable = (list, set, tuple, GeneratorType)


class Endpoint:
    """
        A class representing an endpoint

    Parameters
    ----------
    api : api.AbstractAPIPath
        API path of the request
    method : str
        HTTP method to be used by the request
    """

    def __init__(self, *request):
        if len(request) == 1:
            request = request[0]
            self.api = request.api
            self.method = request.method
        else:
            self.api, self.method = request


class AbstractRequest(ABC):
    """
        A function that makes a request when called
    """

    def __init__(self, *args, **kwargs):
        pass

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
                params[key] = "true" if value else "false"

            # iterables conversion
            elif isinstance(value, iterable):
                params[key] = ",".join(map(str, value))

            # skip params with value None
            elif value is None:
                pass

            # the rest is converted to str
            # (make sure you don't send something wrong)
            else:
                params[key] = str(value)

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
        """ method called to make the request """


class Iterators(Endpoint):
    """
    Access the iterators from :mod:`peony.iterators` right from a
    request object
    """

    def __init__(self, request):
        super().__init__(request)
        self.request = request

    def __getattr__(self, key):
        iterator = getattr(iterators, key)

        if isinstance(self.request, Request):
            def iterate(**kwargs):
                return iterator(self.request, **kwargs)
        else:
            keys = utils.get_args(iterator.__init__)

            def iterate(**kwargs):
                iterator_kwargs = {}
                for key in keys:
                    if '_' + key in kwargs:
                        iterator_kwargs[key] = kwargs.pop('_' + key)

                request = self.request(**kwargs)

                return iterator(request, **iterator_kwargs)

        return iterate


class RequestFactory(Endpoint):
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
        self.iterator = Iterators(self)

    def __call__(self, **kwargs):
        return Request(self.api, self.method, **kwargs)


class Request(asyncio.Future, AbstractRequest):

    def __init__(self, api, method, **kwargs):
        super().__init__()
        self.api = api
        self.method = method
        self.iterator = Iterators(self)
        self.kwargs = kwargs

        kwargs, skip_params, url = self._get_params(**kwargs)

        # if user explicitly wants to skip parameters in the oauth signature
        if 'skip_params' in kwargs:
            skip_params = kwargs.pop('skip_params')

        error_handling = kwargs.pop('error_handling', True)

        kwargs.update(method=self.method, url=url, skip_params=skip_params)

        client = self.api._client
        request = client.request

        if client.error_handler and error_handling:
            request = self.api._client.error_handler(request)

        client.loop.create_task(request(future=self, **kwargs))

    def __call__(self, **kwargs):
        return self.__class__(self.api, self.method, **kwargs)


class StreamingRequest(AbstractRequest):
    """
        Requests to Streaming APIs
    """

    def __init__(self, api, method):
        self.api = api
        self.method = method

    def __call__(self, **kwargs):
        kwargs, skip_params, url = self._get_params(**kwargs)

        return self.api._client.stream_request(self.method, url=url,
                                               skip_params=skip_params,
                                               **kwargs)
