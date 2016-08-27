# -*- coding: utf-8 -*-

import asyncio
from types import GeneratorType

import aiohttp

from . import general, utils
from .oauth import OAuth1Headers
from .stream import StreamContext
from .exceptions import MediaProcessingError
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

    >>> creds = {}
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

    def __init__(self, base_url, api, version, suffix, client):
        """
            build the base url of the api and create the _path and
            client attributes

        :base_url: str that should contain `{api}` and `{version}`
        :api: str
        :version: str
        :client: a class instance that would be called in _request
        """
        base_url = base_url.format(api=api, version=version).rstrip("/")

        self._suffix = suffix
        self._path = [base_url]
        self._client = client

    def url(self, suffix=None):
        """
            build the url using the _path attribute

        :suffix: str, to be appended to the url
        """
        return "/".join(self._path) + (suffix or self.suffix)

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
                self._path.extend(k)
            else:
                self._path.append(str(k))

            return self

    def __getattr__(self, k):
        """
            Call __getitem__ when trying to get an attribute from the
            instance

        if your path contains an actual attribute of the instance
        you should call __getitem__ instead

        >>> instance = APIPath()  # you would have to add more arguments
        >>> instance["client"]    # appends `client` to _path
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

        iterable = (list, set, tuple, GeneratorType)

        for key, value in items:
            # binary data
            if hasattr(value, 'read') or isinstance(value, bytes):
                params[key] = value
                # The params won't be used to make the signature
                skip_params = True

            # booleans conversion
            elif isinstance(value, bool):
                params[key] = value and "true" or "false"

            # integers conversion
            elif isinstance(value, int):
                params[key] = str(value)

            # iterables conversion
            elif isinstance(value, iterable):
                params[key] = ",".join(map(str, value))

            # skip params with value None
            elif value is None:
                pass

            # the rest is sent as is
            else:
                params[key] = value

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
        return "<%s %s>" % (self.__class__.__name__, self.url())


class APIPath(BaseAPIPath):

    def _request(self, method):
        """ Perform request on a REST API """

        async def request(_suffix=".json",
                          _media=None, _medias=[],
                          _auto_convert=True,
                          _formats=general.formats,
                          _max_sizes=None,
                          _medias_params={},
                          _skip_params=None,
                          _chunked_upload=False,
                          **kwargs):

            if _media and not _medias:
                _medias = [_media]

            media_ids = []

            for media in _medias:
                media_response = await self._client.upload_media(
                    media,
                    auto_convert=_auto_convert,
                    formats=_formats,
                    max_sizes=_max_sizes,
                    chunked=_chunked_upload,
                    **_medias_params
                )

                media_ids.append(media_response['media_id'])

            if not media_ids:
                media_ids = None

            kwargs, skip_params = self.sanitize_params(method,
                                                       media_ids=media_ids,
                                                       **kwargs)

            skip_params = _skip_params is None and skip_params or _skip_params

            return await self._client.request(method,
                                              url=self.url(_suffix),
                                              skip_params=skip_params,
                                              **kwargs)

        if self._client.error_handler:
            return self._client.error_handler(request)
        else:
            return request


class StreamingAPIPath(BaseAPIPath):

    def _request(self, method):
        """ Perform request on a Streaming API """

        def request(_suffix=".json", **kwargs):
            kwargs, skip_params = self.sanitize_params(method, **kwargs)

            return self._client.stream_request(method,
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
                 suffix='.json',
                 auth=OAuth1Headers,
                 loads=utils.loads,
                 loop=None,
                 error_handler=utils.requestdecorator,
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
        :suffix: :class:`str`
            suffix passed to APIPath and StreamingAPIPath
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
        self._suffix = suffix

        self._loads = loads
        self.error_handler = error_handler

        self.loop = loop or asyncio.get_event_loop()

        init_tasks = self.init_tasks
        if callable(init_tasks):
            init_tasks = init_tasks()

        self.loop.run_until_complete(asyncio.wait(init_tasks))

    def init_tasks(self):
        return [self.__get_twitter_configuration(), self.__get_user()]

    async def __get_twitter_configuration(self):
        api = self['api', general.twitter_api_version, ".json"]
        self.twitter_configuration = await api.help.configuration.get()

    async def __get_user(self):
        api = self['api', general.twitter_api_version, ".json"]
        self.user = await api.account.verify_credentials.get()

    def __getitem__(self, values):
        """
            Access the api you want

        This permits the use of any API you could know about

        For most api you only need to type
        >>> client[api]  # api is the api you want to access

        You can specify a custom api version using the syntax
        >>> client[api, version]  # version is the api version as a str

        For more complex requests
        >>> client[api, version, suffix, base_url]

        :returns: :class:`StreamingAPIPath` or
                  :class:`APIPath`
        """
        defaults = (None, self.api_version, self._suffix, self.base_url)
        keys = ['api', 'version', 'suffix', 'base_url']

        if isinstance(values, dict):
            # set values in the right order
            values = [values[key] for key in keys]
        elif isinstance(values, set):
            raise TypeError('Cannot use a set to access an api, '
                            'please use a dict, a tuple or a list instead')
        elif not isinstance(values, (tuple, list)):
            # make values an iterable
            values = values,

        if len(values) < len(keys):
            padding_size = len(keys) - len(values)

            # values is either a tuple or a list and padding is an
            # instance of the same class as values
            padding = values.__class__([None] * padding_size)
            values += padding

        kwargs = {key: value or default
                  for key, value, default in zip(keys, values, defaults)
                  if value or default is not None}

        kwargs.update(dict(client=self))

        # api must be in kwargs
        if 'api' in kwargs:
            # use StreamingAPIPath if subdomain is in self.streaming_apis
            if kwargs['api'] in self.streaming_apis:
                return StreamingAPIPath(**kwargs)
            else:
                return APIPath(**kwargs)
        else:
            msg = 'You must provide an api to use for your request'
            raise RuntimeError(msg)

    def __getattr__(self, api):
        """
            Access the api you want

        Same as calling client[api]

        :returns: :class:`StreamingAPIPath` or
                  :class:`APIPath`
        """
        return self[api]

    async def _chunked_upload(self, media,
                              path=None,
                              media_type=None,
                              media_category=None,
                              **params):
        media_size = utils.get_size(media)

        if media_type is None or media_category is None:
            media_type, media_category = utils.get_type(media, path)

        response = await self.upload.media.upload.post(
            command="INIT",
            total_bytes=media_size,
            media_type=media_type,
            media_category=media_category,
            **params
        )

        media_id = response['media_id']

        mb = 2**20
        chunks = utils.media_chunks(media, mb, media_size)

        for i, chunk in enumerate(chunks):
            await self.upload.media.upload.post(command="APPEND",
                                                media_id=media_id,
                                                media=chunk,
                                                segment_index=i,
                                                _json=None)

        status = await self.upload.media.upload.post(command="FINALIZE",
                                                     media_id=media_id)

        if 'processing_info' in status:
            while status['processing_info']['state'] != "succeeded":
                if 'status' not in status['processing_info']:
                    pass
                elif status['processing_info']['status'] == "failed":
                    error = status['processing_info'].get('error', {})

                    message = error.get('message',
                                        "No error message in the response")

                    raise MediaProcessingError(data=status,
                                               message=message,
                                               **params)

                delay = status['processing_info']['check_after_secs']
                await asyncio.sleep(delay)
                status = await self.upload.media.upload.get(
                    command="STATUS",
                    media_id=media_id,
                    **params
                )

        return response

    async def upload_media(self, f,
                           auto_convert=True,
                           formats=general.formats,
                           max_size=None,
                           chunked=False,
                           **params):
        image_metadata = utils.get_image_metadata(f)
        media_type, media_category, is_image, path = image_metadata

        if is_image and auto_convert:
            if not max_size:
                photo_sizes = self.twitter_configuration['photo_sizes']
                large_sizes = photo_sizes['large']
                max_size = large_sizes['h'], large_sizes['w']

            media = utils.optimize_media(path, max_size, formats)
        else:
            media = open(path, 'rb')

        size_limit = self.twitter_configuration['photo_size_limit']

        if utils.get_size(media) > size_limit or chunked:
            args = media, path, media_type, media_category
            response = await self._chunked_upload(*args, **params)
        else:
            response = await self.upload.media.upload.post(media=media,
                                                           **params)

        if not media.closed:
            media.close()

        return response

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
                if int(str(response.status)[0]) == 2:
                    if json or url.endswith(".json") and json is not None:
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
                else:  # throw exceptions if status is not 2xx
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

    @classmethod
    def event_stream(cls, event_stream):
        """ Decorator to attach an event stream to the class """
        cls._streams = getattr(cls, '_streams', EventStreams())

        cls._streams.append(event_stream)
        return event_stream

    def get_tasks(self):
        """
            Get tasks attached to the instance

        You should not need to use this method and call directly
        the tasks attribute of the instance
        """
        funcs = [getattr(self, key) for key in dir(self)]
        tasks = [func(self) for func in funcs if isinstance(func, task)]

        if isinstance(self._streams, EventStreams):
            tasks.extend(self._streams.get_tasks(self))

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
