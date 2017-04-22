#!/usr/bin/env python3

import asyncio
import os
import time

try:
    from . import peony, api
except (SystemError, ImportError):
    from __init__ import peony
    import api


class BDClient(peony.PeonyClient):

    def __init__(self, birthday, birthday_name, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.birthday = (*birthday, 0, 0, 0, 0, 0, -1)
        self.birthday_name = birthday_name
        self.default_name = self.user.name

    async def set_tz(self):
        """
            set the environment timezone to the timezone
            set in your twitter settings
        """
        settings = await self.api.account.settings.get()

        tz = settings.time_zone.tzinfo_name

        os.environ['TZ'] = tz
        time.tzset()

    @property
    def time_until_birthday(self):
        year = time.localtime().tm_year

        birthday = time.mktime((year, *self.birthday))

        if birthday < time.time():
            birthday = time.mktime((year + 1, *self.birthday))

        return birthday - time.time()

    @property
    def time_until_birthday_end(self):
        year = time.localtime().tm_year

        end = time.mktime((year, *self.birthday)) + 3600 * 24

        if end < time.time():
            end = time.mktime((year + 1, *self.birthday)) + 3600 * 24

        return end - time.time()

    async def set_birthday_name(self, name):
        await self.api.account.update_profile.post(name=name)

    async def main(self):
        try:
            await self.set_tz()
            print("Timezone in use is", os.environ['TZ'])
        except:
            print("Timezone in use is that of your computer")

        await asyncio.sleep(self.time_until_birthday)
        await self.set_birthday_name(self.birthday_name)

        await asyncio.sleep(self.time_until_birthday_end)
        await self.set_birthday_name(self.default_name)


def get_birthday(msg):
    birthday = input(msg)
    birthday = [int(i) for i in birthday.split('/')]

    # quick check of the input
    if birthday[0] not in range(13) or birthday[1] not in range(32):
        msg = "Birthday date (%s) is incorrect" % birthday
        raise RuntimeError(msg)

    return birthday


if __name__ == '__main__':
    loop = asyncio.get_event_loop()

    birthday = get_birthday("Your birthday (mm/dd): ")
    birthday_name = input("Name during your birthday: ")

    client = BDClient(birthday, birthday_name, **api.keys, loop=loop)

    loop.run_until_complete(client.main())
