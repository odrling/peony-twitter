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

        self.last_tweet = tweet

    async def get_timeline(self, **kwargs):
        home = await self.api.statuses.home_timeline.get(**kwargs)

        for data in reversed(home):
            self.print_tweet(data)

    @peony.task
    async def init_timeline(self):
        await self.get_timeline()

@Home.event_stream
class UserStream(peony.EventStream):

    def stream_request(self):
        return self.userstream.user.get()

    @peony.event_handler(*peony.events.on_tweet)
    def woohoo(self, data):
        self.print_tweet(data)

    @peony.event_handler(*peony.events.on_restart)
    async def fill_gap(self, data):
        await self.get_timeline(since_id=self.last_tweet.id+1)


if __name__ == '__main__':
    with aiohttp.ClientSession() as session:
        client = Home(**api.keys, session=session)

        client.loop.create_task(asyncio.wait(client.get_tasks()))
        client.loop.run_forever()
