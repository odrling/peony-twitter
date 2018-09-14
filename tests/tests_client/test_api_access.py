
import peony
import peony.api
import pytest
from peony.general import twitter_api_version, twitter_base_api_url

from tests.tests_client import DummyClient


@pytest.mark.asyncio
async def test_create_endpoint():
    async with DummyClient() as dummy_client:
        base_url = twitter_base_api_url.format(api='api',
                                               version=twitter_api_version)

        client_endpoint = dummy_client.api.test.endpoint.url()
        api = peony.api.APIPath([base_url], '.json', dummy_client)
        assert client_endpoint == api.test.endpoint.url()
        client_endpoint_item = dummy_client['api']['test']['endpoint'].url()
        assert client_endpoint == client_endpoint_item


@pytest.mark.asyncio
async def test_create_endpoint_dict():
    async with DummyClient() as dummy_client:
        api = {'api': 'api', 'version': '2.0', 'suffix': '.json'}
        endpoint = dummy_client[api].test.url()
        base_url = twitter_base_api_url.format(api='api', version='2.0')
        assert endpoint == base_url + "/test.json"


@pytest.mark.asyncio
async def test_create_endpoint_set_exception():
    async with DummyClient() as dummy_client:
        with pytest.raises(TypeError):
            dummy_client[{'hello', 'world'}]


@pytest.mark.asyncio
async def test_create_endpoint_tuple():
    async with DummyClient() as dummy_client:
        base_url_v2 = twitter_base_api_url.format(api='api', version='2.0')
        api = dummy_client['api', '2.0']
        assert api.test.url() == base_url_v2 + '/test.json'

        base_url_v1 = twitter_base_api_url.format(api='api', version='1.0')
        endpoint = base_url_v1 + '/test.json'
        api = dummy_client['api', '1.0', '.json']
        assert api.test.url() == endpoint

        base_url = twitter_base_api_url.format(api='api', version="")
        api = dummy_client['api', '', '']
        assert api.test.url() == base_url.rstrip('/') + '/test'

        custom_base_url = "http://{api}.google.com/{version}"
        endpoint = "http://www.google.com/test"
        api = dummy_client['www', '', '', custom_base_url]
        assert api.test.url() == endpoint

        endpoint = "http://google.com/test"
        api = dummy_client['', '', '', custom_base_url]
        assert api.test.url() == endpoint


@pytest.mark.asyncio
async def test_create_endpoint_no_api_or_version():
    async with DummyClient() as dummy_client:
        base_url = "http://google.com"
        api = dummy_client['', '', '', base_url]
        assert api.test.url() == base_url + '/test'


@pytest.mark.asyncio
async def test_create_endpoint_type_error():
    async with DummyClient() as dummy_client:
        with pytest.raises(TypeError):
            dummy_client[object()]


@pytest.mark.asyncio
async def test_create_streaming_path():
    async with DummyClient() as dummy_client:
        assert isinstance(dummy_client.stream.test, peony.api.StreamingAPIPath)


@pytest.mark.asyncio
async def test_create_api_path():
    async with DummyClient() as dummy_client:
        assert isinstance(dummy_client.api.test, peony.api.APIPath)
