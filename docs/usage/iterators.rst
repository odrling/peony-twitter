===========
 Iterators
===========

Sometimes you need to make several requests to the same API endpoint in order
to get all the data you want (e.g. getting more than 200 tweets of an user).
Some iterators are included in Peony and usable through the peony.iterators
module that deals with the actual iteration, getting all the responses you
need.

Cursor iterators
----------------

This is an iterator for endpoints using the `cursor` parameter
(e.g. followers/ids.json). The first argument given to the iterator is the
coroutine function that will make the request.

.. code-block:: python

    from peony import PeonyClient

    # creds being a dictionnary containing your api keys
    client = PeonyClient(**creds)

    async def get_followers(user_id, **additional_params):
        followers_ids = client.api.followers.ids.get.iterator.with_cursor(
            id=user_id,
            count=5000,
            **additional_params
        )

        followers = []
        async for data in followers_ids:
            followers.extend(data.ids)

        return followers

Max_id iterators
----------------

An iterator for endpoints using the `max_id` parameter
(e.g. statuses/user_timeline.json):

.. code-block:: python

    from peony import PeonyClient

    client = PeonyClient(**creds)

    async def get_tweets(user_id, n_tweets=1600, **additional_params):
        responses = client.api.statuses.user_timeline.get.iterator.with_max_id(
            user_id=user,
            count=200,
            **additional_params
        )

        user_tweets = []

        async for tweets in responses:
            user_tweets.extend(tweets)

            if len(user_tweets) >= n_tweets:
                user_tweets = user_tweets[:n_tweets]
                break

        return user_tweets

Since_id iterators
------------------

An iterator for endpoints using the `since_id` parameter
(e.g. statuses/home_timeline.json):

.. code-block:: python

    import asyncio
    import html

    from peony import PeonyClient

    client = peony.PeonyClient(**creds)

    async def get_home(since_id=None, **params):
        request = client.api.statuses.home_timeline.get
        responses = request.iterator.with_since_id(
            count=200,
            **params
        )

        home = []
        async for tweets in responses:
            for tweet in reversed(tweets):
                text = html.unescape(tweet.text)
                print("@{user.screen_name}: {text}".format(user=tweet.user,
                                                           text=text))
                print("-"*10)

            await asyncio.sleep(120)

        return sorted(home, key=lambda tweet: tweet.id)
