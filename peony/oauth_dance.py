# -*- coding: utf-8 -*-

import asyncio
import webbrowser

from . import oauth
from .client import BasePeonyClient


async def get_oauth_token(consumer_key, consumer_secret, callback_uri="oob"):
    """
    Get a temporary oauth token

    Parameters
    ----------
    consumer_key : str
        Your consumer key
    consumer_secret : str
        Your consumer secret
    callback_uri : str, optional
        Callback uri, defaults to 'oob'

    Returns
    -------
    dict
        Temporary tokens
    """

    async with BasePeonyClient(consumer_key=consumer_key,
                               consumer_secret=consumer_secret,
                               api_version="",
                               suffix="") as client:

        response = await client.api.oauth.request_token.post(
            _suffix="",
            oauth_callback=callback_uri
        )

        return parse_token(response)


async def get_oauth_verifier(oauth_token):
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
    url = "https://api.twitter.com/oauth/authorize?oauth_token=" + oauth_token

    try:
        browser = webbrowser.open(url)
        await asyncio.sleep(2)

        if not browser:
            raise RuntimeError
    except RuntimeError:
        print("could not open a browser\ngo here to enter your PIN: " + url)

    verifier = input("\nEnter your PIN: ")
    return verifier


async def get_access_token(consumer_key, consumer_secret,
                           oauth_token, oauth_token_secret,
                           oauth_verifier, **kwargs):
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

    async with BasePeonyClient(consumer_key=consumer_key,
                               consumer_secret=consumer_secret,
                               access_token=oauth_token,
                               access_token_secret=oauth_token_secret,
                               api_version="",
                               suffix="") as client:

        response = await client.api.oauth.access_token.get(
            _suffix="",
            oauth_verifier=oauth_verifier
        )

        return parse_token(response)


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

    oauth_verifier = await get_oauth_verifier(token['oauth_token'])

    token = await get_access_token(
        consumer_key,
        consumer_secret,
        oauth_verifier=oauth_verifier,
        **token
    )

    token = dict(
        consumer_key=consumer_key,
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
    loop : event loop
        asyncio event loop

    Returns
    -------
    dict
        Access tokens
    """
    loop = asyncio.get_event_loop() if loop is None else loop

    coro = async_oauth_dance(consumer_key, consumer_secret, oauth_callback)
    return loop.run_until_complete(coro)


async def async_oauth2_dance(consumer_key, consumer_secret):
    """
        oauth2 dance

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
    async with BasePeonyClient(consumer_key=consumer_key,
                               consumer_secret=consumer_secret,
                               auth=oauth.OAuth2Headers) as client:

        await client.headers.sign()
        return client.headers.token


def oauth2_dance(consumer_key, consumer_secret, loop=None):
    """
        oauth2 dance

    Parameters
    ----------
    consumer_key : str
        Your consumer key
    consumer_secret : str
        Your consumer secret
    loop : event loop, optional
        event loop to use

    Returns
    -------
    str
        Bearer token
    """
    loop = asyncio.get_event_loop() if loop is None else loop
    return loop.run_until_complete(async_oauth2_dance(consumer_key, consumer_secret))
