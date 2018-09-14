
import asyncio
import io
from unittest.mock import patch

import pytest
from peony import BasePeonyClient, iterators, requests
from peony.api import APIPath

from . import dummy

url = "http://whatever.com/endpoint.json"


@pytest.fixture
def api_path():
    client = BasePeonyClient("", "", loop=asyncio.get_event_loop())
    with patch.object(client, 'request', side_effect=dummy):
        yield APIPath(['http://whatever.com', 'endpoint'], '.json', client)


@pytest.fixture
def request(api_path):
    return requests.Request(api_path, 'get')


def test_sanitize_params(request):
    val = [1, 2, 3]
    kwargs, skip_params = request.sanitize_params('get', _test=1, boom=0,
                                                  test=True, val=val, a=None,
                                                  text="aaa")

    assert kwargs == {'test': 1, 'params': {'boom': '0',
                                            'test': "true",
                                            'val': "1,2,3",
                                            'text': "aaa"}}
    assert skip_params is False


def test_sanitize_params_skip(request):
    data = io.BytesIO(b'test')
    kwargs, skip_params = request.sanitize_params('post', _test=1, boom=data)

    assert kwargs == {'test': 1, 'data': {'boom': data}}
    assert skip_params is True


def test_skip_params(api_path):
    client = api_path.client
    with patch.object(client, 'request', side_effect=dummy) as client_request:
        request = requests.Request(api_path, 'get', _skip_params=False)
        client.loop.run_until_complete(request)
        client_request.assert_called_with(method='get', skip_params=False,
                                          url=api_path.url(), future=request)

        client_request.reset_mock()
        request = requests.Request(api_path, 'get', _skip_params=True)
        client.loop.run_until_complete(request)
        client_request.assert_called_with(method='get', skip_params=True,
                                          url=api_path.url(), future=request)


def test_error_handling(api_path):
    client = api_path.client
    with patch.object(client, 'request', side_effect=dummy):
        request = requests.Request(api_path, 'get', _error_handling=False)
        with patch.object(client, 'error_handler',
                          side_effect=dummy_error_handler) as error_handler:
            client.loop.run_until_complete(request)
            assert not error_handler.called


def test_get_params(request):
    kwargs, skip_params, req_url = request._get_params(_test=1, test=2)

    assert kwargs == {'test': 1, 'params': {'test': '2'}}
    assert skip_params is False
    assert url == req_url


def test_get_iterator(request):
    assert isinstance(request.iterator.with_cursor(),
                      iterators.CursorIterator)
    assert isinstance(request.iterator.with_max_id(),
                      iterators.MaxIdIterator)
    assert isinstance(request.iterator.with_since_id(),
                      iterators.SinceIdIterator)


def test_get_iterator_from_factory(api_path):
    factory = requests.RequestFactory(api_path, 'get')
    assert isinstance(factory.iterator.with_cursor(), iterators.CursorIterator)
    assert isinstance(factory.iterator.with_max_id(), iterators.MaxIdIterator)


def test_iterator_params_from_factory(api_path):
    factory = requests.RequestFactory(api_path, 'get')
    iterator = factory.iterator.with_since_id(_force=False)
    assert isinstance(iterator, iterators.SinceIdIterator)
    assert iterator.force is False
    iterator = factory.iterator.with_since_id(_force=True)
    assert isinstance(iterator, iterators.SinceIdIterator)
    assert iterator.force is True


def test_request_call(request):
    assert isinstance(request(), requests.Request)


def test_iterator_unknown_iterator(request):
    with pytest.raises(AttributeError):
        request.iterator.whatchamacallit()


def dummy_error_handler(request):
    return request


def test_request_error_handler(api_path, _error_handler=True):
    client = api_path.client
    with patch.object(client, 'request', side_effect=dummy) as client_request:
        with patch.object(client, 'error_handler',
                          side_effect=dummy_error_handler) as error_handler:
            client.loop.run_until_complete(
                requests.Request(api_path, 'get',
                                 _error_handling=_error_handler,
                                 test=1, _test=2)
            )
            assert client_request.called_with(method='get',
                                              url=url,
                                              skip_params=False,
                                              test=2,
                                              params={'test': 1})
            assert error_handler.called is _error_handler


def test_request_no_error_handler(api_path):
    test_request_error_handler(api_path, _error_handler=False)


def test_streaming_request(api_path):
    streaming_request = requests.StreamingRequest(api_path, 'get')

    with patch.object(streaming_request.api.client,
                      'stream_request') as client_request:
        streaming_request(test=1, _test=2)
        assert client_request.called_with(method='get',
                                          url=url,
                                          skip_params=False,
                                          test=1,
                                          params={'test': 2})
