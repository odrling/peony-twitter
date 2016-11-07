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

    @staticmethod
    def print_tweet(tweet):
        text = html.unescape(tweet.text)
        print("@{user.screen_name}: {text}".format(user=tweet.user,
                                                   text=text))
        print("-" * 10)

    @peony.task
    async def get_timeline(self):
        home = await self.api.statuses.home_timeline.get()

        for data in reversed(home):
            self.print_tweet(data)

@Home.event_stream
class UserStream(peony.EventStream):

    def stream_request(self):
        return self.userstream.user.get()

    @peony.event_handler(*peony.events.on_tweet)
    def woohoo(self, data):
        self.print_tweet(data)

if __name__ == '__main__':
    with aiohttp.ClientSession() as session:
        client = Home(**api.keys, session=session)

        client.loop.create_task(asyncio.wait(client.get_tasks()))
        client.loop.run_forever()
