# -*- coding: utf-8 -*-

from types import GeneratorType

from . import general, requests


class BaseAPIPath:
    r"""
        The syntactic sugar factory

    Everytime you get an attribute or an item from an instance of this
    class this will be appended to its _path variable (that you should
    not call) until you call a request method (like get or post)

    It makes it easy to call any endpoint of the api

    ⚠ You must create a child class of BaseAPIPath to perform
    requests (you have to overload the _request method)

    The client given as an parameter during the creation of the
    BaseAPIPath instance can be accessed as the "client" attribute of
    the instance.
    """

    def __init__(self, path, suffix, client):
        self._path = path
        self._suffix = suffix
        self._client = client

    def url(self, suffix=None):
        """
            Build the url using the _path attribute

        Parameters
        ----------
        suffix : str
            String to be appended to the url

        Returns
        -------
        str
            Path to the endpoint
        """
        return "/".join(self._path) + (suffix or self._suffix)

    def __getitem__(self, k):
        """
            Where the magic happens

        If the key is a request method (eg. get) call the _request
        attribute with the method as argument

        otherwise append the key to the _path attribute

        >>> instance = APIPath()  # you would have to add more arguments
        >>> instance["client"]    # appends `client` to _path

        Parameters
        ----------
        k : str
            Key used to access an API endpoint and appended to the
            path attribute

        Returns
        -------
        BaseAPIPath
            New APIPath instance with a new ``path`` value
        """
        if k.lower() in general.request_methods:
            return self._request(self, k)
        else:
            if isinstance(k, (tuple, list)):
                k = map(str, k)
                new_path = self._path + k
            else:
                new_path = self._path + [k]

            return self.__class__(path=new_path,
                                  suffix=self._suffix,
                                  client=self._client)

    def __getattr__(self, k):
        """
            Call __getitem__ when trying to get an attribute from the
            instance

        If your path contains an actual attribute of the instance
        you should call __getitem__ instead
        """
        return self[k]

    @staticmethod
    def sanitize_params(method, **kwargs):
        """
            Request params can be extracted from the ``**kwargs``

        Arguments starting with `_` will be stripped from it, so they
        can be used as an argument for the request
        (eg. "_headers" → "headers" in the kwargs returned by this
        function while "headers" would be inserted in the params)

        Parameters
        ----------
        **kwargs
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

        iterable = (list, set, tuple, GeneratorType)

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

        if method.lower() == "post":
            kwargs['data'] = params  # post requests use the data argument
        else:
            kwargs['params'] = params

        return kwargs, skip_params

    def _request(self, method):
        """ method to be overloaded """
        pass

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, self.url())


class APIPath(BaseAPIPath):
    """ Class to make requests to a REST API """

    _request = requests.Request


class StreamingAPIPath(BaseAPIPath):
    """ Class to make requests to a Streaming API """

    _request = requests.StreamingRequest
