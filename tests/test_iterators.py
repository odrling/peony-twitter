# -*- coding: utf-8 -*-

import pytest

from peony import iterators

from . import MockIteratorRequest

data = [{"id": 1, "text": "Hello"}]


@pytest.mark.parametrize("response", (data, {"statuses": data}))
def test_get_data(response):
    iterator = iterators.with_max_id(MockIteratorRequest)
    assert iterator.get_data(response) == data


def test_get_data_incorrect():
    iterator = iterators.with_max_id(MockIteratorRequest)
    assert iterator.get_data(data[0]) == []


@pytest.mark.parametrize("dict_resp", (False, True))
@pytest.mark.asyncio
async def test_max_id(dict_resp):
    MockIteratorRequest.kwargs = dict(max_id=499, dict=dict_resp)
    responses = iterators.with_max_id(MockIteratorRequest)

    ids = set()
    async for response in responses:
        if dict_resp:
            response = response["statuses"]

        new_ids = {user["id"] for user in response}
        size_before = len(ids)
        ids |= new_ids

        assert len(new_ids) > 0

        if len(ids) < len(new_ids) + size_before or len(ids) > 500:
            break

    assert len(ids) == 500


@pytest.mark.parametrize("dict_resp", (False, True))
@pytest.mark.asyncio
async def test_since_id(dict_resp):
    MockIteratorRequest.kwargs = dict(since_id=499, count=10, dict=dict_resp)
    responses = iterators.with_since_id(
        MockIteratorRequest, fill_gaps=False, force=False
    )

    ids = set()
    async for response in responses:
        if dict_resp:
            response = response["statuses"]

        new_ids = {user["id"] for user in response}
        size_before = len(ids)
        ids |= new_ids

        assert len(new_ids) > 0

        if len(ids) != len(new_ids) + size_before or len(ids) > 10:
            break

    assert len(ids) == 10


@pytest.mark.asyncio
async def test_since_id_force():
    MockIteratorRequest.kwargs = dict(since_id=499, count=10)
    responses = iterators.with_since_id(
        MockIteratorRequest, fill_gaps=False, force=True
    )

    ids = set()
    async for response in responses:
        new_ids = {user["id"] for user in response}
        size_before = len(ids)
        ids |= new_ids

        if len(new_ids) == 0:
            break

        if len(ids) != len(new_ids) + size_before or len(ids) > 10:
            break

    assert len(ids) == 10


@pytest.mark.asyncio
async def test_fill_gaps():
    MockIteratorRequest.kwargs = dict(since_id=499)
    responses = iterators.with_since_id(
        MockIteratorRequest, fill_gaps=True, force=False
    )

    ids = set()
    async for response in responses:
        new_ids = {user["id"] for user in response}
        ids |= new_ids

        if len(new_ids) == 0:
            raise AssertionError("Iteration should have stopped here")

        if len(ids) > 500:
            break

    assert len(ids) == 500


@pytest.mark.asyncio
async def test_fill_gaps_force():
    MockIteratorRequest.kwargs = dict(since_id=499)
    responses = iterators.with_since_id(MockIteratorRequest, fill_gaps=True, force=True)

    ids = set()
    async for response in responses:
        new_ids = {user["id"] for user in response}
        size_before = len(ids)
        ids |= new_ids

        if len(new_ids) == 0:
            break

        if len(ids) != len(new_ids) + size_before or len(ids) > 500:
            break

    assert len(ids) == 500


@pytest.mark.asyncio
async def test_cursor():
    MockIteratorRequest.kwargs = dict(cursor=500)
    responses = iterators.with_cursor(MockIteratorRequest)

    ids = set()
    async for response in responses:
        new_ids = set(response["ids"])
        size_before = len(ids)
        ids |= new_ids

        if len(ids) != len(new_ids) + size_before or len(ids) > 500:
            break

    assert len(ids) == 500
