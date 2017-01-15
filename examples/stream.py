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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.last_tweet_id = 0

    def print_tweet(self, tweet):
        if self.last_tweet_id < tweet.id:
            if 'retweeted_status' in tweet:
                text = html.unescape(tweet.retweeted_status.text)
                fmt = "@{user.screen_name} RT @{rt.user.screen_name}: {text}"
                print(fmt.format(user=tweet.user,
                                 rt=tweet.retweeted_status,
                                 text=text))
            else:
                text = html.unescape(tweet.text)
                print("@{user.screen_name}: {text}".format(user=tweet.user,
                                                           text=text))

            print("-" * 10)

            self.last_tweet_id = tweet.id

    async def get_timeline(self):
        responses = self.api.statuses.home_timeline.get.iterator.with_since_id(
            count=200,
            since_id=self.last_tweet_id
        )

        async for tweets in responses:
            for tweet in reversed(tweets):
                self.print_tweet(tweet)

            break


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
    def restart_notice(self):
        print("*Stream restarted*\n" + "-" * 10)


if __name__ == '__main__':
    client = Home(**api.keys)
    client.run()
