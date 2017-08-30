# -*- coding: utf-8 -*-

import asyncio
import io
import random
import tempfile
from unittest.mock import Mock, patch

import aiofiles
import aiohttp
import pytest

import peony
import peony.api
from peony import (BasePeonyClient, PeonyClient, data_processing, exceptions,
                   oauth, stream, utils)
from peony.general import twitter_api_version, twitter_base_api_url

from . import Data, MockResponse, dummy, medias


@pytest.fixture
def dummy_client(event_loop):
    client = peony.BasePeonyClient("", "", loop=event_loop)
    yield client
    del client


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


def test_create_endpoint_no_api_or_version(dummy_client):
    base_url = "http://google.com"
    assert dummy_client['', '', '', base_url].test.url() == base_url + '/test'


def test_create_endpoint_type_error(dummy_client):
    with pytest.raises(TypeError):
        dummy_client[object()]


def test_create_streaming_path(dummy_client):
    assert isinstance(dummy_client.stream.test, peony.api.StreamingAPIPath)


def test_create_api_path(dummy_client):
    assert isinstance(dummy_client.api.test, peony.api.APIPath)


class MockSessionRequest:

    def __init__(self, status=200, data=MockResponse.message,
                 content_type="plain/text"):
        self.status = status
        self.data = data
        self.ctype = content_type

    async def __aenter__(self, *args, **kwargs):
        return MockResponse(status=self.status, data=self.data,
                            content_type=self.ctype)

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    def __call__(self, *args, **kwargs):
        return self


class MockSession:

    def __init__(self, request=None):
        if request is None:
            self.request = MockSessionRequest()
        else:
            self.request = request


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
        await client.setup
        assert client.a == "123"
        assert client.b == "321"
        assert client.c.data == {'hello': "world"}

    await asyncio.gather(test(), test())


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


@pytest.mark.current
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
async def test_session_creation(event_loop):
    with patch.object(aiohttp, 'ClientSession') as client_session:
        client = BasePeonyClient("", "", loop=event_loop)
        await client.setup
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
    await client.setup
    assert client.a == "123"
    assert client.b == "321"


def test_client_error():
    with pytest.raises(TypeError):
        BasePeonyClient()


def test_client_encoding_loads():
    text = bytes([194, 161])
    data = b"{\"hello\": \"%s\"}" % text

    client = BasePeonyClient("", "", encoding='utf-8')
    assert client._loads(data)['hello'] == text.decode('utf-8')

    client = BasePeonyClient("", "", encoding='ascii')
    with pytest.raises(UnicodeDecodeError):
        client._loads(data)


@pytest.mark.asyncio
async def test_close(event_loop):
    client = BasePeonyClient("", "", loop=event_loop)
    await client.setup

    def dummy_func(*args, **kwargs):
        pass

    client._gathered_tasks = asyncio.gather(dummy())
    session = client._session
    await client.close()
    assert session.closed
    assert client._session is None


def test_close_no_session():
    client = BasePeonyClient("", "")
    assert client._session is None
    client.close()


def test_close_no_tasks():
    client = BasePeonyClient("", "")
    assert client._gathered_tasks is None
    client.close()


@pytest.mark.asyncio
async def test_bad_request(dummy_client):
    async def prepare_dummy(*args, **kwargs):
        return kwargs

    dummy_client._session = MockSession(MockSessionRequest(status=404))
    with patch.object(dummy_client.headers, 'prepare_request',
                      side_effect=prepare_dummy):
        with pytest.raises(exceptions.NotFound):
            await dummy_client.request('get', "http://google.com/404",
                                       future=asyncio.Future())


@pytest.mark.current
def test_stream_request(dummy_client):
    # streams are tested in test_stream
    assert isinstance(dummy_client.stream.get(), stream.StreamResponse)


