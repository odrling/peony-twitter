# -*- coding: utf-8 -*-
import asyncio
import logging
import mimetypes
import os
import sys
from functools import partial
from itertools import chain
from typing import Any, Iterable, Mapping

import aiohttp

import peony

from . import exceptions

mime = mimetypes.MimeTypes()

try:
    import magic
    magic_mime = magic.Magic(mime=True)
    magic_module = True
except Exception:  # pragma: no cover
    magic_module = False


_logger = logging.getLogger(__name__)


class Handle:

    __slots__ = 'exceptions', 'handler'

    def __init__(self, handler, *exceptions):
        self.exceptions = exceptions
        self.handler = handler


class MetaErrorHandler(type):

    def __new__(cls, name, bases, attrs, **kwargs):
        """ put the :class:`~peony.utils.Handle`s in the right place """
        handlers = {}

        for base in bases:
            if hasattr(base, '_handlers'):
                for key, value in base._handlers.items():
                    handlers[key] = value

        for attr in attrs.values():
            if isinstance(attr, Handle):
                for exception in attr.exceptions:
                    handlers[exception] = attr.handler

        attrs['_handlers'] = handlers

        return super().__new__(cls, name, bases, attrs)


class ErrorHandler(metaclass=MetaErrorHandler):
    """
        Basic error handler

    This error handler just raises all the exceptions that it receives.
    """

    RETRY = CONTINUE = OK = True
    RAISE = STOP = False

    def __init__(self, request):
        self.__request = request

    @staticmethod
    def handle(*exceptions):
        def handler_decorator(handler):
            return Handle(handler, *exceptions)

        return handler_decorator

    async def _handle(self, exception_class, **kwargs):
        if exception_class in self._handlers:
            handler = self._handlers[exception_class]
            args = get_args(handler, skip=1)
            handler_kwargs = {key: kwargs[key] for key in args
                              if key in kwargs}
            try:
                return await execute(handler(self, **handler_kwargs))
            except Exception as exc:
                return exc

        for base in exception_class.__bases__:
            return await self._handle(base, **kwargs)

        return ErrorHandler.RAISE

    async def __call__(self, future=None, **kwargs):
        while True:
            try:
                if future is None:
                    return await self.__request(**kwargs)
                else:
                    return await self.__request(future=future, **kwargs)
            except Exception as exc:
                status = await self._handle(exc.__class__, exception=exc,
                                            **kwargs)

                if isinstance(status, Exception):
                    exc = status
                    status = ErrorHandler.RAISE

                if status is not ErrorHandler.RETRY:
                    _logger.debug("raising exception")
                    if future is not None and not future.done():
                        future.set_exception(exc)
                        return

                    raise exc


class DefaultErrorHandler(ErrorHandler):
    """
        The default error_handler

    The decorated request will retry infinitely on any handled error
    The exceptions handled are :class:`TimeoutError`,
    :class:`asyncio.TimeoutError`,
    :class:`exceptions.RateLimitExceeded` and
    :class:`exceptions.ServiceUnavailable`
    """

    def __init__(self, request, tries=3):
        super().__init__(request)
        self.tries = tries

    @ErrorHandler.handle(exceptions.RateLimitExceeded)
    async def handle_rate_limits(self, exception, url):
        delay = int(exception.reset_in) + 1
        fmt = "Sleeping for {}s (rate limit exceeded on endpoint {})"
        _logger.warning(fmt.format(delay, url))
        await asyncio.sleep(delay)
        return ErrorHandler.RETRY

    @ErrorHandler.handle(asyncio.TimeoutError, TimeoutError)
    def handle_timeout_error(self, url):
        fmt = "Request to {url} timed out, retrying"
        _logger.info(fmt.format(url=url))
        return ErrorHandler.RETRY

    @ErrorHandler.handle(exceptions.HTTPServiceUnavailable)
    async def handle_service_unavailable(self):
        self.tries -= 1
        if self.tries > 0:
            _logger.info("Service temporarily unavailable, "
                         "request will be made again very soon")
            await asyncio.sleep(0.5)
            return ErrorHandler.RETRY

    @ErrorHandler.handle(aiohttp.ClientError)
    async def handle_client_error(self, exception=None):
        assert exception is not None
        self.tries -= 1
        if self.tries > 0:
            _logger.info(str(exception))
            return ErrorHandler.RETRY


