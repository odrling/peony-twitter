#!/usr/bin/env python3

import asyncio
import time
import os

try:
    from . import peony, api, testdir
except (SystemError, ImportError):
    from __init__ import peony, testdir
    import api


class BDClient(peony.PeonyClient):

    def __init__(self, birthday, BD_name, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.birthday = (*birthday, 0, 0, 0, 0, 0, -1)
        self.BD_name = BD_name
        self.default_name = self.user.name

    async def settz(self):
        """
            set the environment timezone to the timezone
            set in your twitter settings
        """
        settings = await self.api.account.settings.get()

        tz = settings.time_zone.tzinfo_name

        os.environ['TZ'] = tz
        time.tzset()

    @property
    def time_until_BD(self):
        year = time.localtime().tm_year

        birthday = time.mktime((year, *self.birthday))

        if birthday < time.time():
            birthday = time.mktime((year + 1, *self.birthday))

        return birthday - time.time()

    @property
    def time_until_BDend(self):
        year = time.localtime().tm_year

        end = time.mktime((year, *self.birthday)) + 3600 * 24

        if end < time.time():
            end = time.mktime((year + 1, *self.birthday)) + 3600 * 24

        return end - time.time()

    async def setBDName(self, name):
        await self.api.account.update_profile.post(name=name)

    async def main(self):
        try:
            await self.settz()
            print("Timezone in use is", os.environ['TZ'])
        except:
            print("Timezone in use is that of your computer")

        await asyncio.sleep(self.time_until_BD)
        await self.setBDName(self.BD_name)

        await asyncio.sleep(self.time_until_BDend)
        await self.setBDName(self.default_name)


def get_BD(msg):
    birthday = input(msg)
    BD = [int(i) for i in birthday.split('/')]

    # quick check of the input
    if BD[0] not in range(13) or BD[1] not in range(32):
        msg = "Birthday date (%s) is incorrect" % birthday
        raise RuntimeError(msg)

    return BD


if __name__ == '__main__':
    loop = asyncio.get_event_loop()

    BD = get_BD("Your birthday (mm/dd): ")
    BD_name = input("Name during your birthday: ")

    client = BDClient(BD, BD_name, **api.keys, loop=loop)

    loop.run_until_complete(client.main())
