=======================
 How to access the API
=======================
.. highlighting: python

You can easily access any Twitter API endpoint:

.. code-block:: python

    creds = dict(consumer_key=YOUR_CONSUMER_KEY,
                 consumer_secret=YOUR_CONSUMER_SECRET,
                 access_token=YOUR_ACCESS_TOKEN,
                 access_token_secret=YOUR_ACCESS_TOKEN_SECRET)

    client = PeonyClient(**creds)

    # to access api.twitter.com/1.1/statuses/home_timeline.json
    # using the GET method with the parameters count and since_id
    async def home():
        return await client.api.statuses.home_timeline.get(count=200,
                                                           since_id=0)

    # to access userstream.twitter.com/1.1/statuses/filter.json
    # using the POST method with the parameter track
    async def track():
        req = client.stream.statuses.filter.post(track="uwu")
        async with req as ressource:
            pass  # do something, see next chapter

    # would GET subdomain.twitter.com/1.1/path.json if it were
    # an API endpoint
    async def path():
        return await client.subdomain.path.get()


see :ref:`adv_api` to access APIs that do not use the version '1.1'

*Note*: Arguments with a leading underscore are arguments that are used to
change the behavior of peony for the request (e.g. `_headers` to add some
additional headers to the request).
Arguments without a leading underscore are parameters of the request you send.


Access the response data of a REST API endpoint
-----------------------------------------------

A call to a REST API endpoint should return a PeonyResponse object.

.. code-block:: python

    async def home():
        req = client.api.statuses.home_timeline.get(count=200, since_id=0)

        # this is a PeonyResponse object
        response = await req

        # you can iterate over the response object
        for tweet in response:
            # you can access items as you would do in a dictionnary
            user_id = tweet['user']['id']

            # or as you would access an attribute
            username = tweet.user.screen_name

            print("@{username} ({id}): {text}".format(username=username,
                                                      id=user_id,
                                                      text=tweet.text))


Access the response data of a Streaming API endpoint
----------------------------------------------------

A call to a Streaming API endpoint should return a StreamContext object, that
yields a StreamResponse object.

.. code-block:: python

    async def track():
        ctx = client.stream.statuses.filter.post(track="uwu")

        # ctx is an asynchronous context (StreamContext)
        async with ctx as stream:
            # stream is an asynchronous iterator (StreamResponse)
            async for tweet in stream:
                # you can then access items as you would do with a
                # PeonyResponse object
                user_id = tweet['user']['id']
                username = tweet.user.screen_name

                msg = "@{username} ({id}): {text}"
                print(.format(username=username,
                              id=user_id,
                              text=tweet.text))