def get_args(func, skip=0):
    """
        Hackish way to get the arguments of a function

    Parameters
    ----------
    func : callable
        Function to get the arguments from
    skip : int, optional
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


def log_error(msg=None, exc_info=None, logger=None, **kwargs):
    """
        log an exception and its traceback on the logger defined

    Parameters
    ----------
    msg : str, optional
        A message to add to the error
    exc_info : tuple
        Information about the current exception
    logger : logging.Logger
        logger to use
    """
    if logger is None:
        logger = _logger

    if not exc_info:
        exc_info = sys.exc_info()

    if msg is None:
        msg = ""

    exc_class, exc_msg, _ = exc_info

    if all(info is not None for info in exc_info):
        logger.error(msg, exc_info=exc_info)


async def get_media_metadata(data, path=None):
    """
        Get all the file's metadata and read any kind of file object

    Parameters
    ----------
    data : bytes
        first bytes of the file (the mimetype shoudl be guessed from the
        file headers
    path : str, optional
        path to the file

    Returns
    -------
    str
        The mimetype of the media
    str
        The category of the media on Twitter
    """
    if isinstance(data, bytes):
        media_type = await get_type(data, path)

    else:
        raise TypeError("get_metadata input must be a bytes")

    media_category = get_category(media_type)

    _logger.info("media_type: %s, media_category: %s" % (media_type,
                                                         media_category))

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
    if hasattr(media, 'seek'):
        await execute(media.seek(0, os.SEEK_END))
        size = await execute(media.tell())
        await execute(media.seek(0))
    elif hasattr(media, 'headers'):
        size = int(media.headers['Content-Length'])
    elif isinstance(media, bytes):
        size = len(media)
    else:
        raise TypeError("Can't get size of media of type:",
                        type(media).__name__)

    _logger.info("media size: %dB" % size)
    return size


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
    if magic_module:
        if not media:
            raise TypeError("Media data is empty")

        _logger.debug("guessing mimetype using magic")
        media_type = magic_mime.from_buffer(media[:1024])
    else:
        media_type = None
        if path:
            _logger.debug("guessing mimetype using built-in module")
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
    coro : asyncio.coroutine or function
    """
    if asyncio.iscoroutine(coro):
        return await coro
    else:
        return coro


def set_debug():
    """ activates error messages, useful during development """
    logging.basicConfig(level=logging.WARNING)
    peony.logger.setLevel(logging.DEBUG)


class Entity:
    """ Helper to use Twitter entities """

    def __init__(self, original: str,
                 entity_type: str,
                 data: Mapping[str, Any]):
        self.data = data
        self.entity_type = entity_type
        self.original = original[self.start:self.end]

    def __getitem__(self, key: str) -> Any:
        return self.data[key]

    @property
    def start(self) -> int:
        return self.data['start']

    @property
    def end(self) -> int:
        return self.data['end']

    @property
    def text(self) -> str:
        """ returns text representing the entity """
        ret = {
            'urls': lambda: self.data['display_url']
        }

        return ret.get(self.entity_type, lambda: self.original)()

    @property
    def url(self) -> str:
        """ returns an url representing the entity """
        ret = {
            'urls': lambda: self.data['expanded_url'],
            'mentions': lambda: "https://twitter.com/{}".format(self.data['username']),    # noqa
            'hashtags': lambda: "https://twitter.com/hashtag/{}".format(self.data['tag'])  # noqa
        }

        return ret.get(self.entity_type, lambda: "")()


def get_twitter_entities(
    text: str,
    entities: Mapping[str, Mapping[str, Any]]
) -> Iterable[Entity]:
    """ Returns twitter entities from an entities dictionnary

    Entities are returned is reversed order for ease of use (start and end
    indexes stay the same if the string is changed in place)
    """
    return sorted(
        chain.from_iterable(
            map(partial(Entity, text, entity_type), entities)
            for entity_type, entities in entities.items()
        ),
        key=lambda e: e.start,
        reverse=True
    )
