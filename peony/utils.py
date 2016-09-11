# -*- coding: utf-8 -*-

import asyncio
import io
import functools
import json
import os
import sys
import traceback
from urllib.parse import urlparse

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
    >>> obj['key'] is obj.key  # returns True
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
    """

    def __init__(self, response, headers, url, request):
        """ keep informations about the response as instance attributes """
        self.response = response
        self.headers = headers
        self.url = url
        self.request = request

    def __getattr__(self, key):
        return getattr(self.response, key)

    def __getitem__(self, key):
        return self.response[key]

    def __iter__(self):
        return iter(self.response)

    def __str__(self):
        return str(self.response)

    def __repr__(self):
        return repr(self.response)

    def __len__(self):
        return len(self.response)


class handler_decorator:

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
    @functools.wraps(request)
    async def decorated_request(**kwargs):
        while True:
            try:
                return await request(**kwargs)
            except exceptions.RateLimitExceeded as e:
                traceback.print_exc(file=sys.stderr)
                # print(e, file=sys.stderr)
                delay = int(e.reset_in) + 1
                print("sleeping for %ds" % delay, file=sys.stderr)
                await asyncio.sleep(delay)
            except TimeoutError:
                print("connection timed out", file=sys.stderr)
            else:
                raise

    return decorated_request


def get_args(func, skip=0):
    """
        hackish way to get the arguments of a function

    Arguments:
        func (function): function to get the arguments from
        skip (Optional[int]): arguments to skip, defaults to 0
                              set it to 1 to skip the ``self`` argument
                              of a method.

    """
    argcount = func.__code__.co_argcount
    return func.__code__.co_varnames[skip:argcount]


def print_error(msg=None, stderr=sys.stderr):
    output = [] if msg is None else [msg]
    output.append(traceback.format_exc().strip())

    print(*output, sep='\n', file=stderr)


def loads(json_data, *args, encoding="utf-8", **kwargs):
    """ custom loads function with an object_hook and automatic decoding """
    if isinstance(json_data, bytes):
        json_data = json_data.decode(encoding)

    return json.loads(json_data, *args, object_hook=JSONObject, **kwargs)


def media_chunks(media, chunk_size, media_size):
    while media.tell() < media_size:
        yield media.read(chunk_size)


def convert(img, formats):
    for kwargs in formats:
        f = io.BytesIO()
        img.save(f, **kwargs)
        yield f


def optimize_media(file_, max_size, formats):
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
    @functools.wraps(func)
    def decorated(media):
        media.seek(0)
        result = func(media)
        media.seek(0)

        return result

    return decorated


@reset_io
def get_media_metadata(f):
    media_type, media_category = get_type(f)
    is_image = not (media_type.endswith('gif')
                    or media_type.startswith('video'))

    return media_type, media_category, is_image


def get_image_metadata(file_):
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
    media.seek(0, os.SEEK_END)
    return media.tell()


@reset_io
def get_type(media, path=None):
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
