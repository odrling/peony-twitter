# -*- coding: utf-8 -*-

from . import general, iterators


class BaseRequest:

    def __init__(self, api, method):
        self.api = api
        self.method = method

    def __call__(self, _suffix=".json", **kwargs):
        return (*self.api.sanitize_params(self.method, **kwargs),
                self.api.url(_suffix))


class Iterators:

    def __init__(self, api, method):
        self.api = api
        self.method = method

    def _get_iterator(self, iterator):
        def iterate(**kwargs):
            return iterator(getattr(self.api, self.method), **kwargs)
        return iterate

    def __getattr__(self, key):
        return self._get_iterator(getattr(iterators, key))


class Request(BaseRequest):

    def __init__(self, api, method):
        super().__init__(api, method)
        self.iterator = Iterators(api, method)

    async def __call__(self,
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
            media_response = await self.api._client.upload_media(
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

        kwargs, skip_params, url = super().__call__(media_ids=media_ids,
                                                    **kwargs)

        skip_params = _skip_params is None and skip_params or _skip_params

        kwargs.update(method=self.method,
                      url=url,
                      skip_params=skip_params)

        client_request = self.api._client.request

        if self.api._client.error_handler:
            client_request = self.api._client.error_handler(client_request)

        return await client_request(**kwargs)


class StreamingRequest(BaseRequest):

    def __call__(self, **kwargs):
        kwargs, skip_params, url = super().__call__(**kwargs)

        return self.api._client.stream_request(self.method,
                                               url=url,
                                               skip_params=skip_params,
                                               **kwargs)
