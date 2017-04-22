# -*- coding: utf-8 -*-

import peony
import peony.api
from peony.general import twitter_api_version, twitter_base_api_url

client = peony.BasePeonyClient("", "")
base_url = twitter_base_api_url.format(api='api', version=twitter_api_version)


def test_create_endpoint():
    client_endpoint = client.api.test.endpoint.url()
    api = peony.api.APIPath([base_url], '.json', client)
    assert client_endpoint == api.test.endpoint.url()
