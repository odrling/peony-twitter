import json

import aiohttp
import pytest

from peony import data_processing, exceptions

from . import MockResponse


@pytest.fixture
def json_data():
    return data_processing.JSONData({'a': 1, 'b': 2})


@pytest.fixture
def response(json_data):
    return data_processing.PeonyResponse(data=json_data,
                                         headers={},
                                         url="",
                                         request={})


def test_json_data_get(json_data):
    assert json_data.a == json_data['a'] == json_data.get('a') == 1
    assert json_data.b == json_data['b'] == json_data.get('b') == 2


def test_json_data_get_default(json_data):
    assert json_data.get('c') is None
    assert json_data.get('c', 1) == 1


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
    resp = data_processing.PeonyResponse(list(range(3)), {}, "", {})
    for i, x in enumerate(resp):
        assert i == x


def test_response_str(response):
    assert str(response) == str(response.data)


def test_response_repr(response):
    assert repr(response) == repr(response.data)


def test_response_len(response):
    assert len(response) == len(response.data)


def test_loads():
    j = data_processing.loads("""{"a": 1, "b": 2}""")
    assert isinstance(j, data_processing.JSONData)
    assert j.a == 1 and j.b == 2


@pytest.mark.asyncio
async def test_read(json_data):
    response = MockResponse(data=MockResponse.message,
                            content_type="text/plain")
    assert await data_processing.read(response) == MockResponse.message

    response = MockResponse(data=json.dumps(json_data),
                            content_type="application/json")

    data = await data_processing.read(response)
    assert all(data[key] == json_data[key]
               for key in {*data.keys(), *json_data.keys()})

    response = MockResponse(data=MockResponse.message,
                            content_type="application/octet-stream")
    data = data_processing.read(response)
    assert await data == MockResponse.message.encode()


@pytest.mark.asyncio
async def test_read_decode_error():
    response = MockResponse(data=b'\x80', content_type="text/plain")
    try:
        await data_processing.read(response, encoding='utf-8')
    except exceptions.PeonyDecodeError as exc:
        assert exc.data == b'\x80'
        assert isinstance(exc.exception, UnicodeDecodeError)
    else:
        pytest.fail("Did not raise PeonyDecoderError")


@pytest.mark.asyncio
async def test_read_json_decode_error():
    response = MockResponse(data='{', content_type="application/json")
    try:
        await data_processing.read(response, encoding='utf-8')
    except exceptions.PeonyDecodeError as exc:
        assert exc.data == b'{'
        assert isinstance(exc.exception, json.JSONDecodeError)
    else:
        pytest.fail("Did not raise PeonyDecoderError")


def download(url):

    def decorator(func):

        async def decorated():
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    json_data = await response.text()
                    data = data_processing.loads(json_data)

            await func(data)

        return decorated

    return decorator


full_text = ("@jeremycloud It's neat to have owls and raccoons around "
             "until you realize that raccoons will eat the eggs from the "
             "owl's nest https://t.co/Q0pkaU4ORH")


@pytest.mark.asyncio
@download("https://raw.githubusercontent.com/twitterdev/tweet-updates/master/"
          "samples/initial/compatibilityplus_classic_hidden_13797.json")
async def test_json_data_extended_entities(data):
    assert data.truncated
    assert data.extended_tweet
    assert data.text == full_text
    assert data.text == data.get('text')
    assert 'display_text_range' in data
    assert data.geo is None


@pytest.mark.asyncio
@download("https://raw.githubusercontent.com/twitterdev/tweet-updates/master/"
          "samples/initial/compatibilityplus_extended_13997.json")
async def test_json_data_full_text(data):
    assert not data.truncated
    assert data.text == full_text
    assert data.text == data.get('text')
    assert data.geo is None
