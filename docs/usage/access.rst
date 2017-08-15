=======================
 How to access the API
=======================
.. highlighting: python

You can easily access any Twitter API endpoint.
Just search for the endpoint that you need on `Twitter's documentation`_, then
you can make a request to this endpoint as:

.. code-block:: python

    client.twitter_subdomain.path.to.endpoint.method()

So to access
`GET statuses/home_timeline <https://dev.twitter.com/rest/reference/get/statuses/home_timeline>`_:

.. code-block:: python

    client.api.status.statuses.home_timeline.get()

.. _Twitter's documentation: https://dev.twitter.com/rest/reference


For a more complete example:

.. code-block:: python

    # NOTE: any reference to a `creds` variable in the documentation
    # examples should have this format
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

    # to access api.twitter.com/1.1/statuses/update.json
    # using the POST method with the parameter status
    async def track():
        return await client.api.statuses.update.post(status="Hello World!")

    # would GET subdomain.twitter.com/1.1/path.json if it were
    # an API endpoint
    async def path():
        return await client.subdomain.path.get()


see :ref:`adv_api` to access APIs that do not use the version '1.1'

.. note::
    Some endpoints require the use of characters that cannot be used as
    attributes such as
    `GET geo/id/:place_id <https://dev.twitter.com/rest/reference/get/geo/id/place_id>`_

    You can use the brackets instead:

    .. code-block:: python

        id = 20  # any status id would work as long as it exists
        client.api.statuses.show[id].get()

.. note::
    Arguments with a leading underscore are arguments that are used to
    change the behavior of peony for the request (e.g. `_headers` to add some
    additional headers to the request).
    Arguments without a leading underscore are parameters of the request you send.

Access the response data of a REST API endpoint
-----------------------------------------------

A call to a REST API endpoint should return a
:class:`~peony.data_processing.PeonyResponse` object if the request was
successful.

.. code-block:: python

    async def home():
        req = client.api.statuses.home_timeline.get(count=200, since_id=0, tweet_mode='extended')

        # this is a PeonyResponse object
        response = await req

        # you can iterate over the response object
        for tweet in response:
            # you can access items as you would do in a dictionnary
            user_id = tweet['user']['id']

            # or as you would access an attribute
            username = tweet.user.screen_name

            display_range = tweet.get('display_text_range', None)
            if display_range is not None:
                # get the text from the display range provided in the response
                # if present
                text = tweet.text[display_range[0]:display_range[1]]
            else:
                # just get the text
                text = tweet.text

            print("@{username} ({id}): {text}".format(username=username,
                                                      id=user_id,
                                                      text=text))


.. note::
    If ``extended_tweet`` is present in the response, attributes that are
    in ``tweet.extended_tweet`` can be retrieved right from ``tweet``:

    .. code-block:: python

        >>> tweet.display_text_range == tweet.extended_tweet.display_text_range
        True # if tweet.extended_tweet.display_range exists.

    Also, getting the ``text`` attribute of the data should always retrieve the
    full text of the tweet even when the data is truncated. So, there should
    be no need to look for a ``full_text`` attribute.

.. note::
    ``tweet.key`` and ``tweet['key']`` are always equivalent, even when the
    key is an attribute in ``extended_tweet`` or ``text``.


Access the response data of a Streaming API endpoint
----------------------------------------------------

A call to a Streaming API endpoint should return a
:class:`~peony.stream.StreamResponse` object.

.. code-block:: python

    async def track():
        req = client.stream.statuses.filter.post(track="uwu")

        # req is an asynchronous context
        async with req as stream:
            # stream is an asynchronous iterator
            async for tweet in stream:
                # check that you actually receive a tweet
                if peony.events.tweet(tweet):
                    # you can then access items as you would do with a
                    # `PeonyResponse` object
                    user_id = tweet['user']['id']
                    username = tweet.user.screen_name

                    msg = "@{username} ({id}): {text}"
                    print(msg.format(username=username,
                                     id=user_id,
                                     text=tweet.text))
