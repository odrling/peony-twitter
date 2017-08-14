=========
 Streams
=========

If you need to access the Streaming API, the recommended way is to use an
:class:`~peony.commands.event_handlers.EventStream`. This can help to divide
the code in a program involving a stream into the methods of a subclass of
:class:`~peony.commands.event_handlers.EventStream`. These methods are
defined by their ``@decorator`` which must be an
:class:`~peony.commands.event_handlers.EventHandler`.


.. code-block:: python

    from peony import EventStream, PeonyClient, event_handler, events
    # all the event handlers are included in peony.events

    class Client(PeonyClient):
        pass

    # every class inheriting from `PeonyClient` or `BasePeonyClient` has
    # an event_stream function that can be used on an `EventStream`
    @Client.event_stream
    class UserStream(EventStream):

        def stream_request(self):
            """
                The stream_request method returns the request
                that will be used by the stream
            """
            return self.userstream.user.get()

        # the on_connect event is triggered on connection to an user stream
        # https://dev.twitter.com/streaming/overview/messages-types#friends-lists-friends
        @events.on_connect.handler
        def connection(self, data):
            print("Connected to stream!")

        # the on_tweet event is triggered when a tweet seems to be sent on
        # the stream, by default retweets are included
        @events.on_tweet.handler
        def tweet(self, data):
            print(data.text)

        # the on_retweet event is triggered when a retweet is in the user's
        # stream.
        # the on_tweet event won't be triggered by retweets if there
        # is an handler for the on_retweet event.
        @events.on_retweet.handler
        def retweet(self, data):
            pass

        # the on_follow event is triggered when the user gets a new follower
        # or the user follows someone
        # https://dev.twitter.com/streaming/overview/messages-types#events-event
        @events.on_follow.handler
        def follow(self, data):
            print("You have a new follower @%s" % data.source.screen_name)

        # the default event is the last event to be triggered
        # if no other event was triggered by the data then this one will be
        @events.default.handler
        def default(self, data):
            print(data)


    if __name__ == '__main__':
        client = Client(**creds)
        client.run()

Default events
--------------

All the events name can be found in :obj:`peony.commands.event_types`.

Custom events
-------------

If you ever need to create your own events that can easily be done with
the :func:`~peony.commands.event_types.events`.
The function decorated with this decorator must have at least 1 argument that
corresponds to the data received and return ``True`` if the data should
trigger this event and ``False`` otherwise.
It is recommended to use the :func:`events.priority`
decorator so that your event will be processed before the ones provided in Peony.

.. code-block:: python

    from peony import events, PeonyClient, EventStream

    # a priority should be set if you want to make sure that your event
    # would not collide with another
    # a number < -5 is probably a good bet (events with the smallest number
    # are processed first)
    @events.priority(-10)
    def on_followed(data, client):
        """
            Event triggered when the user gets a new follower

        Note the optional second positional argument `client` that will be
        given if a function with a second argument is provided to the `events`
        decorator.
        """
        return data.event == 'follow' and data.target.id == client.user.id

    @events.priority(-10)
    def on_tweet_with_media(data):
        """
            Event triggered when the data corresponds to a tweet with a media
        """
        return 'media' in data.get('entities', {})


    @PeonyClient.event_stream
    class UserStream(EventStream):

        def stream_request(self):
            """
                The stream_request method returns the request
                that will be used by the stream
            """
            return self.userstream.user.get()

        @events.on_connect.handler
        def connect(self):  # handlers should work without the data parameter
            print("Connected to the stream")

        # custom handlers are used just like you'd use a default handler
        @on_followed.handler
        def followed(self, data):
            print("@%s followed you" % data.source.screen_name)

        @on_tweet_with_media.handler
        def tweet_with_media(self, data):
            print(data.text)

Stream iterator
---------------

If all this sounded too complicated to integrate in your program you can just
use the stream iterator:

.. code-block:: python

    from peony import PeonyClient, events

    client = PeonyClient(**creds)

    @events.priority(-10)
    def on_tweet_with_media(data):
        """
            Event triggered when the data corresponds to a tweet with a media
        """
        return 'media' in data.get('entities', {})

    async def stream():
        async with self.userstream.user.get() as stream:
            async for data in stream:
                if events.on_connect(data):
                    print("Connected to the stream")
                elif events.on_follow(data):
                    print("@%s followed you" % data.source.screen_name)
                elif on_tweet_with_media(data):
                    print(data.text)


This is pretty much equivalent to the stream in the previous section.
