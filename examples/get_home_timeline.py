#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import html

try:
    from . import peony, api, testdir
except SystemError:
    from __init__ import peony, testdir
    import api


client = peony.PeonyClient(**api.keys)

async def get_home(since_id=None, **params):
    responses = peony.iterators.with_since_id(
        client.api.statuses.home_timeline.get,
        count=200,
        **params
    )

    home = []
    async for tweets in responses:
        for tweet in reversed(tweets):
            text = html.unescape(tweet.text)
            print("@{user.screen_name}: {text}".format(user=tweet.user,
                                                       text=text))
            print("-" * 10)

        await asyncio.sleep(0)

    return sorted(home, key=lambda tweet: tweet.id)


def main():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(get_home())

if __name__ == '__main__':
    main()
