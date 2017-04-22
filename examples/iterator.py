#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import html

try:
    from . import peony, api, testdir
except (SystemError, ImportError):
    from __init__ import peony, testdir
    import api


def print_data(func):

    def decorated(self, tweet):
        if self.last_tweet_id < tweet.id:
            #print(func(self, tweet) + "\n" + "-"*10)

            self.last_tweet_id = tweet.id
        else:
            print("nooo")

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

    @peony.task
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

            print(len(tweets))
            await asyncio.sleep(120)


if __name__ == '__main__':
    client = Home(**api.keys)
    client.run()
