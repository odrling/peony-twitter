# -*- coding: utf-8 -*-

import peony.api
import pytest
from peony import BasePeonyClient
from peony.general import twitter_base_api_url

# unique client

client = BasePeonyClient("", "")

# constants

url = twitter_base_api_url + "/test/endpoint.json"

# fixture functions


@pytest.fixture
def api():
    return peony.api.APIPath([twitter_base_api_url], '.json', client)


@pytest.fixture
def streaming():
    return peony.api.StreamingAPIPath([twitter_base_api_url], '.json', client)


@pytest.fixture
def endpoint(api):
    return api.test.endpoint


# test functions


def test_api_endpoint_creation(endpoint):
    assert endpoint.url() == url


def test_api_endpoint_creation_tuple(api):
    endpoint = api['test', 'endpoint']
    assert endpoint.url() == url


def test_api_endpoint_creation_exception(api):
    with pytest.raises(TypeError):
        api[set()]


def test_api_client(api):
    assert api.client == client


def test_api_suffix(api):
    assert api._suffix == '.json'


def test_api_request_method_get(endpoint):
    assert endpoint.get.method == 'get'


def test_api_request_method_post(endpoint):
    assert endpoint.post.method == 'post'


def test_api_streaming_request_method_get(streaming):
    assert streaming.endpoint.get.method == 'get'


def test_api_streaming_request_method_post(streaming):
    assert streaming.endpoint.post.method == 'post'


def test_api_str(endpoint):
    assert str(endpoint) == "<APIPath %s>" % url
