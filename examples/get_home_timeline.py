#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import html

try:
    from . import api, peony
except (SystemError, ImportError):
    import api
    from __init__ import peony


client = peony.PeonyClient(**api.keys)


async def get_home(**params):
    req = client.api.statuses.home_timeline.get(count=200, **params)
    responses = req.iterator.with_since_id()

    home = []
    async for tweets in responses:
        for tweet in reversed(tweets):
            text = html.unescape(tweet.text)
            print("@{user.screen_name}: {text}".format(user=tweet.user, text=text))
            print("-" * 10)

        await asyncio.sleep(180)

    return home


def main():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(get_home())


if __name__ == "__main__":
    main()
