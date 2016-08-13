
import asyncio
import json

import aiohttp

from . import general, utils
from .oauth import OAuth1Headers
from .stream import StreamContext
from .exceptions import PeonyException
from .commands import EventStreams, task


class BaseAPIPath:
    """
        The syntactic sugar factory

    Everytime you get an attribute or an item from an instance of this
    class this will be appended to its _path variable (that you should
    not call) until you call a request method (like get or post)

    It makes it easy to call any endpoint of the api

    /!\ You must create a child class of BaseAPIPath to perform
    requests (you have to overload the _request method)

    The client given as an argument during the creation of the
    BaseAPIPath instance can be accessed as the "client" attribute of
    the instance.

    >>> api = BaseAPIPath("http://{api}.twitter.com/{version}",
    ...                   api="api", version="1.1",
    ...                   client=PeonyClient(**creds))
    >>>
    >>> # path to /account/verify_credentials.json
    >>> path = api.account.verify_credentials
    >>>
    >>> # should call /account/verify_credentials.json
    >>> path.get() # or api.account.verify_credentials.get()
    >>>
    """

    def __init__(self, base_url, api, version, client):
        """
            build the base url of the api and create the _path and
            client attributes

        :base_url: str that should contain `{api}` and `{version}`
        :api: str
        :version: str
        :client: a class instance that would be called in _request
        """
        base_url = base_url.format(api=api, version=version).rstrip("/")

        self._path = [base_url]
        self.client = client

    def url(self, suffix=".json"):
        """
            build the url using the _path attribute

        :suffix: str, to be appended to the url
        """
        return "/".join(self._path) + suffix

    def __getitem__(self, k):
        """
            Where the magic happens

        if the key is a request method (eg. get) call the _request
        attribute with the method as argument

        otherwise append the key to the _path attribute
        """
        if k.lower() in general.request_methods:
            return self._request(k)
        else:
            if isinstance(k, (tuple, list)):
                k = map(str, k)
                path.extend(k)
            else:
                self._path.append(str(k))

            return self

    def __getattr__(self, k):
        """
            Call __getitem__ when trying to get an attribute from the
            instance

        if your path contains an actual attribute of the instance
        you should call __getitem__ instead

        >>> instance["client"]  # appends `client` to _path
        """
        return self[k]

    @staticmethod
    def sanitize_params(method, **kwargs):
        """
            Request params can be extracted from the **kwargs

        Arguments starting with `_` will be stripped from it, so they
        can be used as an argument for the request
        (eg. "_headers" → "headers" in the kwargs returned by this
        function while "headers" would be inserted in the params)
        """
        # items which does not have a key starting with `_`
        items = [(key, value) for key, value in kwargs.items()
                 if not key.startswith("_")]
        params, skip_params = {}, False

        for key, value in items:
            if hasattr(value, 'read'):
                params[key] = value
                skip_params = True
            elif isinstance(value, bool):           # booleans conversion
                params[key] = value and "true" or "false"
            elif isinstance(value, int):          # integers conversion
                params[key] = str(value)
            elif isinstance(value, (list, set)):  # lists conversion
                params[key] = ",".join(value)
            elif isinstance(value, str):          # append strings
                params[key] = value

            # other types are ignored

        # dict with other items (+ strip "_" from keys)
        kwargs = {key[1:]: value for key, value in kwargs.items()
                  if key.startswith("_")}

        if method.lower() == "post":
            kwargs['data'] = params  # post requests use the data argument
        else:
            kwargs['params'] = params

        return kwargs, skip_params

    def _request(self, method):
        """ method to be overloaded """
        pass

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, self._url())


class APIPath(BaseAPIPath):

    def _request(self, method):
        """ Perform request on a REST API """

        async def request(_suffix=".json", **kwargs):
            kwargs, skip_params = self.sanitize_params(method, **kwargs)

            return await self.client.request(method,
                                             url=self.url(_suffix),
                                             skip_params=skip_params,
                                             **kwargs)

        return request


class StreamingAPIPath(BaseAPIPath):

    def _request(self, method):
        """ Perform request on a Streaming API """

        def request(_suffix=".json", **kwargs):
            kwargs, skip_params = self.sanitize_params(method, **kwargs)

            return self.client.stream_request(method,
                                              url=self.url(_suffix),
                                              skip_params=skip_params,
                                              **kwargs)

        return request


