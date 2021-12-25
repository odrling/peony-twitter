# -*- coding: utf-8 -*-

import asyncio
import io
import logging
import mimetypes
import os
import pathlib
import sys
import tempfile
import traceback
from concurrent.futures import ProcessPoolExecutor
from functools import wraps
from unittest.mock import patch

import aiohttp
import pytest

import peony
from peony import data_processing, exceptions, utils

from . import MockResponse, create_future, dummy


def builtin_mimetypes(func):

    @wraps(func)
    async def decorated(*args, **kwargs):
        with patch.object(utils, 'magic') as magic:
            magic.__bool__.return_value = False
            with patch.object(utils, 'mime') as mime:
                mime.guess_type.side_effect = mimetypes.MimeTypes().guess_type

                await func(*args, **kwargs)

    return decorated


@pytest.fixture
def json_data():
    return data_processing.JSONData({'a': 1, 'b': 2})


@pytest.fixture
def response(json_data):
    return data_processing.PeonyResponse(data=json_data,
                                         headers={},
                                         url="",
                                         request={})


@pytest.fixture
def executor():
    return ProcessPoolExecutor()


@pytest.fixture
def session(event_loop):
    with aiohttp.ClientSession(loop=event_loop):
        yield session


@pytest.mark.asyncio
async def test_error_handler_rate_limit():
    global tries
    tries = 3

    async def rate_limit(**kwargs):
        global tries
        tries -= 1

        if tries > 0:
            response = MockResponse(error=88,
                                    headers={'X-Rate-Limit-Reset': 0})
            await exceptions.throw(response)

    with patch.object(asyncio, 'sleep', side_effect=dummy):
        await utils.DefaultErrorHandler(rate_limit, tries=tries)(url="http://")


@pytest.mark.asyncio
async def test_error_handler_service_unavailable():
    async def service_unavailable(**kwargs):
        raise exceptions.HTTPServiceUnavailable()

    with patch.object(asyncio, 'sleep', side_effect=dummy) as sleep:
        with pytest.raises(exceptions.HTTPServiceUnavailable):
            await utils.DefaultErrorHandler(service_unavailable)()

        assert sleep.called


@pytest.mark.asyncio
async def test_error_handler_client_error():
    global tries
    tries = 3

    async def client_error(**kwargs):
        global tries
        tries -= 1

        if tries > 0:
            raise aiohttp.ClientError()

    await utils.DefaultErrorHandler(client_error)()


@pytest.mark.asyncio
async def test_error_handler_asyncio_timeout(event_loop):
    global tries
    tries = 3

    async def timeout(**kwargs):
        global tries
        tries -= 1

        if tries > 0:
            raise asyncio.TimeoutError

    fut = create_future(event_loop)
    coro = utils.DefaultErrorHandler(timeout)(future=fut, url="http://")
    await coro
    assert tries == 0


@pytest.mark.asyncio
async def test_error_handler_other_exception():
    async def error(**kwargs):
        raise exceptions.PeonyException

    with pytest.raises(exceptions.PeonyException):
        await utils.DefaultErrorHandler(error)()


@pytest.mark.asyncio
async def test_error_handler_response():
    async def request(**kwargs):
        return MockResponse(data=MockResponse.message)

    resp = await utils.DefaultErrorHandler(request)()
    text = await resp.text()
    assert text == MockResponse.message


@pytest.mark.asyncio
async def test_error_handler_base_object():
    global called
    called = False

    class ObjectErrorHandler(utils.DefaultErrorHandler, object,
                             metaclass=utils.MetaErrorHandler):

        @utils.ErrorHandler.handle(exceptions.PeonyException)
        def handle_peony_exception(self):
            global called
            called = True
            return utils.ErrorHandler.RAISE

    async def error(**kwargs):
        raise exceptions.PeonyException

    try:
        await ObjectErrorHandler(error)()
    except exceptions.PeonyException:
        assert called
    else:
        pytest.fail("PeonyException not raised")


class ErrorHandlerWithException(utils.ErrorHandler):

    @utils.ErrorHandler.handle(Exception)
    def whoops_handler(self):
        raise RuntimeError


@pytest.mark.asyncio
async def test_error_handler_with_exception():
    async def raise_exception(**kwargs):
        raise Exception

    with pytest.raises(RuntimeError):
        await ErrorHandlerWithException(raise_exception)()


def test_get_args():
    def test(a, b, c):
        pass

    assert utils.get_args(test) == ('a', 'b', 'c')
    assert utils.get_args(test, skip=1) == ('b', 'c')
    assert utils.get_args(test, skip=3) == tuple()


def test_get_args_class():

    class Test():

        def __call__(self, a, b, c):
            pass

    test = Test()

    assert utils.get_args(test) == ('self', 'a', 'b', 'c')
    assert utils.get_args(test, skip=1) == ('a', 'b', 'c')
    assert utils.get_args(test, skip=4) == tuple()


