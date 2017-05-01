# -*- coding: utf-8 -*-

import asyncio
import os
from unittest.mock import patch

import aiohttp
import peony
import peony.api
import pytest
from peony import BasePeonyClient, data_processing, oauth
from peony.general import twitter_api_version, twitter_base_api_url

from . import Data, MockResponse, dummy

oauth2_keys = 'PEONY_CONSUMER_KEY', 'PEONY_CONSUMER_SECRET'
oauth2 = all(key in os.environ for key in oauth2_keys)

creds_keys = 'consumer_key', 'consumer_secret'
token = None


@pytest.fixture
def dummy_client():
    return peony.BasePeonyClient("", "", loop=False)


def test_create_endpoint(dummy_client):
    base_url = twitter_base_api_url.format(api='api',
                                           version=twitter_api_version)

    client_endpoint = dummy_client.api.test.endpoint.url()
    api = peony.api.APIPath([base_url], '.json', dummy_client)
    assert client_endpoint == api.test.endpoint.url()
    client_endpoint_item = dummy_client['api']['test']['endpoint'].url()
    assert client_endpoint == client_endpoint_item


def test_create_endpoint_dict(dummy_client):
    api = {'api': 'api', 'version': '2.0', 'suffix': '.json'}
    endpoint = dummy_client[api].test.url()
    base_url = twitter_base_api_url.format(api='api', version='2.0')
    assert endpoint == base_url + "/test.json"


def test_create_endpoint_set_exception(dummy_client):
    with pytest.raises(TypeError):
        dummy_client[{'hello', 'world'}]


def test_create_endpoint_tuple(dummy_client):
    base_url_v2 = twitter_base_api_url.format(api='api', version='2.0')
    assert dummy_client['api', '2.0'].test.url() == base_url_v2 + '/test.json'

    base_url_v1 = twitter_base_api_url.format(api='api', version='1.0')
    endpoint = base_url_v1 + '/test.json'
    assert dummy_client['api', '1.0', '.json'].test.url() == endpoint

    base_url = twitter_base_api_url.format(api='api', version="").rstrip('/')
    assert dummy_client['api', '', ''].test.url() == base_url + '/test'

    custom_base_url = "http://{api}.google.com/{version}"
    endpoint = "http://www.google.com/test"
    assert dummy_client['www', '', '', custom_base_url].test.url() == endpoint

    endpoint = "http://google.com/test"
    assert dummy_client['', '', '', custom_base_url].test.url() == endpoint


def test_create_streaming_path(dummy_client):
    assert isinstance(dummy_client.stream.test, peony.api.StreamingAPIPath)


def test_create_api_path(dummy_client):
    assert isinstance(dummy_client.api.test, peony.api.APIPath)


class MockSessionRequest:

    async def __aenter__(self):
        return MockResponse(data=MockResponse.message)

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    def __call__(self, *args, **kwargs):
        return self


class MockSession:

    def __init__(self):
        self.request = MockSessionRequest()


class SetupClientTest(BasePeonyClient):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._session = MockSession()
        self.a, self.b, self.c = "", "", {}

    @peony.init_task
    async def setup_a(self):
        self.a = "123"

    @peony.init_task
    async def setup_b(self):
        self.b = "321"

    @peony.init_task
    async def setup_c(self):
        data = Data({'hello': "world"})

        with patch.object(data_processing, 'read', side_effect=data):
            self.c = await self.api.test.get()


@pytest.mark.asyncio
async def test_setup(event_loop):
    client = SetupClientTest("", "", loop=event_loop)

    async def test():
        await client.setup()
        assert client.a == "123"
        assert client.b == "321"
        assert client.c.data == {'hello': "world"}

    await asyncio.gather(test(), test())


def oauth2_decorator(func):

    @pytest.mark.asyncio
    @pytest.mark.skipif(not oauth2, reason="no credentials found")
    async def decorator():
        global token

        client = get_oauth2_client(bearer_token=token)
        await func(client)

        # keep the token for the next test
        token = client.headers.token

    return decorator


def get_oauth2_client(**kwargs):
    creds = {creds_keys[i]: os.environ[oauth2_keys[i]] for i in range(2)}
    return BasePeonyClient(auth=oauth.OAuth2Headers, loop=False,
                           **creds, **kwargs)


class TasksClientTest(SetupClientTest):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tasks_tests = [False, False, True]

    @peony.task
    async def task_a(self):
        self.tasks_tests[0] = True
        await self.api.test.get()

    @peony.task
    async def task_b(self):
        self.tasks_tests[1] = True
        await self.api.endpoint.post()

    async def not_a_task(self):
        self.tasks_tests[2] = False


@pytest.mark.asyncio
async def test_tasks():
    client = TasksClientTest("", "")
    with patch.object(client, 'request', side_effect=dummy) as request:
        await client.run_tasks()
        base_url = twitter_base_api_url.format(api='api',
                                               version=twitter_api_version)
        assert request.called_with(method='get', url=base_url + '/test.json')
        assert request.called_with(method='get',
                                   url=base_url + '/endpoint.json')

        assert client.a == "123"
        assert client.b == "321"
        assert client.c is None  # it's None this time

        assert all(client.tasks_tests)


@pytest.mark.asyncio
async def test_streaming_apis(dummy_client):
    with patch.object(dummy_client, 'request', side_effect=dummy) as request:
        await dummy_client.api.test.get()
        assert request.called

    with patch.object(dummy_client, 'stream_request') as request:
        dummy_client.stream.test.get()
        assert request.called

    client = BasePeonyClient("", "", streaming_apis={'api'})
    with patch.object(client, 'stream_request') as request:
        client.api.test.get()
        assert request.called

    with patch.object(client, 'request', side_effect=dummy) as request:
        await client.stream.test.get()
        assert request.called


def test_client_base_url():
    base_url = "http://{api}.google.com/{version}"
    client = BasePeonyClient("", "", base_url=base_url, api_version="1")
    assert client.api.test.url() == "http://api.google.com/1/test.json"


@pytest.mark.asyncio
async def test_session_creation(dummy_client):
    with patch.object(aiohttp, 'ClientSession') as client_session:
        await dummy_client.setup()
        assert client_session.called


class SetupInitListTest(BasePeonyClient):

    @property
    def init_tasks(self):
        return self.setup_a(), self.setup_b()

    async def setup_a(self):
        self.a = "123"

    async def setup_b(self):
        self.b = "321"


@pytest.mark.asyncio
async def test_setup_init_tasks_list():
    client = SetupInitListTest("", "")
    await client.setup()
    assert client.a == "123"
    assert client.b == "321"


@pytest.fixture
def oauth2_client(event_loop):
    if oauth2:
        return get_oauth2_client(loop=event_loop)


@oauth2_decorator
async def test_oauth2_get_token(client):
    if 'Authorization' in client.headers:
        del client.headers['Authorization']

    await client.headers.sign()


@oauth2_decorator
async def test_oauth2_request(client):
    await client.api.search.tweets.get(q="@twitter hello :)")


@oauth2_decorator
async def test_oauth2_invalidate_token(client):
    await client.headers.sign()  # make sure there is a token
    await client.headers.invalidate_token()
    assert client.headers.token is None


@oauth2_decorator
async def test_oauth2_bearer_token(client):
    await client.headers.sign()

    token = client.headers.token

    client2 = get_oauth2_client(bearer_token=token)
    assert client2.headers.token == client.headers.token
