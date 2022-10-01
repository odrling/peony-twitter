#!/usr/bin/env python3
import asyncio

try:
    from . import api
except Exception:
    from __init__ import api

import peony
import peony.oauth
from pprint import pprint


async def track():
    client = peony.BasePeonyClient(**api.keys,
                                   auth=peony.oauth.OAuth2Headers,
                                   api_version="2",
                                   suffix="")

    async with client:
        resp = await client.api.tweets.search.stream.rules.get()

        # needed to set a rule before starting the stream
        # only need to be run once
        if not resp.get('data'):
            data = {'add': [{'value': "uwu"}]}
            resp = await client.api.tweets.search.stream.rules.post(_json=data)

        print(resp)

        fields = {
            "tweet.fields": ["created_at", "entities", "referenced_tweets"]
        }
        stream = client.api.tweets.search.stream.get.stream(**fields)

        async for tweet in stream:
            pprint(tweet)


if __name__ == "__main__":
    asyncio.run(track())
