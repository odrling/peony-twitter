.. highlighting: python
.. _adv_api:

Accessing an API using a different API version
==============================================

There actually two ways:

* create a client with an ``api_version`` argument
* provide the api version with the subdomain of the api when creating the path to the ressource

Create a client with a custom api version
-----------------------------------------

::

    # creds being a dict with your api_keys
    # notice the use of the `suffix` argument to change the default
    # extension ('.json')
    client = PeonyClient(**creds, api_version='1', suffix='')

    # params being the parameters of the request
    req = client['ads-api'].accounts[id].reach_estimate.get(**params)


Add a version when creating the request
---------------------------------------

::

    # notice the use of the `_suffix` argument to change the default
    # extension for a request

    # using a tuple as key
    req = client['ads-api', '1'].accounts[id].reach_estimate.get(_suffix='',
                                                                 **kwargs)

    # using a dict as key
    ads = client[dict(api='ads-api', version='1')]
    req = ads.accounts[id].reach_estimate.get(**kwargs, _suffix='')

You can also add more arguments to the tuple or dictionnary::

    # with a dictionnary
    adsapi = dict(
        api='ads-api',
        version='1',
        suffix='',
        base_url='https://{api}.twitter.com/{version}'
    )

    req = client[adsapi].accounts[id].reach_estimate.get(**kwargs,)


    # with a tuple
    ads = client['ads-api', '1', '', 'https://{api}.twitter.com/{version}']
    req = ads.accounts[id].reach_estimate.get(**kwargs)

Use the Application only authentication
=======================================

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


Change the loads function used when decoding responses
======================================================

The responses sent by the Twitter API are commonly JSON data.
By default the data is loaded using the `peony.utils.loads` so that each JSON
Object is converted to a dict object which allows to access its items as you
would access its attribute.


Which means that::

    response.data

returns the same as::

    response['data']

To change this behavior, PeonyClient has a `loads` argument which is the
function used when loading the data. So if you don't want to use the syntax
above and want use the default Python's dicts, you can pass `json.loads` as
argument when you create the client.::

    from peony import PeonyClient
    import json

    client = PeonyClient(**creds, loads=json.loads)
    client.twitter_configuration  # this is a dict object
    client.twitter_configuration['photo_sizes']
    client.twitter_configuration.photo_sizes  # raises AttributeError

You can also use it to change how JSON data is decoded.::

    import peony

    def loads(*args, **kwargs):
        """ parse integers as strings """
        return peony.utils.loads(*args, parse_int=str, **kwargs)

    client = peony.PeonyClient(**creds, loads=loads)

## Handle errors for every request

By default `peony.exceptions.RateLimitExceeded` is handled by sleeping until
the rate limit resets and the requests are resent on ``TimeoutError``.
If you would handle these exceptions another way or want to handle other
exceptions differently you can use the ``error_handler`` argument of
PeonyClient.::

    import peony
    from peony import PeonyClient

    # client using application-only authentication
    backup_client = PeonyClient(**creds, auth=peony.oauth.OAuth2Headers)


    # This decorator permits the use of the `_error_handling` argument for
    # for your own function (see notes below code)
    @peony.handler_decorator
    def error_handler(request):
        """
            try to use backup_client during rate limits
            retry requests three times before giving up
        """

        # NOTE: client.api.statuses.home_timeline.get(_tries=5) should try the
        # request 5 times instead of 3
        async def decorated_request(tries=3, **kwargs):
            while True:
                try:
                    return await request(**kwargs)
                except peony.exceptions.RateLimitExceeded as e:
                    try:
                        return backup_client.request(**kwargs)
                    except:
                        print(e)
                        print("sleeping for %ds" % e.reset_in)
                        await asyncio.sleep(e.reset_in)
                except TimeoutError:
                    pass
                else:
                    tries -= 1
                    if not tries:
                        raise

        return decorated_request


    client = PeonyClient(**creds, error_handler=error_handler)

You can also choose to not use an error handler and disable the default one by
setting the ``error_handler`` argument to ``None``.
If you want to disable the global error handling for a specific request pass a
``_error_handling`` argument to this request with a value of ``False``.
