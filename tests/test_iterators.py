# -*- coding: utf-8 -*-

import asyncio

from peony import iterators
from . import MockIteratorRequest

loop = asyncio.get_event_loop()


def test_max_id():
    async def test():
        responses = iterators.with_max_id(MockIteratorRequest(), max_id=499)

        ids = set()
        async for response in responses:
            new_ids = {user['id'] for user in response}
            size_before = len(ids)
            ids |= new_ids

            if len(ids) < len(new_ids) + size_before or len(ids) > 500:
                break

        assert len(ids) == 500

    loop.run_until_complete(test())


def test_since_id():
    async def test():
        responses = iterators.with_since_id(MockIteratorRequest(), since_id=499,
                                            count=10, _fill_gaps=False,
                                            _force=False)

        ids = set()
        async for response in responses:
            new_ids = {user['id'] for user in response}
            size_before = len(ids)
            ids |= new_ids

            if len(ids) != len(new_ids) + size_before or len(ids) > 10:
                print(new_ids)
                break

        assert len(ids) == 10

    loop.run_until_complete(test())


def test_fill_gaps():
    async def test():
        responses = iterators.with_since_id(MockIteratorRequest(), since_id=499,
                                            _fill_gaps=True, _force=False)

        ids = set()
        async for response in responses:
            new_ids = {user['id'] for user in response}
            print("set %d" % len(new_ids))
            size_before = len(ids)
            ids |= new_ids

            if len(ids) != len(new_ids) + size_before or len(ids) > 500:
                break

        assert len(ids) == 500

    loop.run_until_complete(test())


def test_cursor():
    async def test():
        responses = iterators.with_cursor(MockIteratorRequest(), cursor=500)

        ids = set()
        async for response in responses:
            new_ids = set(response['ids'])
            size_before = len(ids)
            ids |= new_ids

            if len(ids) != len(new_ids) + size_before or len(ids) > 500:
                break

        assert len(ids) == 500

    loop.run_until_complete(test())
