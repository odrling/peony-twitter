#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio

try:
    from . import peony, api, testdir
except SystemError:
    from __init__ import peony, testdir
    import api


client = peony.PeonyClient(**api.keys)

async def get_home(since_id=None, **params):
    responses = peony.iterators.with_since_id(
        client.api.statuses.home_timeline.get,
        since_id=since_id,
        count=200,
        **params
    )

    home = []
    async for tweets in responses:
        home.extend(tweets)
        print(len(home))
        input("waiting for input")

    return sorted(home, key=lambda tweet: tweet.id)

def main():
    loop = asyncio.get_event_loop()
    home_timeline = loop.run_until_complete(get_home())

    for tweet in home_timeline[-10:]:
        print(tweet.text)

if __name__ == '__main__':
    main()