@pytest.mark.asyncio
async def test_request_proxy(dummy_client):
    class RaiseProxy:

        def __init__(self, *args, proxy=None, **kwargs):
            raise RuntimeError(proxy)

    async with aiohttp.ClientSession() as session:
        with patch.object(session, 'request', side_effect=RaiseProxy):
            try:
                await dummy_client.request(method='get',
                                           url="http://hello.com",
                                           proxy="http://some.proxy.com",
                                           session=session,
                                           future=asyncio.Future())
            except RuntimeError as e:
                assert str(e) == "http://some.proxy.com"


@pytest.mark.asyncio
async def test_request_encoding(dummy_client):
    class DummyCTX:

        def __init__(self, **kwargs):
            self.status = 200

        def __getattr__(self, item):
            return None

        def __aiter__(self):
            return self

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    def raise_encoding(*args, encoding=None, **kwargs):
        raise RuntimeError(encoding)

    async with aiohttp.ClientSession() as session:
        with patch.object(session, 'request', side_effect=DummyCTX):
            with patch.object(data_processing, 'read', side_effect=dummy):
                with patch.object(data_processing, 'PeonyResponse'):
                    try:
                        await dummy_client.request(method='get',
                                                   url="http://hello.com",
                                                   encoding="best encoding",
                                                   session=session,
                                                   future=asyncio.Future())
                    except RuntimeError as e:
                        assert str(e) == "best encoding"


def test_run_keyboard_interrupt(event_loop):
    client = BasePeonyClient("", "", loop=event_loop)
    with patch.object(client, 'run_tasks', side_effect=KeyboardInterrupt):
        client.run()


def test_run_exceptions_raise(event_loop):
    client = BasePeonyClient("", "", loop=event_loop)
    for exc in (Exception, RuntimeError, peony.exceptions.PeonyException):
        with patch.object(client, 'run_tasks', side_effect=exc):
            with pytest.raises(exc):
                client.run()


@pytest.mark.asyncio
async def test_close_session(dummy_client, event_loop):
    with aiohttp.ClientSession(loop=event_loop) as session:
        dummy_client._session = session

        def dummy_func(*args, **kwargs):
            pass

        await dummy_client.close()
        assert session.closed
        assert dummy_client._session is None


def test_close_user_session():
    client = BasePeonyClient("", "", session=Mock())

    client.close()
    assert not client._session.close.called


class Client(peony.BasePeonyClient):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.t1, self.t2 = False, False

    @peony.task
    def _t1(self):
        self.t1 = True

    @peony.init_task
    def _t2(self):
        self.t2 = True


def test_get_tasks(event_loop):
    client = Client("", "", session=aiohttp.ClientSession(loop=event_loop))

    client._get_tasks(kind=peony.task)

    assert client.t1 is True
    assert client.t2 is False


def test_get_init_tasks(event_loop):
    client = Client("", "", session=aiohttp.ClientSession(loop=event_loop))
    client._get_tasks(kind=peony.init_task)

    assert client.t1 is False
    assert client.t2 is True


def test_get_tasks_runtime_exception(event_loop):
    client = Client("", "", session=aiohttp.ClientSession(loop=event_loop))

    with pytest.raises(RuntimeError):
        client._get_tasks(kind="")


class SubClient(Client, dict):
    # dict to test inheritance without _task attribute

    @peony.task
    def t3(self):
        pass


def test_tasks_inheritance():
    assert SubClient.t3 in SubClient._tasks['tasks']
    assert Client._t1 in SubClient._tasks['tasks']


class ClientCancelTasks(BasePeonyClient):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cancelled = True

    @peony.task
    async def cancel_tasks(self):
        await asyncio.sleep(0.001)
        await self.close()

    @peony.task
    async def sleep(self):
        await asyncio.sleep(1)
        self.cancelled = False


@pytest.mark.asyncio
async def test_close_cancel_tasks(event_loop):
    client = ClientCancelTasks("", "", loop=event_loop)
    await client.run_tasks()
    assert client.cancelled


@pytest.fixture
def peony_client(event_loop):
    client = PeonyClient("", "", loop=event_loop)
    yield client
    del client


def request_test(expected_url, expected_method):

    async def request(*args, url=None, method=None, future=None, **kwargs):
        assert url == expected_url
        assert method == expected_method
        future.set_result(True)
        return True

    return request


