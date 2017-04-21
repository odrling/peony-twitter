# -*- coding: utf-8 -*-

import asyncio
import io
import mimetypes
import traceback
from functools import wraps

import aiohttp
import pytest

from peony import exceptions
from peony import utils
from . import MockResponse, medias


def builtin_mimetypes(func):

    @wraps(func)
    async def decorated(session):
        magic = utils.magic
        mime = utils.mime

        utils.magic = None
        utils.mime = mimetypes.MimeTypes()

        try:
            await func(session)
        finally:
            utils.magic = magic
            utils.mime = mime

    return decorated


@pytest.fixture
def json_data():
    return utils.JSONData({'a': 1, 'b': 2})


@pytest.fixture
def response(json_data):
    return utils.PeonyResponse(data=json_data,
                               headers={},
                               url="",
                               request={})

@pytest.yield_fixture
def session(event_loop):
    session = aiohttp.ClientSession(loop=event_loop)
    yield session
    event_loop.run_until_complete(session.close())


def test_json_data_get(json_data):
    assert json_data.a == json_data['a'] == 1
    assert json_data.b == json_data['b'] == 2


def test_json_data_set(json_data):
    json_data.c = 1
    json_data['d'] = 2
    assert json_data.c == json_data['c'] == 1
    assert json_data.d == json_data['d'] == 2


def test_json_data_del(json_data):
    del json_data.a
    del json_data['b']
    assert not hasattr(json_data, 'a') and 'a' not in json_data
    assert not hasattr(json_data, 'b') and 'b' not in json_data


def test_response_get(response):
    assert response.a == response['a'] == response.data.a


def test_response_set(response):
    response.a = 3
    response['b'] = 4
    assert response.a == response['a'] == 3
    assert response.b == response['b'] == 4


def test_response_del(response):
    del response.a
    del response['b']
    assert not hasattr(response, 'a') and 'a' not in response
    assert not hasattr(response, 'b') and 'b' not in response


def test_response_iter():
    resp = utils.PeonyResponse(list(range(3)), {}, "", {})
    for i, x in enumerate(resp):
        assert i == x


def test_response_str(response):
    assert str(response) == str(response.data)


def test_response_repr(response):
    assert repr(response) == repr(response.data)


def test_response_len(response):
    assert len(response) == len(response.data)


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
        tries -=1

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


def test_format_error():
    try:
        raise RuntimeError
    except RuntimeError:
        output = utils.format_error(MockResponse.message)
        assert traceback.format_exc().strip() in output
        assert MockResponse.message in output
        assert traceback.format_exc().strip() in utils.format_error()


def test_print_error():
    out = io.StringIO()
    try:
        raise RuntimeError
    except RuntimeError:
        utils.print_error(MockResponse, stderr=out, end='')
        out.seek(0)
        assert utils.format_error(MockResponse) == out.read()


def test_loads():
    j = utils.loads("""{"a": 1, "b": 2}""")
    assert isinstance(j, utils.JSONData)
    assert j.a == 1 and j.b == 2


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
async def test_get_type(session):
    async def test(media, session, chunk_size=1024):
        f = io.BytesIO(await media.download(session, chunk_size))
        media_type, media_category = await utils.get_type(f)
        assert media_type == media.type
        assert media_category == media.category

    tasks = [test(media, session) for media in medias.values()]
    await asyncio.gather(*tasks)

@pytest.mark.asyncio
async def test_get_type_exception():
    with pytest.raises(RuntimeError):
        await utils.get_type(io.BytesIO())


@pytest.mark.asyncio
@builtin_mimetypes
async def test_get_type_builtin(session):
    async def test(media, session, chunk_size=1024):
        f = io.BytesIO(await media.download(session, chunk_size))
        media_type, media_category = await utils.get_type(f, media.filename)
        assert media_type == media.type
        assert media_category == media.category

    tasks = [test(media, session) for media in medias.values()]
    await asyncio.gather(*tasks)


@pytest.mark.asyncio
@builtin_mimetypes
async def test_get_type_builtin_exception(session):
    media = medias['lady_peony']
    f = io.BytesIO(await media.download(session, 1024))
    with pytest.raises(RuntimeError):
        await utils.get_type(f)
