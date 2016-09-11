=========================================
 Use the Application only authentication
=========================================

The application only authentication is restricted to some endpoints.
See `the Twitter documentation page`_::

    import peony
    from peony import PeonyClient

    # NOTE: the bearer_token argument is not necessary
    client = PeonyClient(consumer_key=YOUR_CONSUMER_KEY,
                         consumer_secret=YOUR_CONSUMER_SECRET,
                         bearer_token=YOUR_BEARER_TOKEN,
                         auth=peony.oauth.OAuth2Headers)

.. _the Twitter documentation page: https://dev.twitter.com/oauth/application-only