@pytest.mark.asyncio
async def test_peony_client_get_user(peony_client):
    url = peony_client.api.account.verify_credentials.url()
    request = request_test(url, 'get')

    with patch.object(peony_client, 'request', side_effect=request) as req:
        await peony_client._PeonyClient__get_user()
        assert req.called
        assert peony_client.user


@pytest.mark.asyncio
async def test_peony_client_get_twitter_configuration(peony_client):
    request = request_test(peony_client.api.help.configuration.url(), 'get')

    with patch.object(peony_client, 'request', side_effect=request) as req:
        task = peony_client._PeonyClient__get_twitter_configuration
        await task(peony_client)
        assert req.called
        assert peony_client.twitter_configuration


def test_peony_client_init_tasks(peony_client, event_loop):
    conf_n = random.randrange(1 << 16)
    user_n = random.randrange(1 << 16)
    with patch.object(peony.BasePeonyClient, 'init_tasks',
                      return_value=[conf_n]):
        with patch.object(peony_client, '_PeonyClient__get_user',
                          return_value=user_n):
            tasks = peony_client.init_tasks()
            assert conf_n in tasks
            assert user_n in tasks
            assert len(tasks) == 2


def test_peony_client_init_tasks_oauth2(event_loop):
    client = PeonyClient("", "", loop=event_loop, auth=oauth.OAuth2Headers)
    conf_n = random.randrange(1 << 16)
    with patch.object(peony.BasePeonyClient, 'init_tasks',
                      return_value=[conf_n]):
        tasks = client.init_tasks()
        assert conf_n in tasks
        assert len(tasks) == 1


def test_add_event_stream():

    class ClientTest(BasePeonyClient):
        pass

    assert peony.commands.EventStream not in ClientTest._streams

    ClientTest.event_stream(peony.commands.EventStream)
    assert peony.commands.EventStream in ClientTest._streams


@pytest.fixture
def dummy_peony_client(event_loop):
    client = PeonyClient("", "", loop=event_loop)
    with patch.object(client, 'init_tasks', return_value=[]):
        yield client


@pytest.mark.asyncio
async def test_size_test(dummy_peony_client):
    assert dummy_peony_client._size_test(5, 5) is False
    assert dummy_peony_client._size_test(6, 5) is True


@pytest.mark.asyncio
async def test_size_test_config(dummy_peony_client):
    dummy_peony_client.twitter_configuration = {
        'photo_size_limit': 5
    }

    assert dummy_peony_client._size_test(5, None) is False
    assert dummy_peony_client._size_test(6, None) is True


@pytest.mark.asyncio
async def test_size_test_config_and_limit(dummy_peony_client):
    dummy_peony_client.twitter_configuration = {
        'photo_size_limit': 5
    }

    assert dummy_peony_client._size_test(10, 10) is False
    assert dummy_peony_client._size_test(11, 10) is True


@pytest.mark.asyncio
async def test_size_test_no_limit_no_config(dummy_peony_client):
    assert dummy_peony_client._size_test(5, None) is False
    dummy_peony_client.twitter_configuration = {}
    assert dummy_peony_client._size_test(5, None) is False


@pytest.mark.asyncio
@pytest.mark.parametrize('input_type', ['bytes', 'file', 'path'])
async def test_upload_media(dummy_peony_client, input_type, medias):
    media_data = medias['lady_peony'].content

    if input_type == 'file':
        media = io.BytesIO(media_data)
    elif input_type == 'path':
        media_file = tempfile.NamedTemporaryFile('w+b')
        media_file.write(media_data)
        media = media_file.name
    else:
        media = media_data

    async def dummy_upload(url, method, future, data, skip_params):
        assert url == dummy_peony_client.upload.media.upload.url()
        assert method == 'post'
        if input_type in 'file':
            assert data['media'] == media
        else:
            if isinstance(data['media'], bytes):
                assert data['media'] == media_data
            else:
                assert await utils.execute(data['media'].read()) == media_data
        assert skip_params is True
        future.set_result(None)

    with patch.object(dummy_peony_client, 'request',
                      side_effect=dummy_upload) as req:
        await dummy_peony_client.upload_media(media)
        assert req.called

    with patch.object(dummy_peony_client, 'request',
                      side_effect=dummy_upload) as req:
        await dummy_peony_client.upload_media(media, size_limit=3 * 1024**2)
        assert req.called

    with patch.object(dummy_peony_client, 'request',
                      side_effect=dummy_upload) as req:
        dummy_peony_client.twitter_configuration = {
            'photo_size_limit': 3 * 1024**2
        }
        await dummy_peony_client.upload_media(media)
        assert req.called

    if input_type == 'file':
        media.close()
    elif input_type == 'path':
        media_file.close()


