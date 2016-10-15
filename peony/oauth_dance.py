# -*- coding: utf-8 -*-

import asyncio
import time
import webbrowser

from . import oauth
from .client import BasePeonyClient, PeonyClient

async def get_oauth_token(consumer_key, consumer_secret, callback_uri="oob"):
    """
    Get a temporary oauth token

    Parameters
    ----------
    consumer_key : str
        Your consumer key
    consumer_secret : str
        Your consumer secret
    callback_uri : :obj:`str`, optional
        Callback uri, defaults to 'oob'

    Returns
    -------
    dict
        Temporary tokens
    """

    client = BasePeonyClient(consumer_key=consumer_key,
                             consumer_secret=consumer_secret,
                             api_version="",
                             suffix="")

    response = await client.api.oauth.request_token.post(
        _suffix="",
        oauth_callback=callback_uri
    )

    return parse_token(response)


def get_oauth_verifier(oauth_token):
    """
    Open authorize page in a browser,
    print the url if it didn't work

    Arguments
    ---------
    oauth_token : str
        The oauth token received in :func:`get_oauth_token`

    Returns
    -------
    str
        The PIN entered by the user
    """
    url = "https://api.twitter.com/oauth/authorize?oauth_token="
    url += oauth_token

    try:
        browser = webbrowser.open(url)
        time.sleep(2)

        if not browser:
            raise RuntimeError
    except RuntimeError:
        print("could not open a browser\ngo here to enter your PIN: " + url)

    return input("\nEnter your PIN: ")


async def get_access_token(consumer_key, consumer_secret,
                           oauth_token, oauth_token_secret,
                           oauth_verifier,
                           **kwargs):
    """
        get the access token of the user

    Parameters
    ----------
    consumer_key : str
        Your consumer key
    consumer_secret : str
        Your consumer secret
    oauth_token : str
        OAuth token from :func:`get_oauth_token`
    oauth_token_secret : str
        OAuth token secret from :func:`get_oauth_token`
    oauth_verifier : str
        OAuth verifier from :func:`get_oauth_verifier`

    Returns
    -------
    dict
        Access tokens
    """

    client = BasePeonyClient(consumer_key=consumer_key,
                             consumer_secret=consumer_secret,
                             access_token=oauth_token,
                             access_token_secret=oauth_token_secret,
                             api_version="",
                             suffix="")

    response = await client.api.oauth.access_token.get(
        _suffix="",
        oauth_verifier=oauth_verifier
    )

    access_token = parse_token(response)
    return access_token


async def async_oauth_dance(consumer_key, consumer_secret, callback_uri="oob"):
    """
        OAuth dance to get the user's access token

    Parameters
    ----------
    consumer_key : str
        Your consumer key
    consumer_secret : str
        Your consumer secret
    callback_uri : str
        Callback uri, defaults to 'oob'

    Returns
    -------
    dict
        Access tokens
    """

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
    """
    parse the responses containing the tokens

    Parameters
    ----------
    response : str
        The response containing the tokens

    Returns
    -------
    dict
        The parsed tokens
    """
    items = response.split("&")
    items = [item.split("=") for item in items]

    return {key: value for key, value in items}


def oauth_dance(consumer_key, consumer_secret,
                oauth_callback="oob", loop=None):
    """
        OAuth dance to get the user's access token

    It calls async_oauth_dance and create event loop of not given

    Parameters
    ----------
    consumer_key : str
        Your consumer key
    consumer_secret : str
        Your consumer secret
    oauth_callback : str
        Callback uri, defaults to 'oob'
    loop
        asyncio event loop

    Returns
    -------
    dict
        Access tokens
    """
    loop = loop or asyncio.get_event_loop()

    coro = async_oauth_dance(consumer_key, consumer_secret, oauth_callback)
    return loop.run_until_complete(coro)


def oauth2_dance(consumer_key, consumer_secret):
    """
        oauth2 dance actually dealt with on creation of
        :class:`peony.PeonyClient`

    Parameters
    ----------
    consumer_key : str
        Your consumer key
    consumer_secret : str
        Your consumer secret

    Returns
    -------
    str
        Bearer token
    """
    client = PeonyClient(consumer_key=consumer_key,
                         consumer_secret=consumer_secret,
                         auth=oauth.OAuth2Headers)
    return client.headers['Authorization'][len("Bearer "):]
