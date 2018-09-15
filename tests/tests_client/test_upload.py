# -*- coding: utf-8 -*-

import asyncio
import io
import random
import tempfile
from unittest.mock import patch

import aiofiles
import aiohttp
import peony
import peony.exceptions
import pytest
from peony import utils
from peony.client import PeonyClient

from tests.tests_client import DummyPeonyClient, TaskContext

from .. import dummy, medias


@pytest.mark.asyncio
async def test_size_test():
    async with DummyPeonyClient() as dummy_peony_client:
        assert await dummy_peony_client._size_test(5, 5) is False
        assert await dummy_peony_client._size_test(6, 5) is True


class MyPatch:

    def __init__(self, obj, attr, val):
        self.object = obj
        self.attr = attr
        self.val = val

    def __enter__(self):
        self.original = getattr(self.object, self.attr)
        setattr(self.object, self.attr, self.val)

    def __exit__(self, exc_type, exc_val, exc_tb):
        setattr(self.object, self.attr, self.original)


mypatch = MyPatch


@pytest.mark.asyncio
async def test_size_test_config():
    async with DummyPeonyClient() as dummy_peony_client:
        async def twitter_config():
            return {'photo_size_limit': 5}

        async with TaskContext(twitter_config()) as task:
            with mypatch(dummy_peony_client, '_twitter_configuration', task):
                assert await dummy_peony_client._size_test(5, None) is False
                assert await dummy_peony_client._size_test(6, None) is True


@pytest.mark.asyncio
async def test_size_test_config_and_limit():
    async with DummyPeonyClient() as dummy_peony_client:
        async def twitter_config():
            return {'photo_size_limit': 5}

        async with TaskContext(twitter_config()) as task:
            with mypatch(dummy_peony_client, '_twitter_configuration', task):
                assert await dummy_peony_client._size_test(10, 10) is False
                assert await dummy_peony_client._size_test(11, 10) is True


@pytest.mark.asyncio
async def test_size_test_no_limit_no_config():
    async with DummyPeonyClient() as dummy_peony_client:
        async def twitter_config():
            return {}

        async with TaskContext(twitter_config()) as task:
            with mypatch(dummy_peony_client, '_twitter_configuration', task):
                assert await dummy_peony_client._size_test(5, None) is False


@pytest.mark.asyncio
@pytest.mark.parametrize('input_type', ['bytes', 'file', 'path'])
async def test_upload_media(input_type, medias):
    async with DummyPeonyClient() as dummy_peony_client:
        media_data = medias['lady_peony'].content
        media_file = None

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
                    data = await utils.execute(data['media'].read())
                    assert data == media_data

            assert skip_params is True
            future.set_result(None)

        with patch.object(dummy_peony_client, 'request',
                          side_effect=dummy_upload) as req:
            await dummy_peony_client.upload_media(media,
                                                  size_limit=3 * 1024**2)
            assert req.called

        with patch.object(dummy_peony_client, 'request',
                          side_effect=dummy_upload) as req:
            async def twitter_config():
                return {'photo_size_limit': 3 * 1024**2}

            async with TaskContext(twitter_config()) as task:
                with mypatch(dummy_peony_client,
                             '_twitter_configuration', task):
                    await dummy_peony_client.upload_media(media)

            assert req.called

        if input_type == 'file':
            media.close()
        if media_file is not None:
            media_file.close()


@pytest.mark.asyncio
async def test_upload_media_exception():
    async with DummyPeonyClient() as dummy_peony_client:
        with pytest.raises(TypeError):
            await dummy_peony_client.upload_media([])


@pytest.mark.asyncio
async def test_upload_media_chunked(medias):
    async with DummyPeonyClient() as dummy_peony_client:
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
async def test_upload_media_size_limit(medias):
    async with DummyPeonyClient() as dummy_peony_client:
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


async def chunked_upload(media, file):
    async with DummyPeonyClient() as dummy_peony_client:
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


@pytest.mark.usefixtures('medias')
@pytest.mark.asyncio
@pytest.mark.parametrize('media', medias.values())
async def test_chunked_upload(media):
    data = io.BytesIO(media.content)
    await chunked_upload(media, data)


@pytest.mark.asyncio
async def test_chunked_upload_async_input(medias):
    async with aiofiles.open(str(medias['bloom'].cache), 'rb') as aiofile:
        await chunked_upload(medias['bloom'], aiofile)


@pytest.mark.asyncio
async def test_chunked_upload_fail(medias):
    async with DummyPeonyClient() as client:
        media = medias['video']
        media_data = await media.download()

        chunk_size = 1024**2

        dummy_request = DummyRequest(client, media, chunk_size, True)

        with patch.object(client, 'request',
                          side_effect=dummy_request):
            with patch.object(asyncio, 'sleep', side_effect=dummy) as sleep:
                with pytest.raises(peony.exceptions.MediaProcessingError):
                    await client.upload_media(
                        media_data, chunk_size=chunk_size, chunked=True
                    )
                    sleep.assert_called_with(5)


class MediaRequest:

    def __init__(self, url):
        self.url = url

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        self.req = await self.session.get(self.url)

        return self.req

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.req.close()
        self.session.close()


class MediaPeonyClient(PeonyClient):

    async def _get_twitter_configuration(self):
        return {'photo_size_limit': 3 * 1024**2}

    async def _get_user(self):
        return {}


@pytest.mark.online
@pytest.mark.asyncio
async def test_upload_from_url(url):
    async with MediaPeonyClient("", "") as dummy_peony_client:
        async with MediaRequest(url) as media_request:
            async def dummy_get(get_url):
                assert get_url == url
                return media_request

            async def dummy_request(url, method, future, data=None,
                                    skip_params=None):
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


@pytest.mark.online
@pytest.mark.asyncio
async def test_upload_from_request(url):
    async with MediaPeonyClient("", "") as dummy_peony_client:
        async with MediaRequest(url) as media_request:
            async def dummy_request(url, method, future, data=None,
                                    skip_params=None):
                assert url == dummy_peony_client.upload.media.upload.url()
                assert method.lower() == 'post'
                assert data['media'] == media_request.content
                assert skip_params
                future.set_result(None)

            with patch.object(dummy_peony_client, 'request',
                              side_effect=dummy_request):
                await dummy_peony_client.upload_media(media_request)


@pytest.mark.online
@pytest.mark.asyncio
async def test_upload_type_error(url):
    async with DummyPeonyClient() as client:
        async with MediaRequest(url) as media_request:
            def fail(*args, **kwargs):
                pytest.fail("Did not raise TypeError")

            with pytest.raises(TypeError):
                with patch.object(client, 'request', side_effect=fail):
                    await client.upload_media(media_request.content,
                                              chunked=True)
