================
   Quickstart
================

Installation
------------

To install this module simply run::

    $ pip install 'peony-twitter[all]'

This will install all the modules required to make peony run out of the box.
You might feel like some of them are not fit for your needs.
Check :ref:`adv_install` for more information about how to install only
the modules you will need.

.. _auth:

Authorize your client
---------------------

You can use :func:`peony.oauth_dance.oauth_dance` to authorize your client:

.. code-block:: python

    >>> from peony.oauth_dance import oauth_dance
    >>> tokens = oauth_dance(YOUR_CONSUMER_KEY, YOUR_CONSUMER_SECRET)
    >>> from peony import PeonyClient
    >>> client = PeonyClient(**tokens)

This should open a browser to get a pin to authorize your application.

Getting started
---------------

You can easily create a client using :class:`~peony.client.PeonyClient`.
Make sure to get your api keys and access tokens from
`Twitter's application management page`_ and/or to :ref:`auth`

.. note:: The package name is ``peony`` and not ``peony-twitter``

.. code-block:: python

    import asyncio

    from peony import PeonyClient

    # create the client using your api keys
    client = PeonyClient(consumer_key=YOUR_CONSUMER_KEY,
                         consumer_secret=YOUR_CONSUMER_SECRET,
                         access_token=YOUR_ACCESS_TOKEN,
                         access_token_secret=YOUR_ACCESS_TOKEN_SECRET)

    async def getting_started():
        # print your twitter username or screen name
        user = await client.user
        print("I am @%s" % user.screen_name)
        # tweet about your sudden love for peony
        await client.api.statuses.update.post(status="I'm using Peony!!")

    # run the coroutine
    asyncio.run(getting_started())

.. _Twitter's application management page: https://apps.twitter.com
