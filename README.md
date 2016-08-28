Peony
===

An asynchronous API client for Python

Summary
===

* [Installation](#installation)
* [Getting Started](#getting-started)
* [Usage](#usage)
  * [Authorizing your client](#authorizing-your-client)
  * [How to access the response data](#how-to-access-the-response-data)
    * [From a REST API endpoint](#from-a-rest-api-endpoint)
    * [From a Streaming API endpoint](#from-a-streaming-api-endpoint)
  * [Upload medias](#upload-medias)
  * [Iterators](#iterators)
    * [Cursor iterators](#cursor-iterators)
    * [Max_id iterators](#max-id-iterators)
    * [Since_id iterators](#since-id-iterators)
  * [Tasks](#tasks)
    * [The `task` decorator](#the-task-decorator)
  * [Event handlers](#event-handlers)
* [Advanced Usage](#advanced-usage)
  * [Accessing an API using a different api version](#accessing-an-api-using-a-different-api-version)
  * [Use the Application only authentication](#use-the-application-only-authentication)

# Installation

To install this module simply run:  

    pip install peony-twitter

# Getting started

You can easily create a client using the class `PeonyClient`.
Make sure to get your api keys and access tokens from
[Twitter's application management page][apps] and/or to
[authorize your application for your account](#authorizing-your-client)

*Note: the package name is peony and not peony-twitter*


```python
import asyncio

# Note: the package name is peony and not peony-twitter
from peony import PeonyClient

loop = asyncio.get_event_loop()

# create the client using your api keys
client = PeonyClient(consumer_key=YOUR_CONSUMER_KEY,
                     consumer_secret=YOUR_CONSUMER_SECRET,
                     access_token=YOUR_ACCESS_TOKEN,
                     access_token_secret=YOUR_ACCESS_TOKEN_SECRET)

# this is a coroutine
req = client.api.statuses.update.post(status="I'm using Peony!!")

# run the coroutine
loop.run_until_complete(req)
```


[apps]: <https://apps.twitter.com>


# Usage

You can easily access any Twitter API endpoint

```python
creds = dict(consumer_key=YOUR_CONSUMER_KEY,
             consumer_secret=YOUR_CONSUMER_SECRET,
             access_token=YOUR_ACCESS_TOKEN,
             access_token_secret=YOUR_ACCESS_TOKEN_SECRET)

client = PeonyClient(**creds)

# to access api.twitter.com/1.1/statuses/home_timeline.json
# using the GET method with the parameters count and since_id
async def home():
    return await client.api.statuses.home_timeline.get(count=200, since_id=0)

# to access userstream.twitter.com/1.1/statuses/filter.json
# using the POST method with the parameter track
async def track():
    async with client.stream.statuses.filter.post(track="uwu") as ressource:
        pass  # do something, see next chapter

# would GET subdomain.twitter.com/1.1/path.json if it were
# an API endpoint
async def path():
    return await client.subdomain.path.get()
```

see [Accessing an API using a different api version](#accessing-an-api-using-a-different-api-version)
to access APIs that do not use the version '1.1'

*Note*: Arguments with a leading underscore are arguments that are used to
change the behavior of peony for the request (e.g. `_headers` to add some
additional headers to the request).  
Arguments without a leading underscore are parameters of the request you send.

## Authorizing your client

You can use `peony.oauth_dance` to authorize your client

```python
>>> from peony.oauth_dance import oauth_dance
>>> tokens = oauth_dance(consumer_key, consumer_secret)
```

This should open a browser to get a pin to authorize your application.

## How to access the response data

### From a REST API endpoint

A call to a REST API endpoint should return a PeonyResponse object.


```python
async def home():
    req = client.api.statuses.home_timeline.get(count=200, since_id=0)

    # this is a PeonyResponse object
    response = await req

    # you can iterate over the response object
    for tweet in response:
        # you can access items as you would do in a dictionnary
        user_id = tweet['user']['id']

        # or as you would access an attribute
        username = tweet.user.screen_name

        print("@{username} ({id}): {text}".format(username=username,
                                                  id=user_id,
                                                  text=tweet.text))
```


### From a Streaming API endpoint

A call to a Streaming API endpoint should return a StreamContext object, that
yields a StreamResponse object.

```python
async def track():
    ctx = client.stream.statuses.filter.post(track="uwu")

    # ctx is an asynchronous context (StreamContext)
    async with ctx as stream:
        # stream is an asynchronous iterator (StreamResponse)
        async for tweet in stream:
            # you can then access items as you would do with a
            # PeonyResponse object
            user_id = tweet['user']['id']
            username = tweet.user.screen_name

            print("@{username} ({id}): {text}".format(username=username,
                                                      id=user_id,
                                                      text=tweet.text))
```

## Upload medias

You can easily upload a media with peony.

```python
import asyncio
from peony import PeonyClient

# creds being a dictionnary containing your api keys
client = PeonyClient(**creds)

async def upload_media(picture="picture.jpg"):
    client.api.statuses.update.post(status="Wow! Look at this picture!",
                                    _media=picture)

loop = asyncio.get_event_loop()
loop.run_until_complete(upload_media="picture.jpg")
```

You could also use PeonyClient.upload_media to upload a media without tweeting.
This should be useful if you want to schedule a tweet that sends a picture.

```python
import time

async def upload_media(picture):
    media = await client.upload_media(picture)

    # sleep until the next hour
    await asyncio.sleep(-time.time() % 3600)
    # upload the media using its media_id
    # that you got from the response above
    await client.api.statuses.update.post(status="Wow! Look at this picture!"
                                          media_ids=media.media_id)
```
*Note*: The upload_media method will, by default, convert your picture to the
format that gives the smallest size between JPEG and PNG. If you do not want to
use this behavior you can set the `auto_convert` argument to `False`
(or `_auto_convert` when using the `_media` argument in a request)

## Iterators

Sometimes you need to make several requests to the same API endpoint in order
to get all the data you want (e.g. getting more than 200 tweets of an user).  
Some iterators are included in Peony and usable through the peony.iterators
module that deals with the actual iteration, getting all the responses you need.

### Cursor iterators

This is an iterator for endpoints using the `cursor` parameter
(e.g. followers/ids.json). The first argument given to the iterator is the
coroutine function that will make the request.


```python
import peony.iterators
from peony import PeonyClient

# creds being a dictionnary containing your api keys
client = PeonyClient(**creds)

async def get_followers(user_id, **additional_params):
    followers_ids = peony.iterators.with_cursor(
        client.api.followers.ids.get,
        id=user_id,
        count=5000,
        **additional_params
    )

    followers = []
    async for data in followers_ids:
        followers.extend(data.ids)

    return followers
```

### Max_id iterators
An iterator for endpoints using the `max_id` parameter
(e.g. statuses/user_timeline.json)


```python
from peony import PeonyClient
import peony.iterators

client = PeonyClient(**creds)

async def get_tweets(user_id, n_tweets=1600, **additional_params):
      responses = peony.iterators.with_max_id(
          client.api.statuses.user_timeline.get,
          user_id=user,
          count=200,
          **additional_params
      )

      user_tweets = []

      async for tweets in responses:
          user_tweets.extend(tweets)

          if len(user_tweets) >= n_tweets:
              user_tweets = user_tweets[:n_tweets]
              break

      return user_tweets
```

### Since_id iterators
An iterator for endpoints using the `since_id` parameter
(e.g. statuses/home_timeline.json)


```python
import asyncio
import html

try:
    from . import peony, api, testdir
except SystemError:
    from __init__ import peony, testdir
    import api


client = peony.PeonyClient(**api.keys)

async def get_home(since_id=None, **params):
    responses = peony.iterators.with_since_id(
        client.api.statuses.home_timeline.get,
        count=200,
        **params
    )

    home = []
    async for tweets in responses:
        for tweet in reversed(tweets):
            text = html.unescape(tweet.text)
            print("@{user.screen_name}: {text}".format(user=tweet.user,
                                                       text=text))
            print("-"*10)

        await asyncio.sleep(180)

    return sorted(home, key=lambda tweet: tweet.id)
```

## Tasks

The main advantage of an asynchronous client is that it will be able to run
multiple tasks... asynchronously.  
Which is quite interesting here if you want to access several Streaming APIs,
or perform some requests periodically while using a Streaming API.


So I tried to make it easier to create such a program.

### Init tasks

By default the client makes 2 requests on initialization that are kept as
attributes of the client:
* account/verify_credentials.json (kept as self.user)
* help/twitter_configuration.json (kept as self.twitter_configuration)

If you need to have more informations during the initialization of a client you
should override the `init_tasks` method of your subclass. This will run all the
coroutines held by the list returned by the method at the same time during the
initialization (that's the point of an asynchronous client after all).

```python
import asyncio
from peony import PeonyClient
import peony.iterators

class Client(PeonyClient):

    def init_tasks(self):
        tasks = super().init_tasks()
        tasks += [
            self.get_settings(),
            self.get_likes()
        ]
        return tasks

    async def get_setting():
        self.settings = await self.api.account.settings.get()

    async def get_likes():
        self.likes = await self.api.favorites.list.get(count=200)
```

*Note*: The attributes user and twitter_configuration are created by the tasks
in PeonyClient.init_tasks() which are the respectively the responses from
/1.1/account/verify_credentials.json and /1.1/help/configuration.json.  
So you can access self.user.id in the class and this will give you the id of
the authenticated user.  

*Note*: The attribute twitter_configuration is used by the method upload_media
when it converts your picture

### The `task` decorator

First you will need to create a subclass of PeonyClient and add a `task`
decorator to the methods that you want to run.


```python
import asyncio
import time

from peony import PeonyClient, task

class AwesomePeonyClient(PeonyClient):
    @staticmethod
    async def wait_awesome_hour():
        """ wait until the next awesome hour """
        await asyncio.sleep(-time.time() % 3600)

    async def send_awesome_tweet(self, status="Peony is awesome!!"):
        """ send an awesome tweet """
        await self.api.statuses.update.post(status=status)

    @task
    async def awesome_loop(self):
        """ send an awesome tweet every hour """
        while True:
            await self.wait_awesome_hour()
            await self.send_awesome_tweet()

    @task
    async def awesome_user(self):
        """ The user using this program must be just as awesome, right? """
        user = await self.api.account.verify_credentials.get()

        print("This is an awesome user", user.screen_name)

    @task
    async def awesome_stream(self):
        """
            Tweets that contain awesome without a typo must be
            quite awesome too
        """
        async with self.stream.statuses.filter(track="awesome") as stream:
            async for tweet in stream:
                print("This is an awesome tweet", tweet.text)


def main():
    """ run all the tasks simultaneously """
    loop = asyncio.get_event_loop()

    # set your api keys here
    awesome_client = AwesomePeonyClient(
        consumer_key=your_consumer_key,
        consumer_secret=your_consumer_secret,
        access_token=your_access_token,
        access_token_secret=your_access_token_secret
    )

    asyncio.ensure_future(asyncio.wait(awesome_client.tasks))
    loop.run_forever()

    # if there was no stream:
    # loop.run_until_complete(asyncio.wait(awesome_client.tasks))


if __name__ == '__main__':
    main()
```

### Event handlers

Let's say that your awesome bot has become very popular, and so you'd like to
add some new features to it that would make use of the Streaming API. You could
use the `task` decorator but there is a better way to do it.  

*keeping the code from above*
```python

from peony import EventStream, event_handler, events

# adding permissions dirtily, you should probably try to load them in
# AwesomePeonyClient.__init__ instead
AwesomePeonyClient.permissions = {
    "admin": [42]
}

@AwesomePeonyClient.event_stream
class AwesomeUserStream(EventStream):

    @property
    def stream_request(self):
        # stream_request must return the request used to access the stream
        return self.userstream.user.get()

    @event_handler(*events.on_connect)
    def awesome_connection(self, data):
        print("Connected to stream!")

    @event_handler(*events.on_follow)
    def awesome_follow(self, data, *args):
        print("You have a new awesome follower @%s" % data.source.screen_name)

    # when adding a prefix argument to an event handler it adds a
    # command attribute to the function that you can use as a decorator
    # to create commands
    # it also adds a command argument to the event_handler
    @event_handler(*events.on_dm, prefix='/')
    async def awesome_dm_received(self, data, command):
        # Important: command.run is a coroutine
        msg = await command.run(self, data=data.direct_message)

        if msg:
            await self.api.direct_messages.new.post(
                user_id=data.direct_message.sender.id,
                text=msg
            )

    # Here a command is called when the dm contains:
    # "{prefix}{command_name}"
    # So this command is called when an user sends a dm which
    # contains "/awesome_reply"
    @on_awesome_dm_received.command
    def awesome_reply(self, data):
        return "I can send awesome dms too!"

    # user must have op permission to use this command
    @on_awesome_dm_received.command.restricted('op')
    async def awesome_tweet(self, data):
        awesome_status = " ".join(word for word in data.text.split()
                                  if word != "/awesome_tweet")
        await self.api.statuses.update.post(status=awesome_status)

        return "sent " + awesome_status

    # user must have admin or op permission to use this command
    @on_awesome_dm_received.command.restricted('admin', 'op')
    async def awesome_smiley(self, data):
        return "( ﾟ▽ﾟ)/awesome"

```


# Advanced Usage

## Accessing an API using a different api version

There actually two ways:
* create a client with an `api_version` argument
* provide the api version with the subdomain of the api when creating the path to the ressource

### Create a client with a custom api version

```python
# creds being a dict with your api_keys
# notice the use of the `suffix` argument to change the default
# extension ('.json')
client = PeonyClient(**creds, api_version='1', suffix='')

# params being the parameters of the request
req = client['ads-api'].accounts[id].reach_estimate.get(**params)
```

### Add a version when creating the request

```python
# notice the use of the `_suffix` argument to change the default
# extension for a request

# using a tuple as key
req = client['ads-api', '1'].accounts[id].reach_estimate.get(_suffix='',
                                                             **kwargs)

# using a dict as key
ads = client[dict(api='ads-api', version='1')]
req = ads.accounts[id].reach_estimate.get(**kwargs, _suffix='')
```

You can also add more arguments to the tuple or dictionnary

```python
# with a dictionnary
adsapi = dict(
    api='ads-api',
    version='1',
    suffix='',
    base_url='https://{api}.twitter.com/{version}'
)

req = client[adsapi].accounts[id].reach_estimate.get(**kwargs,)


# with a tuple
ads = client['ads-api', '1', '', 'https://{api}.twitter.com/{version}']
req = ads.accounts[id].reach_estimate.get(**kwargs)
```

## Use the Application only authentication

The application only authentication is restricted to some endpoints.
See [the Twitter documentation page][app_only_doc]

```python
import peony
from peony import PeonyClient

# NOTE: the bearer_token argument is not necessary
client = PeonyClient(consumer_key=YOUR_CONSUMER_KEY,
                     consumer_secret=YOUR_CONSUMER_SECRET,
                     bearer_token=YOUR_BEARER_TOKEN,
                     auth=peony.oauth.OAuth2Headers)
```

[app_only_doc]: <https://dev.twitter.com/oauth/application-only>
