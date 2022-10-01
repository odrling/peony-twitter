#!/usr/bin/env python3
import asyncio

try:
    from . import api
except Exception:
    from __init__ import api

import peony
import peony.oauth


async def get_user():
    client = peony.BasePeonyClient(**api.keys,
                                   auth=peony.oauth.OAuth2Headers,
                                   api_version="2",
                                   suffix="")

    async with client:
        username = "odrling"
        resp = await client.api.users.by.username[username].get()
        print(resp)


if __name__ == "__main__":
    asyncio.run(get_user())
