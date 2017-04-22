# -*- coding: utf-8 -*-

import pytest
from peony import iterators

from . import MockIteratorRequest


@pytest.mark.asyncio
async def test_max_id():
    responses = iterators.with_max_id(MockIteratorRequest(), max_id=499)

    ids = set()
    async for response in responses:
        new_ids = {user['id'] for user in response}
        size_before = len(ids)
        ids |= new_ids

        if len(ids) < len(new_ids) + size_before or len(ids) > 500:
            break

    assert len(ids) == 500


@pytest.mark.asyncio
async def test_since_id():
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


@pytest.mark.asyncio
async def test_fill_gaps():
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


@pytest.mark.asyncio
async def test_cursor():
    responses = iterators.with_cursor(MockIteratorRequest(), cursor=500)

    ids = set()
    async for response in responses:
        new_ids = set(response['ids'])
        size_before = len(ids)
        ids |= new_ids

        if len(ids) != len(new_ids) + size_before or len(ids) > 500:
            break

    assert len(ids) == 500
