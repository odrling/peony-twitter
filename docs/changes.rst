.. _breaking_changes:

================
Breaking changes
================

This page keeps track of the main changes that could cause your
current application to stop working when you update Peony.

--------------------
Changes in Peony 1.1
--------------------

Error Handlers must inherit from :class:`~peony.utils.ErrorHandler`
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Error handler should now inherit from :class:`~peony.utils.ErrorHandler`.
This ensures that the exception will correctly be propagated when you
make a request. See :ref:`error_handlers` for more details on how to
create an error handler.

:class:`~peony.client.PeonyClient`'s properties are now awaitables
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

It wasn't very documented until now, but
:class:`~peony.client.PeonyClient` has two properties ``user`` and
``twitter_configuration``. They used to be created during the first request
made by the client which led to some weird scenarios where these properties could
return ``None``.

Now these properties are awaitables, which can make the syntax a bit more
complicated to use, but now you will never be left with a ``None``.

.. code-block:: python

    client = PeonyClient(**api_keys)
    user = await client.user  # assuming we are in a coroutine
    print(user.screen_name)   # "POTUS"

Init tasks don't exist anymore
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

I think nobody used them anyway but just in case anyone did.
They were used to create the ``user`` and ``twitter_configuration``
properties in :class:`~peony.client.PeonyClient`.