def setup_logger(logger):
    error = io.StringIO()
    h = logging.StreamHandler(stream=error)
    h.setLevel(logging.ERROR)
    logger.addHandler(h)

    return error


@pytest.mark.parametrize('logger', [None, logging.getLogger(__name__)])
def test_log_error(logger):
    if logger is None:
        _logger = logging.getLogger("peony.utils")
    else:
        _logger = logger

    error = setup_logger(_logger)

    try:
        raise RuntimeError

    except RuntimeError:
        for exc_info in (None, sys.exc_info()):
            utils.log_error(MockResponse.message, exc_info=exc_info,
                            logger=logger)

            error.seek(0)
            output = error.read()
            assert traceback.format_exc().strip() in output
            assert MockResponse.message in output


def test_log_error_no_info():
    logger = logging.getLogger("peony.utils")
    error = setup_logger(logger)
    utils.log_error(exc_info=(None, None, None), logger=logger)

    assert error.tell() == 0


@pytest.mark.asyncio
async def test_get_type(medias):
    async def test(media, chunk_size=1024):
        f = await media.download(chunk=chunk_size)
        media_type = await utils.get_type(f)
        assert media_type == media.type

    tasks = [test(media) for media in medias.values()]
    await asyncio.gather(*tasks)


@pytest.mark.asyncio
async def test_get_type_exception():
    with pytest.raises(TypeError):
        await utils.get_type(b"")


@pytest.mark.asyncio
@builtin_mimetypes
async def test_get_type_builtin(medias):
    async def test(media, chunk_size=1024):
        f = io.BytesIO(await media.download(chunk=chunk_size))
        media_type = await utils.get_type(f, media.filename)
        assert media_type == media.type

    tasks = [test(media) for media in medias.values()]
    await asyncio.gather(*tasks)


@pytest.mark.asyncio
@builtin_mimetypes
async def test_get_type_builtin_exception(medias):
    media = medias['lady_peony']
    f = io.BytesIO(await media.download(chunk=1024))
    with pytest.raises(RuntimeError):
        await utils.get_type(f)


def test_get_category():
    assert utils.get_category("image/png") == "tweet_image"
    assert utils.get_category("image/gif") == "tweet_gif"
    assert utils.get_category("video/mp4") == "tweet_video"


def test_get_category_exception():
    with pytest.raises(RuntimeError):
        utils.get_category("")


@pytest.mark.asyncio
async def test_get_size():
    f = io.BytesIO(bytes(10000))
    assert await utils.get_size(f) == 10000
    assert f.tell() == 0


@pytest.mark.online
@pytest.mark.asyncio
async def test_get_size_request(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as req:
            assert await utils.get_size(req) == 302770


@pytest.mark.asyncio
async def test_get_size_exception():
    with pytest.raises(TypeError):
        await utils.get_size("")


@pytest.mark.asyncio
async def test_execute():
    def test():
        return 1

    async def async_test():
        return 1

    assert await utils.execute(test()) == 1
    assert await utils.execute(async_test()) == 1


def convert(img, formats):
    imgs = []
    for kwargs in formats:
        i = io.BytesIO()
        img.save(i, **kwargs)
        imgs.append(i)

    return imgs


def get_size(f):
    f.seek(0, os.SEEK_END)
    return f.tell()


@pytest.mark.asyncio
async def test_get_media_metadata(medias):
    async def test(media):
        data = await media.download(chunk=1024)
        media_metadata = await utils.get_media_metadata(data)
        assert media_metadata == (media.type, media.category)

    tasks = [test(media) for media in medias.values()]
    await asyncio.gather(*tasks)


@pytest.mark.asyncio
async def test_get_media_metadata_filename():
    with tempfile.NamedTemporaryFile('w+b') as tmp:
        with pytest.raises(TypeError):
            await utils.get_media_metadata(tmp.name)


@pytest.mark.asyncio
async def test_get_media_metadata_path():
    with tempfile.NamedTemporaryFile('w+b') as tmp:
        path = pathlib.Path(tmp.name)
        with pytest.raises(TypeError):
            await utils.get_media_metadata(path)


@pytest.mark.asyncio
async def test_get_media_metadata_file(medias):
    media = medias['lady_peony']
    data = io.BytesIO(await media.download())

    with pytest.raises(TypeError):
        await utils.get_media_metadata(data)


@pytest.mark.asyncio
async def test_get_media_metadata_exception():
    with pytest.raises(TypeError):
        await utils.get_media_metadata([])


def test_set_debug():
    with patch.object(logging, 'basicConfig') as basicConfig:
        peony.set_debug()
        assert peony.logger.level == logging.DEBUG
        basicConfig.assert_called_with(level=logging.WARNING)
