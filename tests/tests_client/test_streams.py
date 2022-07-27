# -*- coding: utf-8 -*-

import peony
import peony.api
from peony import BasePeonyClient


class RequestTest:
    def __init__(self, expected_url, expected_method):
        self.expected_url = expected_url
        self.expected_method = expected_method

    async def __call__(self, *args, url=None, method=None, future=None, **kwargs):
        assert url == self.expected_url
        assert method == self.expected_method
        future.set_result(True)
        return True


request_test = RequestTest


def test_add_event_stream():
    class ClientTest(BasePeonyClient):
        pass

    assert peony.commands.EventStream not in ClientTest._streams

    ClientTest.event_stream(peony.commands.EventStream)
    assert peony.commands.EventStream in ClientTest._streams
