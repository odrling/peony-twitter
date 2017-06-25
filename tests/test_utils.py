# -*- coding: utf-8 -*-

import asyncio
import io
import logging
import mimetypes
import os
import pathlib
import tempfile
import traceback
from concurrent.futures import ProcessPoolExecutor
from functools import wraps
from unittest.mock import patch

import aiohttp
import pytest
from peony import data_processing, exceptions, utils

from . import MockResponse, medias


def builtin_mimetypes(func):

    @wraps(func)
    async def decorated():
        with patch.object(utils, 'magic') as magic:
            magic.__bool__.return_value = False
            with patch.object(utils, 'mime') as mime:
                mime.guess_type.side_effect = mimetypes.MimeTypes().guess_type

                await func()

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


@pytest.yield_fixture
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
            raise await exceptions.throw(response)

    await utils.error_handler(rate_limit)()


@pytest.mark.asyncio
async def test_error_handler_asyncio_timeout():
    global tries
    tries = 3

    async def timeout(**kwargs):
        global tries
        tries -= 1

        if tries > 0:
            raise asyncio.TimeoutError

    await utils.error_handler(timeout)()


@pytest.mark.asyncio
async def test_error_handler_other_exception():
    async def error(**kwargs):
        raise exceptions.PeonyException

    with pytest.raises(exceptions.PeonyException):
        await utils.error_handler(error)()


@pytest.mark.asyncio
async def test_error_handler_response():
    async def request(**kwargs):
        return MockResponse(data=MockResponse.message)

    resp = await utils.error_handler(request)()
    text = await resp.text()
    assert text == MockResponse.message


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
    warning = io.StringIO()
    h = logging.StreamHandler(stream=warning)
    h.setLevel(logging.WARNING)
    logger.addHandler(h)

    debug = io.StringIO()
    h = logging.StreamHandler(stream=debug)
    h.setLevel(logging.DEBUG)
    logger.addHandler(h)

    return warning, debug


def test_log_error():
    logger = logging.getLogger(__name__)
    warning, debug = setup_logger(logger)

    try:
        raise RuntimeError

    except RuntimeError:
        logger.setLevel(logging.WARNING)
        utils.log_error(MockResponse.message, logger=logger)

        warning.seek(0)
        output = warning.read()
        assert MockResponse.message in output
        # make sure the debug level is mentioned
        assert 'debug' in output.lower()

        logger.setLevel(logging.DEBUG)
        utils.log_error(MockResponse.message, logger=logger)

        debug.seek(0)
        output = debug.read()
        assert traceback.format_exc().strip() in output
        assert MockResponse.message in output


def test_log_error_default_logger():
    logger = logging.getLogger('peony.utils')
    logger.setLevel(logging.WARNING)

    warning, _ = setup_logger(logger)

    try:
        raise RuntimeError

    except RuntimeError:
        utils.log_error(MockResponse.message)

        warning.seek(0)
        assert MockResponse.message in warning.read()


@pytest.mark.asyncio
async def test_reset_io():
    @utils.reset_io
    async def test(media):
        assert media.tell() == 0
        media.write(MockResponse.message)
        assert media.tell() != 0

    f = io.StringIO()
    f.write("Hello World")
    assert f.tell() != 0
    await test(f)
    assert f.tell() == 0


@pytest.mark.asyncio
async def test_get_type():
    async def test(media, chunk_size=1024):
        f = io.BytesIO(await media.download(chunk=chunk_size))
        media_type = await utils.get_type(f)
        assert media_type == media.type

    tasks = [test(media) for media in medias.values()]
    await asyncio.gather(*tasks)


@pytest.mark.asyncio
async def test_get_type_exception():
    with pytest.raises(TypeError):
        await utils.get_type(io.BytesIO())


@pytest.mark.asyncio
@builtin_mimetypes
async def test_get_type_builtin():
    async def test(media, chunk_size=1024):
        f = io.BytesIO(await media.download(chunk=chunk_size))
        media_type = await utils.get_type(f, media.filename)
        assert media_type == media.type

    tasks = [test(media) for media in medias.values()]
    await asyncio.gather(*tasks)


@pytest.mark.asyncio
@builtin_mimetypes
async def test_get_type_builtin_exception():
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
async def test_get_media_metadata():
    async def test(media):
        data = await media.download(chunk=1024)
        f = io.BytesIO(data)
        media_metadata = await utils.get_media_metadata(f)
        assert media_metadata == (media.type, media.category)

    tasks = [test(media) for media in medias.values()]
    await asyncio.gather(*tasks)


@pytest.mark.asyncio
async def test_get_media_metadata_filename():
    media = medias['lady_peony']
    with tempfile.NamedTemporaryFile('w+b') as tmp:
        data = await media.download()
        tmp.write(data)

        file1_metadata = await utils.get_media_metadata(tmp.name)
        file2_metadata = await utils.get_media_metadata(tmp)

        assert all(file1_metadata[i] == file2_metadata[i] for i in range(2))
        assert file1_metadata[0] == media.type


@pytest.mark.asyncio
async def test_get_media_metadata_path():
    media = medias['lady_peony']
    with tempfile.NamedTemporaryFile('w+b') as tmp:
        data = await media.download()
        tmp.write(data)

        path = pathlib.Path(tmp.name)
        file1_metadata = await utils.get_media_metadata(path)
        file2_metadata = await utils.get_media_metadata(tmp)

        assert all(file1_metadata[i] == file2_metadata[i] for i in range(2))
        assert file1_metadata[0] == media.type


@pytest.mark.asyncio
async def test_get_media_metadata_bytes():
    media = medias['lady_peony']
    data = await media.download()
    f = io.BytesIO(data)

    file1_metadata = await utils.get_media_metadata(data)
    file2_metadata = await utils.get_media_metadata(f)

    assert all(file1_metadata[i] == file2_metadata[i] for i in range(2))
    assert file1_metadata[0] == media.type


@pytest.mark.asyncio
async def test_get_media_metadata_exception():
    with pytest.raises(TypeError):
        await utils.get_media_metadata([])
