# -*- coding: utf-8 -*-

import asyncio
import functools
import logging
import os

from . import exceptions

try:
    import magic
    mime = magic.Magic(mime=True)
except:  # pragma: no cover
    import mimetypes
    mime = mimetypes.MimeTypes()
    magic = None


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
                logging.warning(fmt.format(delay, url))
                await asyncio.sleep(delay)

            except asyncio.TimeoutError:
                fmt = "Request to {url} timed out, retrying"
                logging.info(fmt.format(url=url))

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


def log_error(msg=None, logger=None, **kwargs):
    """
        log an exception and its traceback on the logger defined

    Parameters
    ----------
    msg : :obj:`str`, optional
        A message to add to the error
    logger : logging.Logger
        the logger to use
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    if logging.DEBUG < logger.level <= logging.WARNING:
        logger.warning("An error occurred, set the logger to the debug level"
                       "to see the full report.\n" + msg)
    else:
        logger.debug(msg, exc_info=True)


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


async def get_media_metadata(file_, path=None):
    """
        Get all the file's metadata and read any kind of file object

    Parameters
    ----------
    file_ : file object
        file object corresponding to the media
    path : :obj:`str`, optional
        path to the file

    Returns
    -------
    str
        The mimetype of the media
    str
        The category of the media on Twitter
    """
    # try to get the path no matter what the input is
    if hasattr(file_, 'read'):
        media_type = await get_type(file_, path)

    else:
        raise TypeError("get_metadata input must be a file object")

    media_category = get_category(media_type)

    return media_type, media_category


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
        if media_type == 'application/x-empty':
            raise TypeError("No data in media")
    else:
        media_type = None
        if path:
            media_type = mime.guess_type(path)[0]

        if media_type is None:
            msg = ("Could not guess the mimetype of the media.\n"
                   "Please consider installing python-magic\n"
                   "(pip3 install peony-twitter[magic])")
            raise RuntimeError(msg)

    return media_type


def get_category(media_type):
    if media_type.startswith('video'):
        return "tweet_video"
    elif media_type.endswith('gif'):
        return "tweet_gif"
    elif media_type.startswith('image'):
        return "tweet_image"
    else:
        raise RuntimeError("The provided media cannot be handled.\n"
                           "mimetype: %s" % media_type)


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


class chunks:  # noqa

    def __init__(self, media, chunk_size):
        self.media = media
        self.chunk_size = chunk_size
        self.i = -1

    async def __aiter__(self):
        return self

    async def __anext__(self):
        self.i += 1

        chunk = await execute(self.media.read(self.chunk_size))
        if not chunk:
            raise StopAsyncIteration()

        return self.i, chunk
