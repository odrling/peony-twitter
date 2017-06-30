#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import html
import pprint

try:
    from . import peony, api
except (SystemError, ImportError):
    from __init__ import peony
    import api


peony.set_debug()


def print_data(func):

    def decorated(self, tweet):
        if self.last_tweet_id < tweet.id:
            print(func(self, tweet) + "\n" + "-" * 10)

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
        request = self.api.statuses.home_timeline.get(
            count=200,
            since_id=self.last_tweet_id
        )
        responses = request.iterator.with_since_id()

        async for tweets in responses:
            for tweet in reversed(tweets):
                if 'retweeted_status' in tweet:
                    self.print_rt(tweet)
                else:
                    self.print_tweet(tweet)

            break


@peony.events.priority(-5)
def on_favorited(data, client):
    return peony.events.on_favorite(data) and data.target.id == client.user.id


@Home.event_stream
class UserStream(peony.EventStream):

    def stream_request(self):
        return self.userstream.user.get(stall_warnings="true", replies="all")

    @peony.events.on_connected.handler
    async def init_timeline(self):
        await self.get_timeline()

    @peony.events.on_retweeted_status.handler
    def on_retweet(self, data):
        self.print_rt(data)

    @peony.events.on_tweet.handler
    def on_tweet(self, data):
        self.print_tweet(data)

    @peony.events.reconnecting_in.handler
    async def reconnecting(self, data):
        print("reconnecting in %ss" % data.reconnecting_in)

    @peony.events.on_restart.handler
    async def restart_notice(self):
        print("*Stream restarted*\n" + "-" * 10)
        await self.get_timeline()

    @peony.events.on_dm.handler
    def direct_message(self, data):
        dm = data.direct_message
        text = html.unescape(dm.text)
        fmt = "@{sender} → @{recipient}: {text}\n" + "-" * 10
        print(fmt.format(sender=dm.sender.screen_name,
                         recipient=dm.recipient.screen_name,
                         text=text))

    @on_favorited.handler
    def favorited(self, data):
        print(data.source.screen_name, "favorited:",
              html.unescape(data.target_object.text) + "\n" + "-" * 10)

    @peony.events.friends.handler
    def pass_friends(self):
        pass

    @peony.events.default.handler
    def default(self, data):
        print(pprint.pformat(data), "\n" + "-" * 10)


if __name__ == '__main__':
    home = Home(**api.keys)
    home.run()
