.. highlighting: python

:mod:`peony` --- an asynchonous Twitter API client for Python 3.5+
==================================================================

.. py:module:: peony
    :synopsis: an asynchonous Twitter API client for Python 3.5+

.. autoclass:: PeonyClient
    :members:
    :undoc-members:

.. py:class:: task

    decorator to create a task in a :class:`PeonyClient` subclass

.. py:module:: peony.oauth

.. py:class:: PeonyHeaders

    | Parent class of :class:`OAuth1Headers` and :class:`OAuth2Headers`.
    | :class:`peony.PeonyClient` calls :func:`prepare_request` before each request

.. autoclass:: OAuth1Headers(consumer_key, consumer_secret[, token_access, token_secret])
    :members:

.. autoclass:: OAuth2Headers(consumer_key, consumer_secret[, bearer_token])
    :members:
