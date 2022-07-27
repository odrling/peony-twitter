#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import html

try:
    from . import api, peony
except (SystemError, ImportError):
    import api
    from __init__ import peony


def print_data(func):
    def decorated(self, tweet):
        if self.last_id < tweet.id:
            print(func(self, tweet) + "\n" + "-" * 10)

    return decorated


class Home(peony.PeonyClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.last_id = 1

    @print_data
    def print_rt(self, tweet):
        text = html.unescape(tweet.retweeted_status.text)
        fmt = "@{user.screen_name} RT @{rt.user.screen_name}: {text}"
        return fmt.format(user=tweet.user, rt=tweet.retweeted_status, text=text)

    @print_data
    def print_tweet(self, tweet):
        text = html.unescape(tweet.text)
        fmt = "@{user.screen_name}: {text}"
        return fmt.format(user=tweet.user, text=text)

    @peony.task
    async def get_timeline(self):
        request = self.api.statuses.home_timeline.get(count=200, since_id=self.last_id)
        responses = request.iterator.with_since_id(fill_gaps=True)

        async for tweets in responses:
            for tweet in reversed(tweets):
                if "retweeted_status" in tweet:
                    self.print_rt(tweet)
                else:
                    self.print_tweet(tweet)

            print(len(tweets))
            await asyncio.sleep(120)


if __name__ == "__main__":
    client = Home(**api.keys)
    client.run()
