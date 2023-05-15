from uuid import UUID

import discord.utils
from discord import (
    Client, Intents, Message, ForumChannel, Thread
)
import typing
import logging

import chatbox50
discord.VoiceClient.warn_nacl = False
FORUM_TEMPLATE = """
this is checkbox50.
set uid as `{}`

"""


class DiscordServer(Client):
    def __init__(self, api: chatbox50.ServiceWorker, _logger: logging.Logger, *, intents: Intents = Intents.all(),
                 **options: typing.Any):
        super().__init__(intents=intents, **options)
        self._api = api
        self._api.set_create_callback(self.__create_thread_callback)
        self._api.set_received_message_callback(self.__received_message_callback)
        self.channel: ForumChannel | None = None
        self._forum_chatbox_id: dict[int, UUID] = dict()  # dict[ForumChannel.id, Chatbox.uid]
        # self.channels: dict[int, ForumChannel] = dict()  # dict[ForumChannel.id, ForumChannel]
        self.threads: dict[int, Thread] = dict()  # dict[Thread.id, Thread]
        self.logger = _logger.getChild("discord")

    async def on_message(self, message: Message):  # Event Callback
        # ignore a message sent by this bot.
        if message.author == self.user:
            return
        self.logger.debug(f"received: from:{message.author} content: {message.content}")
        if isinstance(message.channel, Thread) and message.channel.parent_id == self.channel.id:
            msg_sender = self._api.get_msg_sender(message.channel.id)
            await msg_sender(message.content)

    async def __create_thread_callback(self, name: UUID) -> int:
        result = await self.channel.create_thread(name=str(name), content="new client access")
        if result is None:
            self.logger.error({"place": "discord", "action": "create_callback",
                               "status": "error", "content": "result is None", "name": str(name)})
        thread, _ = result
        self.threads[thread.id] = thread
        return thread.id

    async def __accessed_callback(self, service_id: int):
        ch = await self.fetch_channel(service_id)
        self.threads[service_id] = ch
        await ch.send("client connected!")

    async def __received_message_callback(self, message: chatbox50.Message):
        if message.sent_by == chatbox50.SentBy.s2:
            return
        thread: Thread = self.threads.get(message.service2_id)
        if thread is None:
            thread: Thread = await self.fetch_channel(message.service2_id)
            if not thread:
                self.threads[message.service2_id] = thread
        if thread is None:
            self.logger.error(
                {"action": "receive_msg", "status": "error", "content": "Can't find service_id in threads",
                 "message_content": message.content, "s2_id": str(message.service2_id)})
            return
        await thread.send(message.content)

    async def on_ready(self):  # Event Callback
        self.logger.debug("Discord server setup...")
        async for guild in self.fetch_guilds():
            channels = await guild.fetch_channels()
            for channel in channels:
                if isinstance(channel, ForumChannel) and channel.name == "chatbox50":
                    self.logger.debug(f"Found Forum channel id: {channel.id} {channel}")
                    self.channel = channel
                    for thread in self.channel.threads:
                        self.logger.debug(f"Found thread : {thread.name} {thread.id}")
                        self.threads[thread.id] = thread
                    break

        if self.channel is None:
            raise RuntimeError("can't find chatbox50 ForumChannel")
        else:
            self.logger.info("setup completed.")
            self.logger.info(f"ChatBox50 forum channel is {self.channel.id}")
            self.logger.info(f"there are already threads, {self.channel.threads}")


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
