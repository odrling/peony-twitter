#!/usr/bin/env python3

import asyncio
import os

try:
    from . import peony, api, testdir
except SystemError:
    from __init__ import peony, testdir
    import api

client = peony.PeonyClient(**api.keys)


async def send_tweet_with_media():
    status = input("status: ")
    path = input('file to upload:\n')
    if not path:
        dirname = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(dirname, "test.gif")

    media = await client.upload_media(path, auto_convert=True)
    await client.api.statuses.update.post(status=status,
                                          media_ids=media.media_id)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(send_tweet_with_media())
