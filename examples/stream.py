#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import html
from pprint import pprint

try:
    from . import peony, api, testdir
except (SystemError, ImportError):
    from __init__ import peony, testdir
    import api


def print_data(func):

    def decorated(self, tweet):
        if self.last_tweet_id < tweet.id:
            print(func(self, tweet) + "\n" + "-"*10)

            self.last_tweet_id = tweet.id

    return decorated


class Home(peony.PeonyClient):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.last_tweet_id = 1

    @print_data
    def print_rt(self, tweet):
        text = html.unescape(tweet.retweeted_status.text)
        fmt = "@{user.screen_name} RT @{rt.user.screen_name}: {text}"
        return fmt.format(user=tweet.user, rt=tweet.retweeted_status,
                          text=text)

    @print_data
    def print_tweet(self, tweet):
        text = html.unescape(tweet.text)
        fmt = "@{user.screen_name}: {text}"
        return fmt.format(user=tweet.user, text=text)

    async def get_timeline(self):
        responses = self.api.statuses.home_timeline.get.iterator.with_since_id(
            count=200,
            since_id=self.last_tweet_id
        )

        async for tweets in responses:
            for tweet in reversed(tweets):
                if 'retweeted_status' in tweet:
                    self.print_rt(tweet)
                else:
                    self.print_tweet(tweet)

            break


@Home.event_stream
class UserStream(peony.EventStream):

    def stream_request(self):
        return self.userstream.user.get(stall_warnings="true", replies="all")

    @peony.events.on_connect.handler
    async def init_timeline(self):
        await self.get_timeline()

    @peony.events.on_retweeted_status.handler
    def on_retweet(self, data):
        self.print_rt(data)

    @peony.events.on_tweet.handler
    def on_tweet(self, data):
        pprint(data)
        self.print_tweet(data)

    @peony.events.on_restart.handler
    def restart_notice(self):
        print("*Stream restarted*\n" + "-" * 10)

    @peony.events.on_dm.handler
    def direct_message(self, data):
        dm = data.direct_message
        text = html.unescape(dm.text)
        fmt = "@{sender} → @{recipient}: {text}\n" + "-"*10
        print(fmt.format(sender=dm.sender.screen_name,
                         recipient=dm.recipient.screen_name,
                         text=text))

    @peony.events.on_favorite.handler
    def on_favorite(self, data):
        if data.source.id != self.user.id:
            print(data.source.screen_name, "favorited:",
                  html.unescape(data.target_object.text) + "\n" + "-"*10)

    @peony.events.default.handler
    def default(self, data):
        pprint(data, "\n" + "-"*10)

if __name__ == '__main__':
    client = Home(**api.keys)
    client.run()
