# -*- coding: utf-8 -*-

import asyncio
import logging
import os
import sys

import peony

from . import exceptions

try:
    import magic
    mime = magic.Magic(mime=True)
except:  # pragma: no cover
    import mimetypes
    mime = mimetypes.MimeTypes()
    magic = None


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
        """  """
        def handler_decorator(handler):
            return Handle(handler, *exceptions)

        return handler_decorator

    async def __handle(self, exception_class, **kwargs):
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
            return await self.__handle(base, **kwargs)

        return ErrorHandler.RAISE

    async def __call__(self, future=None, **kwargs):
        while True:
            try:
                if future is None:
                    return await self.__request(**kwargs)
                else:
                    return await self.__request(future=future, **kwargs)
            except Exception as exc:
                reply = await self.__handle(exc.__class__, exception=exc,
                                            **kwargs)
                if isinstance(reply, Exception):
                    exc = reply
                if reply is not ErrorHandler.RETRY:
                    _logger.debug("raising exception")
                    if future is not None:
                        future.set_exception(exc)
                    else:
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

    def __init__(self, request):
        super().__init__(request)
        self.tries = 3

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
    if magic:
        if not media:
            raise TypeError("Media data is empty")

        _logger.debug("guessing mimetype using magic")
        media_type = mime.from_buffer(media[:1024])
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
