# -*- coding: utf-8 -*-

twitter_base_api_url = "https://{api}.twitter.com/{version}"
twitter_api_version = "1.1"

request_methods = {"get", "post", "put", "delete", "patch", "option", "head"}
streaming_apis = {"stream", "userstream", "sitestream"}

rate_limit_notices = [
    b"Exceeded connection limit for user",
    b"Easy there, Turbo. Too many requests recently. Enhance your calm."
]

formats = [dict(format='PNG'),
           dict(format='JPEG', quality=90, optimize=True)]
