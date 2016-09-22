# -*- coding: utf-8 -*-

import asyncio
import io
import functools
import json
import os
import sys
import traceback
from urllib.parse import urlparse

import aiohttp
from PIL import Image

from . import exceptions

try:
    from magic import Magic
    mime = Magic(mime=True)
    magic = True
except:
    print('Could not load python-magic, fallback to mimetypes',
          file=sys.stderr)
    import mimetypes
    mime = mimetypes.MimeTypes()
    magic = False


class JSONObject(dict):
    """
        A dict in which you can access items as attributes

    >>> obj = JSONObject(key=True)
    >>> obj['key'] is obj.key
    True
    """

    def __getattr__(self, key):
        if key in self:
            return self[key]
        raise AttributeError("%s has no property named %s." %
                             (self.__class__.__name__, key))

    def __setattr__(self, *args):
        raise AttributeError("%s instances are read-only." %
                             self.__class__.__name__)
    __delattr__ = __setitem__ = __delitem__ = __setattr__


class PeonyResponse:
    """
        Response objects

    In these object you can access the headers, the request, the url
    and the response
    getting an attribute/item of this object will get the corresponding
    attribute/item of the response

    >>> peonyresponse.key is peonyresponse.response.key  # returns True
    >>>
    >>> # iterate over peonyresponse.response
    >>> for key in peonyresponse:
    ...     pass  # do whatever you want

    Parameters
    ----------
    response : dict or list
        Response object
    headers : dict
        Headers of the response
    url : str
        URL of the request
    request : dict
        Requests arguments
    """

    def __init__(self, response, headers, url, request):
        self.response = response
        self.headers = headers
        self.url = url
        self.request = request

    def __getattr__(self, key):
        """ get attributes from the response """
        return getattr(self.response, key)

    def __getitem__(self, key):
        """ get items from the response """
        return self.response[key]

    def __iter__(self):
        """ iterate over the response """
        return iter(self.response)

    def __str__(self):
        """ use the string of the response """
        return str(self.response)

    def __repr__(self):
        """ use the representation of the response """
        return repr(self.response)

    def __len__(self):
        """ get the lenght of the response """
        return len(self.response)


class handler_decorator:
    """
        A decorator for requests handlers

    implements the ``_error_handling`` argument

    Parameters
    ----------
    handler : function
        The error handler to decorate
    """

    def __init__(self, handler):
        functools.update_wrapper(self, handler)

    def __call__(self, request, error_handling=True):
        if error_handling:
            return self.__wrapped__(request)
        else:
            return request

    def __repr__(self):
        return repr(self.__wrapped__)


@handler_decorator
def error_handler(request):
    """
        The default error_handler

    The decorated request will retry infinitely on any handled error
    The exceptions handled are :class:`asyncio.TimeoutError` and
    :class:`exceptions.RateLimitExceeded`
    """

    @functools.wraps(request)
    async def decorated_request(timeout=10, **kwargs):
        while True:
            try:
                with aiohttp.Timeout(timeout):
                    return await request(**kwargs)

            except exceptions.RateLimitExceeded as e:
                traceback.print_exc(file=sys.stderr)
                delay = int(e.reset_in) + 1
                print("sleeping for %ds" % delay, file=sys.stderr)
                await asyncio.sleep(delay)

            except asyncio.TimeoutError:
                print("Request timed out, retrying", file=sys.stderr)

            except:
                raise

    return decorated_request


def get_args(func, skip=0):
    """
        Hackish way to get the arguments of a function

    Parameters
    ----------
    func : function
        Function to get the arguments from
    skip : :obj:`int`, optional
        Arguments to skip, defaults to 0 set it to 1 to skip the
        ``self`` argument of a method.

    Returns
    -------
    tuple
        Function's arguments
    """
    argcount = func.__code__.co_argcount
    return func.__code__.co_varnames[skip:argcount]


def print_error(msg=None, stderr=sys.stderr, error=None):
    """
        Print an exception and its traceback to stderr

    Parameters
    ----------
    msg : :obj:`str`, optional
        A message to add to the error
    stderr : file object
        A file object to write the errors to
    """
    output = [] if msg is None else [msg]
    output.append(traceback.format_exc().strip())

    print(*output, sep='\n', file=stderr)


def loads(json_data, *args, encoding="utf-8", **kwargs):
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

    return json.loads(json_data, *args, object_hook=JSONObject, **kwargs)


