=======
 Tasks
=======

The main advantage of an asynchronous client is that it will be able to run
multiple tasks... asynchronously.
Which is quite interesting here if you want to access several Streaming APIs,
or perform some requests periodically while using a Streaming API.


So I tried to make it easier to create such a program.

Init tasks
----------

By default the client makes 2 requests on initialization that are kept as
attributes of the client:
* account/verify_credentials.json (kept as self.user)
* help/twitter_configuration.json (kept as self.twitter_configuration)

If you need to have more informations during the initialization of a client you
should override the `init_tasks` method of your subclass. This will run all the
coroutines held by the list returned by the method at the same time during the
initialization (that's the point of an asynchronous client after all).

.. code-block:: python

    import asyncio
    from peony import PeonyClient

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


*Note*: The attributes user and twitter_configuration are created by the tasks
in PeonyClient.init_tasks() which are the respectively the responses from
/1.1/account/verify_credentials.json and /1.1/help/configuration.json.
So you can access self.user.id in the class and this will give you the id of
the authenticated user.

*Note*: The attribute ``twitter_configuration`` is used by the method
upload_media when it converts your picture

The ``task`` decorator
----------------------

First you will need to create a subclass of PeonyClient and add a ``task``
decorator to the methods that you want to run.

.. code-block:: python

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

        asyncio.ensure_future(asyncio.wait(awesome_client.get_tasks()))
        loop.run_forever()

        # if there was no stream:
        # loop.run_until_complete(asyncio.wait(awesome_client.tasks))


    if __name__ == '__main__':
        main()

Event handlers
--------------

Let's say that your awesome bot has become very popular, and so you'd like to
add some new features to it that would make use of the Streaming API. You could
use the `task` decorator but there is a better way to do it.

*keeping the code from above*

.. code-block:: python

    from peony import EventStream, event_handler, events

    # adding permissions dirtily, you should probably try to load them in
    # AwesomePeonyClient.__init__ instead
    AwesomePeonyClient.permissions = {
        "admin": [42]  # list of user id
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
