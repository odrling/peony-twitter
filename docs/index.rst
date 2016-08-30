Peony's documentation
=====================

Peony is an asynchronous Twitter API client.

Installation
============

To install this module simply run::

    pip install peony-twitter

Getting started
===============

.. highlighting: python

You can easily create a client using the class `PeonyClient`.
Make sure to get your api keys and access tokens from
`Twitter's application management page`_ and/or to :ref:`auth`

*Note: the package name is peony and not peony-twitter*::

    import asyncio

    # Note: the package name is peony and not peony-twitter
    from peony import PeonyClient

    loop = asyncio.get_event_loop()

    # create the client using your api keys
    client = PeonyClient(consumer_key=YOUR_CONSUMER_KEY,
                         consumer_secret=YOUR_CONSUMER_SECRET,
                         access_token=YOUR_ACCESS_TOKEN,
                         access_token_secret=YOUR_ACCESS_TOKEN_SECRET)

    # this is a coroutine
    req = client.api.statuses.update.post(status="I'm using Peony!!")

    # run the coroutine
    loop.run_until_complete(req)

.. _Twitter's application management page: https://apps.twitter.com

Usage
=====

.. toctree::

    usage

Advanced Usage
==============

.. toctree::

    adv_usage


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
