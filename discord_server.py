import asyncio
import os
from uuid import UUID

import discord.utils
from discord import (
    Client, Intents, Message, Guild, ForumChannel, Thread
)
import typing
import logging

logger = logging.getLogger(__name__)
import chatbox50
discord.VoiceClient.warn_nacl = False
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
        logger.debug(f"received: from:{message.author} content: {message.content}")
        if isinstance(message.channel, Thread) and message.channel.parent_id == self.channel.id:
            msg_sender = self._api.get_msg_sender(message.channel.id)
            await msg_sender(message.content)

    async def __create_thread_callback(self, name: str, *args) -> int:
        thread, _ = await self.channel.create_thread(name=name)
        self.threads[thread.id] = thread
        return thread.id

    async def __received_message_callback(self, message: chatbox50.Message):
        if message.sent_by == chatbox50.SentBy.s2:
            return
        thread: Thread = self.threads.get(message.service2_id)
        await thread.send(message.content)

    async def on_ready(self):  # Event Callback
        logger.debug("Discord server setup...")
        async for guild in self.fetch_guilds():
            channels = await guild.fetch_channels()
            for channel in channels:
                if isinstance(channel, ForumChannel) and channel.name == "chatbox50":
                    logger.debug(f"Found Forum channel id: {channel.id} {channel}")
                    self.channel = channel
                    for thread in self.channel.threads:
                        logger.debug(f"Found thread : {thread.name} {thread.id}")
                        self.threads[thread.id] = thread
                    break

        if self.channel is None:
            raise RuntimeError("can't find chatbox50 ForumChannel")
        else:
            logger.info("setup completed.")
            logger.info(f"ChatBox50 forum channel is {self.channel.id}")
            logger.info(f"there are already threads, {self.channel.threads}")


if __name__ == '__main__':
    import os
    from chatbox50 import ChatBox

    logging.basicConfig(level=logging.DEBUG)
    TOKEN = os.getenv("DISCORD_TOKEN")
    print(TOKEN)
    NAME = "sample"
    cb = ChatBox(name=NAME, debug=True)
    ds = DiscordServer(cb.get_worker2)
    ds.run(TOKEN)
