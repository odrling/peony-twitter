# -*- coding: utf-8 -*-
"""
Peony Clients

:class:`BasePeonyClient` only handles requests while
:class:`PeonyClient` adds some methods that could help when using
the Twitter APIs, with a method to upload a media
"""

import asyncio
from types import GeneratorType

import aiohttp

from . import exceptions, general, oauth, requests, utils
from .api import APIPath, StreamingAPIPath
from .commands import EventStreams, task
from .stream import StreamContext


class BasePeonyClient(oauth.Client):
    """
        Attributes/items become a :class:`APIPath` or
        :class:`StreamingAPIPath` automatically

    This class only handles the requests and makes accessing Twitter's
    APIs easy.
    """

    def __init__(self, *args,
                 streaming_apis=None,
                 base_url=None,
                 api_version=None,
                 suffix='.json',
                 loads=utils.loads,
                 error_handler=utils.error_handler,
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
        :bearer_token: :class: `str`
            bearer token of the client
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
        :error_handler: A decorator to use on a request to handle errors
        """

        if streaming_apis is None:
            self.streaming_apis = general.streaming_apis
        else:
            self.streaming_apis = streaming_apis

        if base_url is None:
            self.base_url = general.twitter_base_api_url
        else:
            self.base_url = base_url

        if api_version is None:
            self.api_version = general.twitter_api_version
        else:
            self.api_version = api_version

        self._suffix = suffix

        self._loads = loads
        self.error_handler = error_handler

        super().__init__(*args, **kwargs)

        if callable(self.init_tasks):
            init_tasks = self.init_tasks()
        else:
            init_tasks = self.init_tasks

        if init_tasks is not None:
            # loop attribute was created in oauth.Client.__init__
            self.loop.run_until_complete(asyncio.wait(init_tasks))

    def init_tasks(self):
        pass

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
        elif isinstance(values, str):
            values = [values, *defaults[1:]]
        elif values:
            if len(values) < len(keys):
                padding = (None,) * (len(keys) - len(values))
                values += padding

            values = [default if value is None else value
                      for value, default in zip(values, defaults)
                      if (value, default) != (None, None)]

        api, version, suffix, base_url = values

        base_url = base_url.format(api=api, version=version).rstrip('/')

        # use StreamingAPIPath if subdomain is in self.streaming_apis
        if api in self.streaming_apis:
            return StreamingAPIPath([base_url], suffix=suffix, client=self)
        else:
            return APIPath([base_url], suffix=suffix, client=self)

    def __getattr__(self, api):
        """
            Access the api you want

        Same as calling client[api]

        :returns: :class:`StreamingAPIPath` or
                  :class:`APIPath`
        """
        return self[api]

    async def request(self, method, url,
                      headers=None,
                      json=False,
                      **kwargs):
        """
            Make requests to the REST API

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
                if response.status // 100 == 2:
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
                    await exceptions.throw(response)

    def stream_request(self, method, url, headers=None, *args, **kwargs):
        """
            Make requests to the Streaming API

        :method: str, method to be used by the request
        :url: str, url of the ressource
        :headers: dict, custom headers (doesn't overwrite `Authorization`
                  headers)
        """
        return StreamContext(
            method, url,
            *args,
            headers=headers,
            _headers=self.headers,
            _error_handler=self.error_handler,
            **kwargs
        )


class PeonyClient(BasePeonyClient):
    """
        A client with an easy handling of tasks

    You can create tasks by decorating a function from a child
    class with :class:`peony.task`

    You also attach a :class:`EventStream` to a subclass using
    the :func:`event_stream` of the subclass

    After creating an instance of the child class you will be able
    to run all the tasks easily by executing :func:`get_tasks`
    """

    def init_tasks(self):
        tasks = [self.__get_twitter_configuration()]
        if isinstance(self.headers, oauth.OAuth1Headers):
            tasks.append(self.__get_user())
        return tasks

    async def __get_twitter_configuration(self):
        api = self['api', general.twitter_api_version, ".json"]
        self.twitter_configuration = await api.help.configuration.get()

    async def __get_user(self):
        api = self['api', general.twitter_api_version, ".json"]
        self.user = await api.account.verify_credentials.get()

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

        size_limit = 2**20
        chunks = utils.media_chunks(media, size_limit, media_size)

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

                    raise exceptions.MediaProcessingError(data=status,
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

    async def upload_media(self, file_,
                           auto_convert=False,
                           formats=None,
                           max_size=None,
                           chunked=False,
                           **params):
        formats = formats or general.formats

        image_metadata = utils.get_image_metadata(file_)
        media_type, media_category, is_image, file_ = image_metadata

        if is_image and auto_convert:
            if not max_size:
                photo_sizes = self.twitter_configuration['photo_sizes']
                large_sizes = photo_sizes['large']
                max_size = large_sizes['h'], large_sizes['w']

            media = utils.optimize_media(file_, max_size, formats)
        else:
            media = open(file_, 'rb')

        size_limit = self.twitter_configuration['photo_size_limit']

        if utils.get_size(media) > size_limit or chunked:
            args = media, file_, media_type, media_category
            response = await self._chunked_upload(*args, **params)
        else:
            response = await self.upload.media.upload.post(media=media,
                                                           **params)

        if not media.closed:
            media.close()

        return response

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
