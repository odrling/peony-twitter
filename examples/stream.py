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

    @peony.task
    async def get_timeline(self):
        home = await self.api.statuses.home_timeline.get()

        for t in home:
            print(html.unescape(t.text))


@Home.event_stream
class HomeStream(peony.EventStream):

    def stream_request(self):
        return self.userstream.user.get()

    @peony.event_handler(*peony.events.connect)
    def on_connect(self, data):
        print(len(data))

    @peony.event_handler(*peony.events.on_tweet)
    def woohoo(self, data):
        print(html.unescape(data.text))

if __name__ == '__main__':
    with aiohttp.ClientSession() as session:
        client = Home(**api.keys, session=session)

        client.loop.create_task(asyncio.wait(client.get_tasks()))
        client.loop.run_forever()
