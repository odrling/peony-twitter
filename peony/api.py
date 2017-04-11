# -*- coding: utf-8 -*-

from abc import ABC, abstractmethod

from . import general, requests


class AbstractAPIPath(ABC):
    """
        The syntactic sugar factory

    Every time you get an attribute or an item from an instance of this
    class this will be appended to its _path variable (that you should
    not call) until you call a request method (like get or post)

    It makes it easy to call any endpoint of the api

    ⚠ You must create a child class of AbstractAPIPath to perform
    requests (you have to implement the _request method)

    The _client given as an parameter during the creation of the
    BaseAPIPath instance can be accessed as the "_client" attribute of
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

    def __getitem__(self, key):
        """
            Where the magic happens

        If the key is a request method (eg. get) call the _request
        attribute with the method as argument

        otherwise append the key to the _path attribute

        >>> api = APIPath()  # you would have to add more arguments
        >>> api['_client']   # appends '_client' to _path

        Parameters
        ----------
        key : :obj:`str`, :obj:`tuple` or :obj:`list`
            Key used to access an API endpoint and appended to the
            path attribute

        Returns
        -------
        BaseAPIPath
            New APIPath instance with a new ``path`` value
        """
        if isinstance(key, str):
            if key.lower() in general.request_methods:
                return self._request(key)
            else:
                new_path = self._path + [key]
        elif isinstance(key, (tuple, list)):
            key = [str(i) for i in key]
            new_path = self._path + key
        else:
            raise TypeError("Could not create endpoint from %s"
                            "of type %s" % (key, type(key)))

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

    @abstractmethod
    def _request(self, method):
        """
            Make a request for the endpoint
        
        Parameters
        ----------
        method : str
            method to use to make the request
        """

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, self.url())


class APIPath(AbstractAPIPath):
    """ Class to make requests to a REST API """

    def _request(self, method):
        return requests.Request(self, method)


class StreamingAPIPath(AbstractAPIPath):
    """ Class to make requests to a Streaming API """

    def _request(self, method):
        return requests.StreamingRequest(self, method)
