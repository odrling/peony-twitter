# -*- coding: utf-8 -*-

import asyncio
import functools
import io
import json
import os
import pathlib
import sys
import traceback
from urllib.parse import urlparse

from . import exceptions, general

try:
    import PIL.Image
except ImportError:  # pragma: no cover
    PIL = None

try:
    from aiofiles import open
except ImportError:  # pragma: no cover
    pass

try:
    import magic
    mime = magic.Magic(mime=True)
except:  # pragma: no cover
    import mimetypes
    mime = mimetypes.MimeTypes()
    magic = None


class JSONData(dict):
    """
        A dict in which you can access items as attributes

    >>> obj = JSONData(key=True)
    >>> obj['key'] is obj.key
    True
    """

    def __getattr__(self, key):
        if key in self:
            return self[key]
        raise AttributeError("%s has no property named %s." %
                             (self.__class__.__name__, key))

    def __delattr__(self, item):
        del self[item]

    def __setattr__(self, key, value):
        self[key] = value


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
        super().__setattr__('data', data)
        super().__setattr__('headers', headers)
        super().__setattr__('url', url)
        super().__setattr__('request', request)

    def __getattr__(self, key):
        """ get attributes from the data """
        return getattr(self.data, key)

    def __getitem__(self, key):
        """ get items from the data """
        return self.data[key]

    def __contains__(self, item):
        return item in self.data

    def __iter__(self):
        """ iterate over the data """
        return iter(self.data)

    def __str__(self):
        """ use the string of the data """
        return str(self.data)

    def __repr__(self):
        """ use the representation of the data """
        return repr(self.data)

    def __len__(self):
        """ get the length of the data """
        return len(self.data)

    def __setitem__(self, key, value):
        self.data[key] = value
    __setattr__ = __setitem__

    def __delitem__(self, key):
        del self.data[key]
    __delattr__ = __delitem__


def error_handler(request):
    """
        The default error_handler

    The decorated request will retry infinitely on any handled error
    The exceptions handled are :class:`asyncio.TimeoutError` and
    :class:`exceptions.RateLimitExceeded`
    """

    @functools.wraps(request)
    async def decorated_request(url=None, **kwargs):
        while True:
            try:
                return await request(url=url, **kwargs)

            except exceptions.RateLimitExceeded as e:
                delay = int(e.reset_in) + 1
                fmt = "Sleeping for {}s (rate limit exceeded on endpoint {})"
                print(fmt.format(delay, url), file=sys.stderr)
                await asyncio.sleep(delay)

            except asyncio.TimeoutError:
                fmt = "Request to {url} timed out, retrying"
                print(fmt.format(url=url), file=sys.stderr)

            except:
                raise

    return decorated_request


def get_args(func, skip=0):
    """
        Hackish way to get the arguments of a function

    Parameters
    ----------
    func : callable
        Function to get the arguments from
    skip : :obj:`int`, optional
        Arguments to skip, defaults to 0 set it to 1 to skip the
        ``self`` argument of a method.

    Returns
    -------
    tuple
        Function's arguments
    """

    code = getattr(func, '__code__', None)
    if code is None:
        code = func.__call__.__code__

    return code.co_varnames[skip:code.co_argcount]


def format_error(msg=None):
    """
        return a string representing an exception and its traceback

    Parameters
    ----------
    msg : :obj:`str`, optional
        A message to add to the error
    """
    exc = traceback.format_exc().strip()
    if msg is None:
        return exc
    else:
        return "{exc}\n{msg}".format(exc=exc, msg=msg)


def print_error(msg=None, stderr=sys.stderr, **kwargs):
    """
        Print an exception and its traceback to stderr

    Parameters
    ----------
    msg : :obj:`str`, optional
        A message to add to the error
    stderr : file object
        A file object to write the errors to
    """
    print(format_error(msg), file=stderr, **kwargs)


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

    return json.loads(json_data, *args, object_hook=JSONData, **kwargs)


