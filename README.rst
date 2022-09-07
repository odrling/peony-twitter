Asynchronous Twitter API client for Python 3.6+
===============================================


.. image:: https://codecov.io/gh/odrling/peony-twitter/branch/master/graph/badge.svg
  :target: https://codecov.io/gh/odrling/peony-twitter

.. image:: https://readthedocs.org/projects/peony-twitter/badge/?version=stable
  :target: https://peony-twitter.readthedocs.io/en/stable/?badge=stable
  :alt: Documentation Status

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black


Installation
------------

To install this module simply run::

    pip install 'peony-twitter[all]'

This will install all the modules required to make peony run out of the box.
You might feel like some of them are not fit for your needs.
Check `Advanced installation`_ for more information about how to install only
the modules you will need.

.. _Advanced installation: https://peony-twitter.readthedocs.io/en/latest/adv_usage/install.html#adv-install

Authorize your client
---------------------

You can use ``peony.oauth_dance`` to authorize your client:

.. code-block:: python

    >>> from peony.oauth_dance import oauth_dance
    >>> tokens = oauth_dance(YOUR_CONSUMER_KEY, YOUR_CONSUMER_SECRET)
    >>> from peony import PeonyClient
    >>> client = PeonyClient(**tokens)

This should open a browser to get a pin to authorize your application.


Getting started
---------------

You can easily create a client using the class ``PeonyClient``.
Make sure to get your api keys and access tokens from
`Twitter's application management page`_ and/or to `Authorize your client`_

.. code-block:: python

    import asyncio

    # NOTE: the package name is peony and not peony-twitter
    from peony import PeonyClient

    # create the client using your api keys
    client = PeonyClient(consumer_key=YOUR_CONSUMER_KEY,
                         consumer_secret=YOUR_CONSUMER_SECRET,
                         access_token=YOUR_ACCESS_TOKEN,
                         access_token_secret=YOUR_ACCESS_TOKEN_SECRET)

    # this is a coroutine
    req = client.api.statuses.update.post(status="I'm using Peony!!")

    # run the coroutine
    asyncio.run(req)

.. _Twitter's application management page: https://apps.twitter.com

.. _Authorize your client: #authorize-your-client

Documentation
-------------

Read `Peony's documentation`_ on Read The Docs.

There is a `#peony`_ channel on the `Libera IRC network`_ for support and
discussion about Peony.
You can use `Libera's webchat`_ to connect to this channel from your web browser.

.. _Peony's documentation: https://peony-twitter.readthedocs.io
.. _#peony: irc://irc.libera.chat/peony
.. _Libera IRC network: https://libera.chat
.. _Libera's webchat: https://web.libera.chat/#peony

Contributing
------------

Every kind of contribution is appreciated.

If you find a bug please start an issue and if you're very motivated you can
create a pull request.

If you have a suggestion you can also start an issue and create a pull
request if you managed to make it work.

Tests
-----

To run the tests run:

.. code-block:: bash

    make

The first time this command is run it will install all the dependencies
which can take a bit of time.

The tests include a code style test. The code style is mostly PEP8, the only
exception so far being long urls included in docstrings and some imports
that are not at the top of the file (because they can't be there).

You can also use tox to run the tests, a configuration file is provided:

.. code-block:: bash

    tox
