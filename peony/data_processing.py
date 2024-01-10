import json
import logging

from . import exceptions

logger = logging.getLogger(__name__)


class BaseJSONData(dict):
    """
        A dict in which you can access items as attributes

    >>> obj = JSONData(key=True)
    >>> obj['key'] is obj.key
    True
    """

    def __getattr__(self, key):
        if key in self:
            return self[key]

        raise AttributeError(
            "%s has no property named %s." % (self.__class__.__name__, key)
        )

    def __delattr__(self, item):
        del self[item]

    def __setattr__(self, key, value):
        self[key] = value


class JSONData(BaseJSONData):
    """
    A dict that lets you get the full data of the tweet without having
    to check if the data is truncated
    """

    def __contains__(self, key):
        if key == "text":
            return super().__contains__("text") or "full_text" in self

        elif super().__contains__(key):
            return True

        if "extended_tweet" in self.keys():
            return key in self.extended_tweet

        return False

    def __getitem__(self, key):
        if key == "text" and "full_text" in self.keys():
            return super().__getitem__("full_text")

        if key == "extended_tweet":
            return super().__getitem__(key)

        if "extended_tweet" in self.keys():
            if key in self.extended_tweet:
                return self.extended_tweet[key]

        return super().__getitem__(key)

    def get(self, key, default=None):
        # it seems like the get method still called another __getitem__
        # than that of the instance
        if key in self:
            return self[key]

        return default


class PeonyResponse:
    """
        Response objects

    In these object you can access the headers, the request, the url
    and the data
    getting an attribute/item of this object will get the corresponding
    attribute/item of the data

    >>> peonyresponse = PeonyResponse(
    ...     data=JSONData(key="test"), headers={},
    ...     url="http://google.com", request={}
    ... )
    >>> peonyresponse.key is peonyresponse.data.key  # returns True
    >>>
    >>> peonyresponse = PeonyResponse(
    ...     data=[JSONData(key="test"), JSONData(key=1)], headers={},
    ...     url="http://google.com", request={}
    ... )
    >>> # iterate over peonyresponse.data
    >>> for key in peonyresponse:
    ...     pass  # do whatever you want

    Parameters
    ----------
    data : JSONData, dict or list
        Data object
    headers : dict
        Headers of the response
    url : str
        URL of the request
    request : dict
        Requests arguments
    """

    def __init__(self, data, headers, url, request):
        super().__setattr__("data", data)
        super().__setattr__("headers", headers)
        super().__setattr__("url", url)
        super().__setattr__("request", request)

    def __getattr__(self, key):
        """get attributes from the data"""
        return getattr(self.data, key)

    def __getitem__(self, key):
        """get items from the data"""
        return self.data[key]

    def __contains__(self, item):
        return item in self.data

    def __iter__(self):
        """iterate over the data"""
        return iter(self.data)

    def __str__(self):
        """use the string of the data"""
        return str(self.data)

    def __repr__(self):
        """use the representation of the data"""
        return repr(self.data)

    def __len__(self):
        """get the length of the data"""
        return len(self.data)

    def __setitem__(self, key, value):
        self.data[key] = value

    __setattr__ = __setitem__

    def __delitem__(self, key):
        del self.data[key]

    __delattr__ = __delitem__


def loads(json_data, encoding="utf-8", **kwargs):
    """
        Custom loads function with an object_hook and automatic decoding

    Parameters
    ----------
    json_data : str
        The JSON data to decode
    *args
        Positional arguments, passed to :func:`json.loads`
    encoding : :obj:`str`, optional
        The encoding of the bytestring
    **kwargs
        Keyword arguments passed to :func:`json.loads`

    Returns
    -------
    :obj:`dict` or :obj:`list`
        Decoded json data
    """
    if isinstance(json_data, bytes):
        json_data = json_data.decode(encoding)

    return json.loads(json_data, object_hook=JSONData, **kwargs)


async def read(response, loads=loads, encoding=None):
    """
        read the data of the response

    Parameters
    ----------
    response : aiohttp.ClientResponse
        response
    loads : callable
        json loads function
    encoding : :obj:`str`, optional
        character encoding of the response, if set to None
        aiohttp should guess the right encoding

    Returns
    -------
    :obj:`bytes`, :obj:`str`, :obj:`dict` or :obj:`list`
        the data returned depends on the response
    """
    ctype = response.headers.get("Content-Type", "").lower()

    try:
        if "application/json" in ctype:
            logger.debug("decoding data as json")
            return await response.json(encoding=encoding, loads=loads)

        if "text" in ctype:
            logger.debug("decoding data as text")
            return await response.text(encoding=encoding)

    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        data = await response.read()
        raise exceptions.PeonyDecodeError(response=response, data=data, exception=exc) from exc

    return await response.read()
