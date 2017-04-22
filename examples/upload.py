#!/usr/bin/env python3

import asyncio
import os.path

try:
    from . import peony, api
except (SystemError, ImportError):
    from __init__ import peony
    import api

client = peony.PeonyClient(**api.keys)


async def send_tweet_with_media():
    status = input("status: ")

    path = ""
    while not path and not os.path.exists(path):
        path = input('file to upload:\n')

    media = await client.upload_media(
        path,
        auto_convert=True,
        chunk_size=2**18,
        chunked=True,
        max_size=(2048, 2048)
    )
    await client.api.statuses.update.post(status=status,
                                          media_ids=media.media_id)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(send_tweet_with_media())
