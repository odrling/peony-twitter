#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio

try:
    from . import api, peony
except (SystemError, ImportError):
    import api
    from __init__ import peony


async def search_test():
    async with peony.PeonyClient(**api.keys) as client:
        print(await client.user)


if __name__ == "__main__":
    asyncio.run(search_test())
