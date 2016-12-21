#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import html

import aiohttp

try:
    from . import peony, api, testdir
except SystemError:
    from __init__ import peony, testdir
    import api


class Home(peony.PeonyClient):

    def print_tweet(self, tweet):
        text = html.unescape(tweet.text)
        print("@{user.screen_name}: {text}".format(user=tweet.user,
                                                   text=text))
        print("-" * 10)

        self.last_tweet_id = tweet.id

    async def get_timeline(self, **kwargs):
        home = await self.api.statuses.home_timeline.get(**kwargs)

        for data in reversed(home):
            self.print_tweet(data)


@Home.event_stream
class UserStream(peony.EventStream):

    def stream_request(self):
        return self.userstream.user.get()

    @peony.events.on_connect.handler
    async def init_timeline(self):
        await self.get_timeline()

    @peony.events.on_tweet.handler
    def woohoo(self, data):
        self.print_tweet(data)

    @peony.events.on_restart.handler
    async def fill_gap(self):
        await self.get_timeline(since_id=self.last_tweet_id + 1)


async def main(loop):
    async with aiohttp.ClientSession() as session:
        client = Home(**api.keys, session=session, loop=loop)

        await asyncio.wait(client.get_tasks())


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(main(loop))
    loop.run_forever()
