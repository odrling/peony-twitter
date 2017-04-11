# -*- coding: utf-8 -*-

import pytest

import peony.api
from peony import BasePeonyClient
from peony.general import twitter_base_api_url

client = BasePeonyClient("", "")

api = peony.api.APIPath([twitter_base_api_url], '.json', client)
streaming = peony.api.StreamingAPIPath([twitter_base_api_url], '.json', client)

endpoint = api.test.endpoint
url = twitter_base_api_url + "/test/endpoint.json"


def test_api_endpoint_creation():
    assert endpoint.url() == url


def test_api_endpoint_creation_tuple():
    endpoint = api['test', 'endpoint']
    assert endpoint.url() == url


def test_api_endpoint_creation_exception():
    with pytest.raises(TypeError):
        api[set()]


def test_api_client():
    assert api._client == client


def test_api_suffix():
    assert api._suffix == '.json'


def test_api_request_method_get():
    assert endpoint.get.method == 'get'


def test_api_request_method_post():
    assert endpoint.post.method == 'post'


def test_api_streaming_request_method_get():
    assert streaming.endpoint.get.method == 'get'


def test_api_streaming_request_method_post():
    assert streaming.endpoint.post.method == 'post'


def test_api_str():
    assert str(endpoint) == "<APIPath %s>" % url
