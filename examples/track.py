#!/usr/bin/env python3
import asyncio

try:
    from . import api, peony
except Exception:
    import api
    from __init__ import peony

client = peony.PeonyClient(**api.keys)


async def track():
    stream = client.stream.statuses.filter.post.stream(track="uwu")

    # stream is an asynchronous iterator
    async for tweet in stream:
        # you can then access items as you would do with a
        # `PeonyResponse` object
        if peony.events.tweet(tweet):
            user_id = tweet["user"]["id"]
            username = tweet.user.screen_name

            msg = "@{username} ({id}): {text}"
            print(msg.format(username=username, id=user_id, text=tweet.text))


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(track())
