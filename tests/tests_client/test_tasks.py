
import pytest
from asynctest import patch

import peony
from peony.general import twitter_api_version, twitter_base_api_url

from . import DummyClient, MockSession


class SetupClientTest(DummyClient):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._session = MockSession()
        self.a, self.b, self.c = "", "", {}


class TasksClientTest(DummyClient):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tasks_tests = [False, False, True]

    @peony.task
    async def task_a(self):
        self.tasks_tests[0] = True

    @peony.task
    async def task_b(self):
        self.tasks_tests[1] = True

    async def not_a_task(self):
        self.tasks_tests[2] = False


@pytest.mark.asyncio
async def test_tasks():
    async with TasksClientTest() as client:
        with patch.object(client, 'request') as request:
            await client.run_tasks()
            base_url = twitter_base_api_url.format(api='api',
                                                   version=twitter_api_version)
            assert request.called_with(method='get',
                                       url=base_url + '/test.json')
            assert request.called_with(method='get',
                                       url=base_url + '/endpoint.json')

            assert all(client.tasks_tests)


def test_run():
    client = TasksClientTest()
    with patch.object(client, 'request') as request:
        client.run()
        base_url = twitter_base_api_url.format(api='api',
                                               version=twitter_api_version)
        assert request.called_with(method='get',
                                   url=base_url + '/test.json')
        assert request.called_with(method='get',
                                   url=base_url + '/endpoint.json')

        assert all(client.tasks_tests)