@pytest.mark.asyncio
async def test_upload_media_exception(dummy_peony_client):
    with pytest.raises(TypeError):
        await dummy_peony_client.upload_media([])


@pytest.mark.asyncio
async def test_upload_media_chunked(dummy_peony_client, medias):
    media_data = await medias['lady_peony'].download()
    rand = random.randrange(1 << 16)

    async def dummy_upload(media, size, *args, **kwargs):
        assert media == media_data
        assert size == len(media)
        return rand

    with patch.object(dummy_peony_client, '_chunked_upload',
                      side_effect=dummy_upload) as upload:
        await dummy_peony_client.upload_media(media_data, chunked=True)
        assert upload.called


@pytest.mark.asyncio
async def test_upload_media_size_limit(dummy_peony_client, medias):
    media_data = await medias['video'].download()
    rand = random.randrange(1 << 16)

    async def dummy_upload(media, size, *args, **kwargs):
        assert media == media_data
        assert size == len(media)
        return rand

    with patch.object(dummy_peony_client, '_chunked_upload',
                      side_effect=dummy_upload) as upload:
        await dummy_peony_client.upload_media(media_data,
                                              size_limit=3 * 1024**2)
        assert upload.called


class DummyRequest:

    def __init__(self, client, media, chunk_size=1024**2, fail=False):
        self.i = -1
        self.client = client
        self.media = media
        self.media_data = None
        self.chunk_size = chunk_size
        self.media_id = random.randrange(1 << 16)
        self.fail = fail

    async def __call__(self, url, method, future,
                       data=None, skip_params=None, params=None):
        assert url == self.client.upload.media.upload.url()

        response = {'media_id': self.media_id}

        append = range(self.media.content_length // self.chunk_size + 1)

        if self.i <= append[-1] + 1:
            assert method == "post"
        else:
            assert method == "get"

        if self.i == -1:
            self.media_data = io.BytesIO(self.media.content)
            assert data == {'command': 'INIT',
                            'media_category': self.media.category,
                            'media_type': self.media.type,
                            'total_bytes': str(self.media.content_length)}
        elif self.i in append:
            assert data == {'command': 'APPEND',
                            'media': self.media_data.read(self.chunk_size),
                            'media_id': str(self.media_id),
                            'segment_index': str(self.i)}
        elif self.i == append[-1] + 1:
            if self.media.category != 'tweet_image':
                check_after_secs = 5 if 'video' in self.media.category else 1
                response['processing_info'] = {
                    'state': 'pending',
                    'check_after_secs': check_after_secs
                }

            assert data == {'command': 'FINALIZE',
                            'media_id': str(self.media_id)}
        else:
            if self.fail:
                response['processing_info'] = {'state': "failed",
                                               'error': {'message': "test"}}
            else:
                response['processing_info'] = {'state': 'succeeded'}

            assert params == {'command': 'STATUS',
                              'media_id': str(self.media_id)}

        assert skip_params is (self.i in append)

        self.i += 1
        future.set_result(response)
        return response

    def reset(self):
        self.i = -1
        self.media_id = random.randrange(1 << 16)


async def chunked_upload(dummy_peony_client, media, file):
    chunk_size = 1024 ** 2

    dummy_request = DummyRequest(dummy_peony_client, media, chunk_size)

    with patch.object(dummy_peony_client, 'request',
                      side_effect=dummy_request):
        with patch.object(asyncio, 'sleep', side_effect=dummy) as sleep:
            await dummy_peony_client.upload_media(file,
                                                  chunk_size=chunk_size,
                                                  chunked=True)

            if media.filename == 'video':
                sleep.assert_called_with(5)
            elif media.filename == 'bloom':
                sleep.assert_called_with(1)

            dummy_request.reset()
            with patch.object(utils, 'get_media_metadata') as metadata:
                with patch.object(utils, 'get_category') as category:
                    await dummy_peony_client.upload_media(
                        file, chunk_size=chunk_size, chunked=True,
                        media_category=media.category,
                        media_type=media.type
                    )
                    assert not metadata.called
                    assert not category.called

            dummy_request.reset()
            with patch.object(utils, 'get_media_metadata') as metadata:
                await dummy_peony_client.upload_media(
                    file, chunk_size=chunk_size,
                    media_type=media.type, chunked=True
                )
                assert not metadata.called


@pytest.mark.current
@pytest.mark.usefixtures('medias')
@pytest.mark.asyncio
@pytest.mark.parametrize('media', medias.values())
async def test_chunked_upload(dummy_peony_client, media):
    data = io.BytesIO(media.content)
    await chunked_upload(dummy_peony_client, media, data)


@pytest.fixture
def media_filename(medias):
    media = medias['bloom']

    with tempfile.NamedTemporaryFile() as file:
        file.write(media.content)
        yield media, file.name


@pytest.mark.asyncio
async def test_chunked_upload_async_input(dummy_peony_client, media_filename):
    media, filename = media_filename
    async with aiofiles.open(filename, 'rb') as aiofile:
        await chunked_upload(dummy_peony_client, media, aiofile)


@pytest.mark.asyncio
async def test_chunked_upload_fail(dummy_peony_client, medias):
    media = medias['video']
    media_data = await media.download()

    chunk_size = 1024**2

    dummy_request = DummyRequest(dummy_peony_client, media, chunk_size, True)

    with patch.object(dummy_peony_client, 'request',
                      side_effect=dummy_request):
        with patch.object(asyncio, 'sleep', side_effect=dummy) as sleep:
            with pytest.raises(peony.exceptions.MediaProcessingError):
                await dummy_peony_client.upload_media(
                    media_data, chunk_size=chunk_size, chunked=True
                )
                sleep.assert_called_with(5)


@pytest.mark.asyncio
async def test_upload_from_url(dummy_peony_client, medias, media_request):
    url = medias['lady_peony'].url

    async def dummy_get(get_url):
        assert get_url == url
        return media_request

    async def dummy_request(url, method, future, data=None, skip_params=None):
        assert url == dummy_peony_client.upload.media.upload.url()
        assert method.lower() == 'post'
        assert data['media'] == media_request.content
        assert skip_params
        future.set_result(None)

    with patch.object(dummy_peony_client, '_session') as session:
        session.get = dummy_get
        with patch.object(dummy_peony_client, 'request',
                          side_effect=dummy_request):
            await dummy_peony_client.upload_media(url)


@pytest.mark.asyncio
async def test_upload_from_request(dummy_peony_client, media_request):
    async def dummy_request(url, method, future, data=None, skip_params=None):
        assert url == dummy_peony_client.upload.media.upload.url()
        assert method.lower() == 'post'
        assert data['media'] == media_request.content
        assert skip_params
        future.set_result(None)

    with patch.object(dummy_peony_client, 'request',
                      side_effect=dummy_request):
        await dummy_peony_client.upload_media(media_request)


@pytest.mark.asyncio
async def test_upload_type_error(dummy_peony_client, media_request):
    def fail(*args, **kwargs):
        pytest.fail("Did not raise TypeError")

    with pytest.raises(TypeError):
        with patch.object(dummy_peony_client, 'request', side_effect=fail):
            await dummy_peony_client.upload_media(media_request.content,
                                                  chunked=True)
