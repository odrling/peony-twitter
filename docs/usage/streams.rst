=========
 Streams
=========

Streams can be used in peony using a async iterators (other than that
the usage is similar to that of REST API endpoints).


.. code-block:: python

    import asyncio
    from peony import PeonyClient, events
    client = peony.PeonyClient(**creds)


    async def track():
        stream = client.stream.statuses.filter.post.stream(track="uwu")

        # stream is an asynchronous iterator
        async for tweet in stream:
            # you can then access items as you would do with a
            # `PeonyResponse` object
            if peony.events.tweet(tweet):
                user_id = tweet['user']['id']
                username = tweet.user.screen_name

                msg = "@{username} ({id}): {text}"
                print(msg.format(username=username,
                                 id=user_id,
                                 text=tweet.text))

    if __name__ == '__main__':
        asyncio.run(track())