def convert(img, formats):
    """
        Convert the image to all the formats specified

    Parameters
    ----------
    img : PIL.Image.Image
        The image to convert
    formats : list
        List of all the formats to use

    Returns
    -------
    io.BytesIO
        A file object containing the converted image
    """
    media = None
    min_size = 0

    for kwargs in formats:
        f = io.BytesIO()
        img.save(f, **kwargs)
        size = f.tell()

        if media is None or size < min_size:
            if media is not None:
                media.close()

            media = f
            min_size = size
        else:
            f.close()

    return media


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
    if not PIL:
        msg = ("Pillow must be installed to optimize a media\n"
               "(pip3 install peony[Pillow])")
        raise RuntimeError(msg)

    img = PIL.Image.open(file_)

    # resize the picture (defaults to the 'large' photo size of Twitter
    # in peony.PeonyClient.upload_media)
    ratio = max(hw / max_hw for hw, max_hw in zip(img.size, max_size))

    if ratio > 1:
        size = tuple(int(hw // ratio) for hw in img.size)
        img = img.resize(size, PIL.Image.ANTIALIAS)

    media = convert(img, formats)

    # do not close a file opened by the user
    # only close if a filename was given
    if not hasattr(file_, 'read'):
        img.close()

    return media


def reset_io(func):
    """
    A decorator to set the pointer of the file to beginning
    of the file before and after the decorated function
    """
    @functools.wraps(func)
    async def decorated(media, *args, **kwargs):
        if await execute(media.tell()):
            await execute(media.seek(0))

        result = await func(media, *args, **kwargs)

        if await execute(media.tell()):
            await execute(media.seek(0))

        return result

    return decorated


async def get_media_metadata(file_):
    """
        Get all the file's metadata and read any kind of file object

    Parameters
    ----------
    file_ : :obj:`str`, :obj:`bytes` or file object
        A filename, binary data or file object corresponding to
        the media

    Returns
    -------
    str
        The mimetype of the media
    str
        The category of the media on Twitter
    bool
        Tell whether this file is an image or a video
    :obj:`str` or file object
        Path to the file
    """
    # try to get the path no matter what the input is
    if isinstance(file_, pathlib.Path):
        file_ = str(file_)

    if isinstance(file_, str):
        file_ = urlparse(file_).path.strip(" \"'")

        original = await execute(open(file_, 'rb'))
        media_type, media_category = await get_type(original, file_)
        await execute(original.close())

    elif hasattr(file_, 'read'):
        media_type, media_category = await get_type(file_)

    elif isinstance(file_, bytes):
        file_ = io.BytesIO(file_)
        media_type, media_category = await get_type(file_)

    else:
        raise TypeError("upload_media input must be a file object or a"
                        "filename or binary data")

    is_image = media_type.startswith('image')

    return media_type, media_category, is_image, file_


async def get_size(media):
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
    await execute(media.seek(0, os.SEEK_END))
    size = await execute(media.tell())
    await execute(media.seek(0))
    return size


@reset_io
async def get_type(media, path=None):
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
        media_type = mime.from_buffer(await execute(media.read(1024)))
    else:
        media_type = None
        if path:
            print("path:", str(path))
            media_type = mime.guess_type(path)[0]

        if media_type is None:
            msg = ("Could not guess the mimetype of the media.\n"
                   "Please consider installing python-magic\n"
                   "(pip3 install peony-twitter[magic])")
            raise RuntimeError(msg)

    if media_type.startswith('video'):
        media_category = "tweet_video"
    elif media_type.endswith('gif'):
        media_category = "tweet_gif"
    elif media_type.startswith('image'):
        media_category = "tweet_image"
    else:
        raise RuntimeError("The provided media cannot be handled.\n"
                           "mimetype: %s" % media_type)

    return media_type, media_category


async def execute(coro):
    """
        run a function or coroutine

    Parameters
    ----------
    coro : coroutine or function
    """
    if asyncio.iscoroutine(coro):
        return await coro
    else:
        return coro


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
    ctype = response.headers.get('Content-Type', "").lower()

    try:
        if "application/json" in ctype:
            return await response.json(encoding=encoding, loads=loads)

        if "text" in ctype:
            return await response.text(encoding=encoding)

    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        data = await response.read()
        raise exceptions.PeonyDecodeError(response=response,
                                          data=data,
                                          exception=exc)

    return await response.read()
