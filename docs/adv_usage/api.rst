.. _adv_api:

================================================
 Accessing an API using a different API version
================================================

There actually two ways:

* create a client with an ``api_version`` argument
* provide the api version with the subdomain of the api when creating the path to the ressource

Create a client with a custom api version
-----------------------------------------

.. code-block:: python

    # creds being a dict with your api_keys
    # notice the use of the `suffix` argument to change the default
    # extension ('.json')
    client = PeonyClient(**creds, api_version='1', suffix='')

    # params being the parameters of the request
    req = client['ads-api'].accounts[id].reach_estimate.get(**params)


Add a version when creating the request
---------------------------------------

.. code-block:: python

    # notice the use of the `_suffix` argument to change the default
    # extension for a request

    # using a tuple as key
    req = client['ads-api', '1'].accounts[id].reach_estimate.get(_suffix='',
                                                                 **kwargs)

    # using a dict as key
    ads = client[dict(api='ads-api', version='1')]
    req = ads.accounts[id].reach_estimate.get(**kwargs, _suffix='')

You can also add more arguments to the tuple or dictionnary:

.. code-block:: python

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
