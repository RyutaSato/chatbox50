import asyncio
import os
from uuid import UUID

import discord.utils
from discord import (
    Client, Intents, Message, Guild, ForumChannel, Thread
)
import typing

import chatbox50

FORUM_TEMPLATE = """
this is checkbox50.
set uid as `{}`

"""


class DiscordServer(Client):
    def __init__(self, api: chatbox50.ServiceWorker, *, intents: Intents = Intents.all(),
                 **options: typing.Any):
        super().__init__(intents=intents, **options)
        self._api = api
        self._api.set_created_callback(self.__create_thread_callback)
        self._api.set_received_message_callback(self.__received_message_callback)
        self.channel: ForumChannel | None = None
        self._forum_chatbox_id: dict[int, UUID] = dict()  # dict[ForumChannel.id, Chatbox.uid]
        # self.channels: dict[int, ForumChannel] = dict()  # dict[ForumChannel.id, ForumChannel]
        self.threads: dict[int, Thread] = dict()  # dict[Thread.id, Thread]

    async def on_message(self, message: Message):  # Event Callback
        # ignore a message sent by this bot.
        if message.author == self.user:
            return
        if isinstance(message.channel, Thread) and message.channel.parent_id == self.channel.id:
            msg_sender = self._api.get_msg_sender(message.channel.id)
            await msg_sender(message.content)
            print(message.guild, message.channel, message.type, type(message), type(message.channel))

    # async def on_guild_join(self, guild: Guild):  # Event Callback
    #     new_chat_box = Chatbox(guild.name)
    #     new_forum = await guild.create_forum("chatbox50")
    #     self.subscribe_forum_and_chatbox(new_forum, new_chat_box)

    # forum.create_thread()
    async def __create_thread_callback(self, *args) -> int:
        thread, _ = await self.channel.create_thread(name=str(args[0]))
        self.threads[thread.id] = thread
        return thread.id

    async def __received_message_callback(self, message: chatbox50.Message):
        if message.sent_by == chatbox50.SentBy.s2:
            return
        thread: Thread = self.threads.get(message.service2_id)
        await thread.send(message.content)

    async def on_ready(self):  # Event Callback
        async for guild in self.fetch_guilds():
            # channel = discord.utils.get(self.get_all_channels(), name="chatbox50")
            # self.channel_id = channel.id
            channel = discord.utils.get(guild.channels, name="chatbox50")
            if isinstance(channel, ForumChannel):
                self.channel = channel
                for thread in self.channel.threads:
                    self.threads[thread.id] = thread
                break
