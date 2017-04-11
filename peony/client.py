# -*- coding: utf-8 -*-
"""
Peony Clients

:class:`BasePeonyClient` only handles requests while
:class:`PeonyClient` adds some methods that could help when using
the Twitter APIs, with a method to upload a media
"""

import asyncio
import io
import itertools
import pathlib
from concurrent.futures import ProcessPoolExecutor

import aiohttp

from . import exceptions, general, oauth, utils
from .api import APIPath, StreamingAPIPath
from .commands import EventStreams, task
from .oauth import OAuth1Headers
from .stream import StreamContext

try:
    from aiofiles import open
except ImportError:
    pass


class BasePeonyClient:
    """
        Access the Twitter API easily

    You can create tasks by decorating a function from a child
    class with :class:`peony.task`

    You also attach a :class:`EventStream` to a subclass using
    the :func:`event_stream` of the subclass

    After creating an instance of the child class you will be able
    to run all the tasks easily by executing :func:`get_tasks`

    Parameters
    ----------
    streaming_apis : iterable, optional
        Iterable containing the streaming APIs subdomains
    base_url : :obj:`str`, optional
        Format of the url for all the requests
    api_version : :obj:`str`, optional
        Default API version
    suffix : :obj:`str`, optional
        Default suffix of API endpoints
    loads : :obj:`function`, optional
        Function used to load JSON data
    error_handler : :obj:`function`, optional
        Requests decorator
    session : :obj:`asyncio.ClientSession`, optional
        Session to use to make requests
    proxy : str
        Proxy used with every request
    compression : :obj:`bool`, optional
        Activate response compression on every requests, defaults to True
    user_agent : :obj:`str`, optional
        Set a custom user agent header
    loop : event loop, optional
        An event loop, if not specified :func:`asyncio.get_event_loop`
        is called
    """

    def __init__(self, consumer_key, consumer_secret,
                 access_token=None,
                 access_token_secret=None,
                 bearer_token=None,
                 auth=None,
                 headers=None,
                 streaming_apis=None,
                 base_url=None,
                 api_version=None,
                 suffix='.json',
                 loads=utils.loads,
                 error_handler=utils.error_handler,
                 session=None,
                 proxy=None,
                 compression=True,
                 user_agent=None,
                 loop=None,
                 **kwargs):

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

        if auth is None:
            auth = OAuth1Headers

        if headers is None:
            headers = {}

        self.proxy = proxy

        self._suffix = suffix

        self._loads = loads
        self.error_handler = error_handler

        self.loop = asyncio.get_event_loop() if loop is None else loop

        self._session = session
        self._user_session = session is not None

        # all the possible args required by headers in :mod:`peony.oauth`
        kwargs = {
            'consumer_key': consumer_key,
            'consumer_secret': consumer_secret,
            'access_token': access_token,
            'access_token_secret': access_token_secret,
            'bearer_token': bearer_token,
            'compression': compression,
            'user_agent': user_agent,
            'headers': headers,
            'client': self
        }

        # get the args needed by the auth parameter on initialization
        args = utils.get_args(auth.__init__, skip=1)

        # keep only the arguments required by auth on init
        kwargs = {key: value for key, value in kwargs.items()
                  if key in args}

        self.headers = auth(**kwargs)

        self.__setup = {'event': asyncio.Event(),
                        'state': False}

        if not self.loop.is_running():
            self.loop.run_until_complete(self.setup())

    async def setup(self):
        """
            set up the client on the first request
        """
        if not self.__setup['state']:
            self.__setup['state'] = True

            if self._session is None:
                self._session = aiohttp.ClientSession()

            prepare_headers = self.headers.prepare_headers()
            if prepare_headers is not None:
                await prepare_headers

            self.__setup['event'].set()

            if callable(self.init_tasks):
                init_tasks = self.init_tasks()
            else:
                init_tasks = self.init_tasks

            if init_tasks is not None:
                await asyncio.wait(init_tasks)

        await self.__setup['event'].wait()

    def init_tasks(self):
        """ tasks executed on initialization """
        pass

    def __getitem__(self, values):
        """
            Access the api you want

        This permits the use of any API you could know about

        For most api you only need to type

        >>> self[api]  # api is the api you want to access

        You can specify a custom api version using the syntax

        >>> self[api, version]  # version is the api version as a str

        For more complex requests

        >>> self[api, version, suffix, base_url]

        Returns
        -------
        api.BaseAPIPath
            To access an API endpoint
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

    __getattr__ = __getitem__

    def __del__(self):
        # close the session only if it was created by peony
        if not self._user_session:
            self._session.close()

    async def request(self, method, url,
                      headers=None,
                      json=False,
                      session=None,
                      **kwargs):
        """
            Make requests to the REST API

        Parameters
        ----------
        method : str
            Method to be used by the request
        url : str
            URL of the ressource
        headers : peony.oauth.PeonyHeaders
            Custom headers (doesn't overwrite `Authorization` headers)
        session : :obj:`aiohttp.ClientSession`, optional
            Client session used to make the request
        json : bool
            Force json decoding

        Returns
        -------
        utils.PeonyResponse
            Response to the request
        """
        await self.setup()

        # prepare request arguments, particularly the headers
        req_kwargs = self.headers.prepare_request(
            method=method,
            url=url,
            headers=headers,
            **kwargs
        )

        if 'proxy' not in req_kwargs:
            req_kwargs['proxy'] = self.proxy

        session = session if (session is not None) else self._session

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
            else:  # throw exception if status is not 2xx
                await exceptions.throw(response)

    def stream_request(self, method, url, headers=None, _session=None,
                       *args, **kwargs):
        """
            Make requests to the Streaming API

        Parameters
        ----------
        method : str
            Method to be used by the request
        url : str
            URL of the ressource
        headers : dict
            Custom headers (doesn't overwrite `Authorization` headers)
        _session : :obj:`aiohttp.ClientSession`, optional
            The session to use for this specific request, the session
            given as argument of :meth:`__init__` is used by default

        Returns
        -------
        stream.StreamContext
            Stream context for the request
        """
        return StreamContext(
            method, url, self,
            *args,
            headers=headers,
            session=_session,
            **kwargs
        )

    @classmethod
    def event_stream(cls, event_stream):
        """ Decorator to attach an event stream to the class """
        if getattr(cls, '_streams', None) is None:
            cls._streams = EventStreams()

        cls._streams.append(event_stream)
        return event_stream

    def get_tasks(self):
        """
            Get the tasks attached to the instance

        Returns
        -------
        list
            List of tasks (:class:`asyncio.Task`)
        """
        funcs = [getattr(self, key) for key in dir(self)]
        tasks = [self.loop.create_task(func(self))
                 for func in funcs if isinstance(func, task)]

        if isinstance(self._streams, EventStreams):
            tasks.extend(self._streams.get_tasks(self))

        return tasks

    async def run_tasks(self):
        """ Run the tasks attached to the instance """
        await self.setup()
        await asyncio.wait(self.get_tasks())

    def run(self):
        """ Run the tasks attached to the instance """
        self.loop.create_task(self.run_tasks())
        try:
            self.loop.run_forever()
        except KeyboardInterrupt:
            pending = asyncio.Task.all_tasks(loop=self.loop)
            gathered = asyncio.gather(*pending, loop=self.loop)
            try:
                gathered.cancel()
                self.loop.run_until_complete(gathered)

                # we want to retrieve any exceptions to make sure that
                # they don't nag us about it being un-retrieved.
                gathered.exception()
            except:
                pass
        finally:
            self.loop.close()


class PeonyClient(BasePeonyClient):
    """
        A client with some useful methods for most usages
    """

    def __init__(self, *args, executor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.executor = ProcessPoolExecutor() if executor is None else executor

    def init_tasks(self):
        tasks = [self.__get_twitter_configuration()]
        if isinstance(self.headers, oauth.OAuth1Headers):
            tasks.append(self.__get_user())
        return tasks

    async def __get_twitter_configuration(self):
        """
        create a ``twitter_configuration`` attribute with the response
        of the endpoint
        https://api.twitter.com/1.1/help/configuration.json
        """
        api = self['api', general.twitter_api_version,
                   ".json", general.twitter_base_api_url]

        req = api.help.configuration.get()
        self.twitter_configuration = await req

    async def __get_user(self):
        """
        create a ``user`` attribute with the response of the endpoint
        https://api.twitter.com/1.1/account/verify_credentials.json
        """
        api = self['api', general.twitter_api_version,
                   ".json", general.twitter_base_api_url]

        req = api.account.verify_credentials.get()
        self.user = await req

    async def _chunked_upload(self, media,
                              path=None,
                              media_type=None,
                              media_category=None,
                              chunk_size=2**20,
                              **params):
        """
            upload media in chunks

        Parameters
        ----------
        media : file object
            a file object of the media
        path : :obj:`str`, optional
            filename of the media
        media_type : :obj:`str`, optional
            mime type of the media
        media_category : :obj:`str`, optional
            twitter media category
        chunk_size : :obj:`int`, optional
            size of a chunk in bytes
        params : :obj:`dict`, optional
            additional parameters of the request

        Returns
        -------
        utils.PeonyResponse
            Response of the request
        """
        media_size = await utils.get_size(media)

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

        for i in itertools.count():
            chunk = await utils.execute(media.read(chunk_size))
            if not chunk:
                break

            await self.upload.media.upload.post(command="APPEND",
                                                media_id=media_id,
                                                media=chunk,
                                                segment_index=i,
                                                _json=None)

        status = await self.upload.media.upload.post(command="FINALIZE",
                                                     media_id=media_id)

        if 'processing_info' in status:
            while status['processing_info']['state'] != "succeeded":
                if status['processing_info'].get('state', "") == "failed":
                    error = status['processing_info'].get('error', {})

                    message = error.get('message', str(status))

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
                           size_limit=None,
                           **params):
        """
            upload a media on twitter

        Parameters
        ----------
        file_ : :obj:`str` or :class:`pathlib.Path` or file
            Path to the file or file object
        auto_convert : :obj:`bool`, optional
            If set to True the media will be optimized by calling
            :func:`utils.optimize_media`
        formats : :obj:`list`, optional
            A list of all the formats to try to optimize the media
        max_size : :obj:`tuple`, optional
            Max size of the picture in the (width, height) format
        chunked : :obj:`bool`, optional
            If True, force the use of the chunked upload for the media
        size_limit : :obj:`int`, optional
            If set, the media will be sent using a multipart upload if
            its size is over ``sizelimit`` bytes

        Returns
        -------
        utils.PeonyResponse
            response of the request
        """
        formats = formats or general.formats

        image_metadata = await utils.get_image_metadata(file_)
        media_type, media_category, is_image, file_ = image_metadata

        if hasattr(file_, 'read'):
            media = file_
        else:
            media = await utils.execute(open(str(file_), 'rb'))

        if is_image and auto_convert:
            if not max_size:
                photo_sizes = self.twitter_configuration['photo_sizes']
                large_sizes = photo_sizes['large']
                max_size = large_sizes['w'], large_sizes['h']

            data = io.BytesIO(await utils.execute(media.read()))

            media = await self.loop.run_in_executor(
                self.executor, utils.optimize_media, data, max_size, formats
            )

        if not isinstance(self.twitter_configuration, APIPath) or size_limit:
            if size_limit is None:
                size_limit = self.twitter_configuration['photo_size_limit']
            size_test = await utils.get_size(media) > size_limit
        else:
            size_test = False

        if size_test or chunked:
            args = media, file_, media_type, media_category
            response = await self._chunked_upload(*args, **params)
        else:
            params['media'] = media
            response = await self.upload.media.upload.post(**params)

        if not hasattr(file_, 'read') and not media.closed:
            media.close()

        return response
