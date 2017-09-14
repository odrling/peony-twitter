import asyncio
import inspect
import pathlib
import socket

import aiohttp
import pytest
from aiohttp import web

from . import medias


@pytest.fixture
def event_loop():
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        return asyncio.new_event_loop()
    else:
        return loop


@pytest.fixture(name='medias')
def fixture_medias(event_loop):
    with aiohttp.ClientSession(loop=event_loop) as session:
        task = asyncio.gather(*[media.download(session=session)
                                for media in medias.values()])
        event_loop.run_until_complete(task)

    return medias


class AppMedias(web.Application):

    def __init__(self):
        super().__init__()

        file = pathlib.Path(inspect.getfile(inspect.currentframe()))
        self.router.add_static('/', str(file.parent / "cache"))

        self.srv = None
        self.handler = None

    def run(self, sock):
        loop = asyncio.get_event_loop()
        self.handler = self.make_handler()
        f = loop.create_server(self.handler, sock=sock)
        self.srv = loop.run_until_complete(f)

    async def stop(self):
        try:
            await self.srv.close()
        except:
            pass
        finally:
            await self.srv.wait_closed()
        await self.shutdown()
        await self.handler.shutdown(1.0)
        await self.cleanup()


@pytest.fixture
def port(event_loop):
    app = AppMedias()

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]

    app.run(sock)

    yield port

    event_loop.run_until_complete(app.stop())
    sock.close()


@pytest.fixture
def url(medias, port):
    return "http://127.0.0.1:%d/%s" % (port, medias['lady_peony'].filename)


@pytest.fixture
def media_request(event_loop, url):
    with aiohttp.ClientSession(loop=event_loop) as session:
        req = session.get(url)
        yield event_loop.run_until_complete(req)
        req.close()
