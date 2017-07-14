import asyncio

import pytest

from . import medias


@pytest.fixture(name='medias')
def fixture_medias(event_loop):
    task = asyncio.gather(*[media.download() for media in medias.values()])
    event_loop.run_until_complete(task)
    return medias
