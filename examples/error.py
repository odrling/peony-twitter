#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio

import peony

try:
    from . import api  # , peony
except (SystemError, ImportError):
    # from __init__ import peony
    import api

loop = asyncio.get_event_loop()
client = peony.BasePeonyClient(**api.keys, loop=loop)


async def search_test():
    try:
        # Known suspended user account, expected to raise
        # peony.exceptions.Forbidden
        result = await asyncio.gather(
            client.api.users.show.get(screen_name="realDonaldTrump")
        )
    except peony.exceptions.Forbidden as e:
        print("exception info: %r" % e)
    else:
        print(result[0])


if __name__ == "__main__":
    loop.run_until_complete(search_test())
