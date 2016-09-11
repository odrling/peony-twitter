========================================================
 Change the loads function used when decoding responses
========================================================

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
