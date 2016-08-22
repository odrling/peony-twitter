# -*- coding: utf-8 -*-

import asyncio
import time
import webbrowser

from .client import PeonyClient


async def get_oauth_token(consumer_key, consumer_secret, callback_uri="oob"):
    """ get a temporary oauth token """

    client = PeonyClient(consumer_key=consumer_key,
                         consumer_secret=consumer_secret,
                         callback_uri=callback_uri,
                         api_version="")

    response = await client.api.oauth.request_token.post(_suffix="")

    return parse_token(response)


def get_oauth_verifier(oauth_token):
    """
        open authorize page in a browser,
        print the url if it didn't work

        returns the PIN entered by the user
    """
    url = "https://api.twitter.com/oauth/authorize?oauth_token="
    url += oauth_token

    try:
        wb = webbrowser.open(url)
        time.sleep(2)

        if not wb:
            raise Exception
    except:
        print("could not open a browser\ngo here to enter your PIN: " + url)

    return input("\nEnter your PIN: ")


async def get_access_token(consumer_key, consumer_secret,
                           oauth_token, oauth_token_secret,
                           oauth_verifier):
    """ get the access token of the user """

    client = PeonyClient(consumer_key=consumer_key,
                         consumer_secret=consumer_secret,
                         access_token=oauth_token,
                         access_token_secret=oauth_token_secret,
                         api_version="")

    response = await client.api.oauth.access_token.get(
        _suffix="",
        oauth_verifier=oauth_verifier
    )

    access_token = parse_token(response)
    return access_token


async def async_oauth_dance(consumer_key, consumer_secret, callback_uri="oob"):
    """ oauth dance to get the user's access token """

    token = await get_oauth_token(consumer_key, consumer_secret, callback_uri)

    oauth_verifier = get_oauth_verifier(token['oauth_token'])

    token = await get_access_token(
        consumer_key,
        consumer_secret,
        oauth_verifier=oauth_verifier,
        **token
    )

    token = dict(
        consumer_key=consumer_secret,
        consumer_secret=consumer_secret,
        access_token=token['oauth_token'],
        access_token_secret=token['oauth_token_secret']
    )

    return token


def parse_token(response):
    """ parse the responses containing the tokens """
    items = response.split("&")
    items = [item.split("=") for item in items]

    return {key: value for key, value in items}


def oauth_dance(consumer_key, consumer_secret,
                oauth_callback="oob", loop=None):
    """
        oauth dance to get the user's access token

    calls async_oauth_dance, create event loop of not given
    """
    loop = loop or asyncio.get_event_loop()

    coro = async_oauth_dance(consumer_key, consumer_secret, oauth_callback)
    return loop.run_until_complete(coro)
