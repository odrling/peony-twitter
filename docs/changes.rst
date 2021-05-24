.. _breaking_changes:

================
Breaking changes
================

This page keeps track of the main changes that could cause your
current application to stop working when you update Peony.

--------------------
Changes in Peony 2.0
--------------------

Twitter exceptions inherit from HTTP exceptions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The name of the exceptions related to the HTTP status of the response are now
prefixed with ``HTTP``.
Here is a list of those new exceptions:

* :class:`~peony.exceptions.HTTPNotModified`
* :class:`~peony.exceptions.HTTPBadRequest`
* :class:`~peony.exceptions.HTTPUnauthorized`
* :class:`~peony.exceptions.HTTPForbidden`
* :class:`~peony.exceptions.HTTPNotFound`
* :class:`~peony.exceptions.HTTPNotAcceptable`
* :class:`~peony.exceptions.HTTPConflict`
* :class:`~peony.exceptions.HTTPGone`
* :class:`~peony.exceptions.HTTPEnhanceYourCalm`
* :class:`~peony.exceptions.HTTPUnprocessableEntity`
* :class:`~peony.exceptions.HTTPTooManyRequests`
* :class:`~peony.exceptions.HTTPInternalServerError`
* :class:`~peony.exceptions.HTTPBadGateway`
* :class:`~peony.exceptions.HTTPServiceUnavailable`
* :class:`~peony.exceptions.HTTPGatewayTimeout`


The exceptions related to twitter error codes now inherit from those
exceptions, this means that the order of execution of your ``except`` blocks
now matter. The "HTTP" exceptions should be handled after the exceptions
related to twitter error codes.

This works as expected:

.. code-block:: python

    except ReadOnlyApplication:
        ...
    except HTTPForbidden:
        ...


Here, :class:`~peony.exceptions.ReadOnlyApplication` will be caught by the first ``except`` block instead of the more specific ``except ReadOnlyApplication``.

.. code-block:: python

    except HTTPForbidden:
        ...
    except ReadOnlyApplication:
        ...

:class:`~peony.client.PeonyClient` doesn't have a ``twitter_configuration`` attribute anymore
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

`Twitter removed the endpoint used to set this attribute's value
<https://twittercommunity.com/t/retiring-the-1-1-configuration-endpoint/153319>`_,
because they never really changed. So you can use constants instead of using
the values from this attribute.

`Here is an exemple of what this endpoint used to return in case you need it.
<https://hikari.butaishoujo.moe/b/f97a8847/twitter_configuration.json>`_


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
