#!/usr/bin/env python3

import asyncio
import base64
from urllib.parse import urlparse

try:
    from . import peony, api, testdir
except SystemError:
    from __init__ import peony, testdir
    import api

client = peony.PeonyClient(**api.keys)

async def set_avi(path):
    with open(path, 'rb') as avi:
        avib64 = base64.b64encode(avi.read()).decode('utf-8')

    await client.api.account.update_profile_image.post(image=avib64)


def main():
    path = input("avi: ")
    path = urlparse(path).path.strip(" \"'")

    loop = asyncio.get_event_loop()
    loop.run_until_complete(set_avi(path))

if __name__ == '__main__':
    main()