class BasePeonyClient:
    """
        Attributes/items become a :class:`APIPath` or
        :class:`StreamingAPIPath` automatically

    This class only handles the requests and makes accessing twitter's
    APIs easy.
    (see BasePeonyClient.__getitem__ and BasePeonyClient.__getattr__)
    """

    def __init__(self, consumer_key, consumer_secret,
                 access_token=None,
                 access_token_secret=None,
                 headers={},
                 streaming_apis=general.streaming_apis,
                 base_url=general.twitter_base_api_url,
                 api_version=general.twitter_api_version,
                 auth=OAuth1Headers,
                 loads=utils.loads,
                 loop=None,
                 **kwargs):
        """
            Set main attributes

        :consumer_key: :class:`str`
            consumer key of your application
        :consumer_secret: :class:`str`
            consumer secret of your application
        :access_token: :class:`str`
            access token of the user
        :access_token_secret: :class:`str`
            access token secret of the user
        :headers: :class:`dict`
            custom headers (does not override `Authorization` headers)
        :streaming_apis: :class:`list`,
                         :class:`tuple` or
                         :class:`set`
            contains the streaming api subdomains
        :base_url: :class:`str`
            base_url passed to APIPath and StreamingAPIPath
        :api_version: :class:`str`
            version passed to APIPath and StreamingAPIPath
        :auth: dynamic headers that generate the `Authorization`
               headers for each request (needed for OAuth1)
        :loads: custom json.loads function override if you don't want
                to use utils.JSONObject for responses
        :loop: asyncio loop
        """

        self.headers = auth(
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            access_token=access_token,
            access_token_secret=access_token_secret,
            **kwargs
        )
        self.headers.update(headers)

        self.streaming_apis = streaming_apis

        self.base_url = base_url
        self.api_version = api_version

        self._loads = loads

        self.loop = loop or asyncio.get_event_loop()

    def __getitem__(self, key):
        """
            Access the api you want

        This permits the use of any API you could know about

        For most api you only need to type
        >>> client[api]  # api is the api you want to access

        You can specify a custom api version using the syntax
        >>> client[api, version]  # version is the api version as a str

        :returns: :class:`StreamingAPIPath` or
                  :class:`APIPath`
        """
        if isinstance(key, tuple):
            if len(key) == 2:
                api, version = key
            else:
                msg = "tuple keys must have a length of 2. got " + str(key)
                raise ValueError(msg)
        else:
            api, version = key, self.api_version

        kwargs = dict(base_url=self.base_url, api=api,
                      version=version, client=self)

        # use StreamingAPIPath if subdomain is in self.streaming_apis
        if api in self.streaming_apis:
            return StreamingAPIPath(**kwargs)
        else:
            return APIPath(**kwargs)

    def __getattr__(self, api):
        """
            Access the api you want

        Same as calling client[api]

        :returns: :class:`StreamingAPIPath` or
                  :class:`APIPath`
        """
        return self[api]

    async def request(self, method, url,
                      headers={},
                      json=False,
                      **kwargs):
        """
            Make request to the REST API

        :method: str, method to be used by the request
        :url: str, url of the ressource
        :headers: dict, custom headers (doesn't overwrite `Authorization`
                  headers)
        :json: bool, force json decoding
        """

        # prepare request arguments, particularly the headers
        req_kwargs = self.headers.prepare_request(
            method=method,
            url=url,
            headers=headers,
            **kwargs
        )

        async with aiohttp.ClientSession() as session:

            # make the request
            async with session.request(**req_kwargs) as response:
                if response.status == 200:
                    if json or url.endswith(".json"):
                        # decode as json
                        content = await response.json(loads=self._loads)
                    else:
                        # decode as text
                        content = await response.text()

                    return utils.PeonyResponse(
                        response=content,
                        headers=response.headers,
                        url=response.url,
                        request=req_kwargs
                    )
                else:  # throw exceptions if status is not 200 OK
                    raise await utils.throw(response)

    def stream_request(self, method, url, headers={}, *args, **kwargs):
        """
            Make requests to the Streaming API

        :method: str, method to be used by the request
        :url: str, url of the ressource
        :headers: dict, custom headers (doesn't overwrite `Authorization`
                  headers)
        """
        return StreamContext(
            *args,
            method=method,
            url=url,
            headers=headers,
            _headers=self.headers,
            **kwargs
        )


class PeonyClient(BasePeonyClient):
    """
        A client with an easy handling of tasks

    You can create tasks by decorating a function from a child
    class with :class:`commands.task`

    You also attach a :class:`EventStream` to a child class using
    PeonyClientChild.event_stream

    After creating an instance of the child class you will be able
    to run all the tasks easily by accessing the tasks attribute

    >>> loop = asyncio.get_event_loop()
    >>> client = PeonyClientChild()
    >>> loop.run_until_complete(asyncio.wait(client.tasks))
    """

    def __init__(self, *args, **kwargs):
        """ Setup streams and create tasks attribute """
        super().__init__(*args, **kwargs)

        if isinstance(self.streams, EventStreams):
            self.streams.setup(client=self)

        self.tasks = self.get_tasks()

    @classmethod
    def event_stream(cls, event_stream):
        """ Decorator to attach an event stream to the class """
        if not hasattr(cls, "streams"):
            cls.streams = EventStreams()

        cls.streams.append(event_stream)
        return event_stream

    def get_tasks(self):
        """
            Get tasks attached to the instance

        You should not need to use this method and call directly
        the tasks attribute of the instance
        """
        funcs = [getattr(self, key) for key in dir(self)]
        tasks = [func(self) for func in funcs if isinstance(func, task)]

        if isinstance(self.streams, EventStreams):
            tasks.extend(self.streams.tasks)

        return tasks

    def get_task(self):
        """ Get the only task of the instance """
        tasks = self.get_tasks()

        if len(tasks) == 1:
            return tasks[0]

        # raise an exception if there are more than one task
        elif self.tasks:
            raise RuntimeError("more than one task in %s" % self)

        # raise an exception if there are no tasks
        else:
            raise RuntimeError("no tasks in %s" % self)
