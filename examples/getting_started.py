#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio

try:
    from . import api, peony
except (SystemError, ImportError):
    import api
    from __init__ import peony

loop = asyncio.get_event_loop()
client = peony.PeonyClient(**api.keys, loop=loop)


async def getting_started():
    # print your twitter username or screen name
    user = await client.user
    print("I am @%s" % user.screen_name)
    # tweet about your sudden love for peony
    await client.api.statuses.update.post(status="I'm using Peony!!")


if __name__ == "__main__":
    loop.run_until_complete(getting_started())
