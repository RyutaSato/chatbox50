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
    def __init__(self, send_queue: asyncio.Queue, receive_queue: asyncio.Queue, *, intents: Intents = Intents.all(),
                 **options: typing.Any):
        super().__init__(intents=intents, **options)
        self.server_send_que = send_queue
        self.server_receive_que = receive_queue
        self.channel: ForumChannel | None = None
        self._forum_chatbox_id: dict[int, UUID] = dict()  # dict[ForumChannel.id, Chatbox.uid]
        # self.channels: dict[int, ForumChannel] = dict()  # dict[ForumChannel.id, ForumChannel]
        self.threads: dict[int, Thread] = dict()  # dict[Thread.id, Thread]

    async def on_message(self, message: Message):  # Event Callback
        # ignore a message sent by this bot.
        if message.author == self.user:
            return
        if message.channel.id == self.channel.id:
            msg = chatbox50.Message(message.channel.name, chatbox50.SentBy.server, message.content)
            await self.server_send_que.put(msg)
            print(message.guild, message.channel, message.type, type(message), type(message.channel))

    # async def on_guild_join(self, guild: Guild):  # Event Callback
    #     new_chat_box = Chatbox(guild.name)
    #     new_forum = await guild.create_forum("chatbox50")
    #     self.subscribe_forum_and_chatbox(new_forum, new_chat_box)

        # forum.create_thread()
    async def create_thread_callback(self, client: chatbox50.ChatClient):

        # ** このコールバックをchatboxに登録する．
        # threadを作成する
        # self.threadsに登録する.
        #

        pass

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

    async def send_message_task(self):
        while True:
            msg: chatbox50.Message = await self.server_receive_que.get()
            self.channel.threads




if __name__ == '__main__':
    server = DiscordServer()
    TOKEN = os.getenv("DISCORD_TOKEN")
    print(TOKEN)
    server.run(TOKEN)
