# -*- coding: utf-8 -*-

import asyncio
from unittest.mock import Mock, patch

import aiohttp
import pytest

import peony
import peony.api
from peony import BasePeonyClient, data_processing, exceptions, stream
from tests import dummy
from tests.tests_client import DummyClient, MockSession, MockSessionRequest


@pytest.mark.asyncio
async def test_streaming_apis():
    async with DummyClient() as dummy_client:
        with patch.object(dummy_client, 'request', side_effect=dummy)\
                as request:
            await dummy_client.api.test.get()
            assert request.called

        with patch.object(dummy_client, 'stream_request') as request:
            dummy_client.stream.test.get.stream()
            assert request.called


@pytest.mark.asyncio
async def test_client_base_url():
    base_url = "http://{api}.google.com/{version}"
    async with DummyClient(base_url=base_url, api_version="1") as client:
        assert client.api.test.url() == "http://api.google.com/1/test.json"


@pytest.mark.asyncio
async def test_session_creation(event_loop):
    with patch.object(aiohttp, 'ClientSession') as client_session:
        client = DummyClient(loop=event_loop)
        await client.setup
        assert client_session.called


def test_client_error():
    with pytest.raises(TypeError):
        BasePeonyClient()


@pytest.mark.asyncio
async def test_client_encoding_loads():
    text = bytes([194, 161])
    data = b"{\"hello\": \"%s\"}" % text

    async with DummyClient(encoding='utf-8') as client:
        assert client._loads(data)['hello'] == text.decode('utf-8')

    async with DummyClient(encoding='ascii') as client:
        with pytest.raises(UnicodeDecodeError):
            client._loads(data)


@pytest.mark.asyncio
async def test_close(event_loop):
    async with DummyClient(loop=event_loop) as client:
        await client.setup

        client._gathered_tasks = asyncio.gather(dummy())
        session = client._session

        await client.close()
        assert session.closed
        assert client._session is None


@pytest.mark.asyncio
async def test_close_no_session():
    async with DummyClient() as client:
        assert client._session is None
        await client.close()


@pytest.mark.asyncio
async def test_close_no_tasks():
    async with DummyClient() as client:
        assert client._gathered_tasks is None
        await client.close()


@pytest.mark.asyncio
async def test_bad_request():
    async def prepare_dummy(*args, **kwargs):
        return kwargs

    async with BasePeonyClient("", "") as dummy_client:
        dummy_client._session = MockSession(MockSessionRequest(status=404))
        with patch.object(dummy_client.headers, 'prepare_request',
                          side_effect=prepare_dummy):
            with pytest.raises(exceptions.HTTPNotFound):
                await dummy_client.request('get', "http://google.com/404",
                                           future=asyncio.Future())


@pytest.mark.asyncio
async def test_stream_request():
    # streams are tested in test_stream
    async with DummyClient() as dummy_client:
        assert isinstance(dummy_client.stream.get.stream(),
                          stream.StreamResponse)


@pytest.mark.asyncio
async def test_request_proxy():
    def raise_proxy(*args, proxy=None, **kwargs):
        raise RuntimeError(proxy)

    async with BasePeonyClient("", "",
                               proxy="http://some.proxy.com") as dummy_client:
        async with aiohttp.ClientSession() as session:
            with patch.object(dummy_client.headers, 'prepare_request',
                              side_effect=raise_proxy):
                try:
                    await dummy_client.request(method='get',
                                               url="http://hello.com",
                                               session=session,
                                               future=None)
                except RuntimeError as e:
                    assert str(e) == "http://some.proxy.com"
                else:
                    pytest.fail("Could not check proxy")


@pytest.mark.asyncio
async def test_request_encoding():
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

    ENCODING = "best encoding"

    async def get_encoding(*args, encoding=None, **kwargs):
        return encoding

    def check_encoding(data, *args, **kwargs):
        assert data == ENCODING

    async with BasePeonyClient("", "") as client:
        async with aiohttp.ClientSession() as session:
            with patch.object(session, 'request', side_effect=DummyCTX):
                with patch.object(data_processing, 'read',
                                  side_effect=get_encoding):
                    with patch.object(data_processing, 'PeonyResponse',
                                      side_effect=check_encoding):
                        await client.request(method='get',
                                             url="http://hello.com",
                                             encoding=ENCODING,
                                             session=session,
                                             future=asyncio.Future())


@pytest.mark.asyncio
async def test_run_keyboard_interrupt(event_loop):
    async with DummyClient(loop=event_loop) as client:
        with patch.object(client, 'run_tasks', side_effect=KeyboardInterrupt):
            await client.arun()


@pytest.mark.asyncio
async def test_run_exceptions_raise():
    async with DummyClient() as client:
        for exc in (Exception, RuntimeError, peony.exceptions.PeonyException):
            with patch.object(client, 'run_tasks', side_effect=exc):
                with pytest.raises(exc):
                    await client.arun()


@pytest.mark.asyncio
async def test_close_session():
    async with DummyClient() as dummy_client:
        async with aiohttp.ClientSession() as session:
            dummy_client._session = session

            await dummy_client.close()
            assert session.closed
            assert dummy_client._session is None


@pytest.mark.asyncio
async def test_close_user_session():
    session = Mock()
    client = BasePeonyClient("", "", session=session)

    await client.close()
    assert not session.close.called


class Client(DummyClient):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.t1 = False

    @peony.task
    def _t1(self):
        self.t1 = True


@pytest.mark.asyncio
async def test_get_tasks():
    session = aiohttp.ClientSession()
    session.request = dummy
    client = Client(session=aiohttp.ClientSession())
    assert client.t1 is False
    client._get_tasks()
    assert client.t1 is True


class SubClient(Client, dict):
    # inherit from dict to test inheritance without _task attribute

    @peony.task
    def t3(self):
        pass


def test_tasks_inheritance():
    assert SubClient.t3 in SubClient._tasks['tasks']
    assert Client._t1 in SubClient._tasks['tasks']


class ClientCancelTasks(DummyClient):

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
    async with ClientCancelTasks(loop=event_loop) as client:
        await client.run_tasks()
        assert client.cancelled


@pytest.mark.asyncio
async def test_disabled_error_handler():
    async def raise_runtime_error(*args, **kwargs):
        raise RuntimeError

    with patch.object(BasePeonyClient, 'request',
                      side_effect=raise_runtime_error):
        async with BasePeonyClient("", "") as client:
            with pytest.raises(RuntimeError):
                await client.api.test.get()


@pytest.mark.asyncio
async def test_change_request_client():
    async with DummyClient() as client:
        req = client.api.call.get()
        assert req.client == client
        with patch.object(client, 'request', side_effect=dummy) as request:
            try:
                await req()
            finally:
                assert request.called

        async with DummyClient() as client2:
            req.client = client2
            assert req.client == client2
            with patch.object(client2, 'request',
                              side_effect=dummy) as request:
                try:
                    await req()
                finally:
                    assert request.called
