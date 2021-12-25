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

By default the :class:`~peony.client.PeonyClient` makes 2 requests after being
started:

* account/verify_credentials.json (kept as ``self.user``)
* help/twitter_configuration.json (kept as ``self.twitter_configuration``)

If you need to have more informations during the initialization of a client you
should use the :func:`~peony.commands.tasks.init_task` decorator.
The methods decorated with this decorator will be started on setup.

.. code-block:: python

    from peony import PeonyClient, init_tasks

    class Client(PeonyClient):

        @init_tasks
        async def get_setting():
            self.settings = await self.api.account.settings.get()

        @init_tasks
        async def get_likes():
            self.likes = await self.api.favorites.list.get(count=200)


.. note::
    The attributes user and twitter_configuration are created by the tasks
    in PeonyClient.init_tasks() which are the respectively the responses from
    /1.1/account/verify_credentials.json and /1.1/help/configuration.json.
    So you can access self.user.id in the class and this will give you the id
    of the authenticated user.

.. note::
    The attribute ``twitter_configuration`` is used by the method
    upload_media when it converts your picture

The ``task`` decorator
----------------------

First you will need to create a subclass of PeonyClient and add a
:func:`~peony.commands.tasks.task`
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


    def main():
        """ start all the tasks """
        loop = asyncio.get_event_loop()

        # set your api keys here
        awesome_client = AwesomePeonyClient(
            consumer_key=your_consumer_key,
            consumer_secret=your_consumer_secret,
            access_token=your_access_token,
            access_token_secret=your_access_token_secret,
            loop=loop
        )

        awesome_client.run()  # you can also use the run_tasks()
                              # coroutine if you need it


    if __name__ == '__main__':
        main()


.. note::

    The :meth:`~peony.client.BasePeonyClient.run_tasks` method can be used
    instead of :meth:`~peony.client.BasePeonyClient.run` to start the tasks.
    Just keep in mind that :meth:`~peony.client.BasePeonyClient.run` is a
    wrapper around :meth:`~peony.client.BasePeonyClient.run_tasks` with some
    basic features such as handling :exc:`KeyboardInterrupt` and run
    :meth:`~peony.client.BasePeonyClient.close` when all the tasks are complete.