def media_chunks(media, chunk_size, media_size=None):
    """
        read the file by chunks

    Parameters
    ----------
    media : file
        The file object to read
    chunk_size : int
        The size of a chunk in bytes
    media_size : :obj:`int`, optional
        Size of the file in bytes

    Yields
    ------
    bytes
        A chunk of the file
    """
    if media_size is None:
        media_size = get_size(media)

    while media.tell() < media_size:
        yield media.read(chunk_size)


def convert(img, formats):
    """
        Convert the image to all the formats specified

    Parameters
    ----------
    img : PIL.Image.Image
        The image to convert
    formats : list
        List of all the formats to use

    Yields
    ------
    io.BytesIO
        A file object containing the converted image
    """
    for kwargs in formats:
        f = io.BytesIO()
        img.save(f, **kwargs)
        yield f


def optimize_media(file_, max_size, formats):
    """
        Optimize an image

    Resize the picture to the ``max_size``, defaulting to the large
    photo size of Twitter in :meth:`PeonyClient.upload_media` when
    used with the ``optimize_media`` argument.

    Parameters
    ----------
    file_ : file object
        the file object of an image
    max_size : :obj:`tuple` or :obj:`list` of :obj:`int`
        a tuple in the format (width, height) which is maximum size of
        the picture returned by this function
    formats : :obj`list` or :obj:`tuple` of :obj:`dict`
        a list of all the formats to convert the picture to

    Returns
    -------
    file
        The smallest file created in this function
    """
    img = Image.open(file_)
    ratio = max(hw / max_hw for hw, max_hw in zip(img.size, max_size))

    # resize the picture (defaults to the 'large' photo size of Twitter
    # in peony.PeonyClient.upload_media)
    if ratio > 1:
        size = tuple(int(hw // ratio) for hw in img.size)
        img = img.resize(size, Image.ANTIALIAS)

    files = list(convert(img, formats))

    # do not close a file opened by the user
    # only close if a filename was given
    if not hasattr(file_, 'read'):
        img.close()

    files.sort(key=get_size)
    media = files.pop(0)

    for f in files:
        if not f.closed:
            f.close()

    return media


def reset_io(func):
    """
    A decorator to set the pointer of the file to beginning
    of the file before and after the decorated function
    """
    @functools.wraps(func)
    def decorated(media):
        media.seek(0)
        result = func(media)
        media.seek(0)

        return result

    return decorated


@reset_io
def get_media_metadata(media):
    """
        Get the metadata of the file

    Parameters
    ----------
    media : file
        The file to analyze

    Returns
    -------
    str
        The mimetype of the media
    str
        The category of the media on Twitter
    bool
        Tell whether this file is an image or a video
    """
    media_type, media_category = get_type(media)
    is_image = not (media_type.endswith('gif')
                    or media_type.startswith('video'))

    return media_type, media_category, is_image


def get_image_metadata(file_):
    """
        Get all the file's metadata and read any kind of file object

    Parameters
    ----------
    file_ : file object
        A file object of the image

    Returns
    -------
    str
        The mimetype of the media
    str
        The category of the media on Twitter
    bool
        Tell whether this file is an image or a video
    str
        Path to the file
    """
    # try to get the path no matter how the input is
    if isinstance(file_, str):
        path = urlparse(file_).path.strip(" \"'")

        with open(path, 'rb') as original:
            return (*get_media_metadata(original), path)

    elif hasattr(file_, 'read'):
        return (*get_media_metadata(file_), file_)
    else:
        raise TypeError("upload_media input must be a file object or a"
                        "filename")


@reset_io
def get_size(media):
    """
        Get the size of a file

    Parameters
    ----------
    media : file object
        The file object of the media

    Returns
    -------
    int
        The size of the file
    """
    media.seek(0, os.SEEK_END)
    return media.tell()


@reset_io
def get_type(media, path=None):
    """
    Parameters
    ----------
    media : file object
        A file object of the image
    path : str, optional
        The path to the file

    Returns
    -------
    str
        The mimetype of the media
    str
        The category of the media on Twitter
    """
    if magic:
        media_type = mime.from_buffer(media.read(1024))
    elif path:
        media_type = mime.guess_type(path)
    else:
        raise RuntimeError("Cannot guess mimetype of media")

    if media_type.startswith('video'):
        media_category = "tweet_video"
    elif media_type.endswith('gif'):
        media_category = "tweet_gif"
    else:
        media_category = "tweet_image"

    return media_type, media_category
