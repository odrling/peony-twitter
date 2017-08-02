import asyncio

import aiohttp
import pytest

from . import medias


@pytest.fixture(name='medias')
def fixture_medias(event_loop):
    task = asyncio.gather(*[media.download() for media in medias.values()])
    event_loop.run_until_complete(task)
    return medias


@pytest.fixture
def media_request(medias, event_loop):
    session = aiohttp.ClientSession(loop=event_loop)
    req = session.get(medias['lady_peony'].url)
    yield event_loop.run_until_complete(req)
    req.close()
    session.close()
