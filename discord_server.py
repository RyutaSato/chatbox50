from uuid import UUID

import discord.utils
from discord import (
    Client, Intents, Message, Guild, PermissionOverwrite, Role, Invite, ForumChannel
)
import typing

from chatbox50 import Chatbox
FORUM_TEMPLATE = """
this is checkbox50.
set uid as `{}`

"""

class DiscordServer(Client):
    def __init__(self, name: str,  *, intents: Intents = Intents.all(), **options: typing.Any):
        super().__init__(intents=intents, **options)
        self.chat_boxes: dict[UUID, Chatbox] = dict()  # dict[Chatbox.uid, Chatbox]
        self._forum_chatbox_id: dict[int, UUID] = dict()  # dict[ForumChannel.id, Chatbox.uid]
        self.channels: dict[int, ForumChannel] = dict()  # dict[ForumChannel.id, ForumChannel]

    def get_chatbox(self, channel_id: int) -> Chatbox | None:
        chat_box_uid = self._forum_chatbox_id.get(channel_id)
        if chat_box_uid is None:
            return None
        chat_box = self.chat_boxes.get(chat_box_uid)
        return chat_box

    async def on_message(self, message: Message):
        # ignore a message sent by this bot.
        if message.author == self.user:
            return
        chat_box = self.get_chatbox(message.channel.id)
        if chat_box is not None:
            await message.channel.send(f"received: {message.content}")
        print(message.guild, message.channel, message.type, type(message), type(message.channel))

    async def on_guild_join(self, guild: Guild):
        new_chat_box = Chatbox(guild.name)
        new_forum = await guild.create_forum("chatbox50")
        self.subscribe_forum_and_chatbox(new_forum, new_chat_box)

        # forum.create_thread()

    async def on_ready(self):
        async for guild in self.fetch_guilds():
            channel = discord.utils.get(self.get_all_channels(), name="chatbox50")
            if isinstance(channel, ForumChannel):
                chat_box = Chatbox(channel.guild.name)
            else:
                chat_box = Chatbox(guild.name)
                channel = await guild.create_forum("chatbox50", topic=FORUM_TEMPLATE.format(chat_box.uid))
            self.subscribe_forum_and_chatbox(channel, chat_box)

    def subscribe_forum_and_chatbox(self, forum: ForumChannel, chat_box: Chatbox):
        self._forum_chatbox_id[forum.id] = chat_box.uid
        self.channels[forum.id] = forum
        self.chat_boxes[chat_box.uid] = chat_box

    async def on_accessed_customer(self, forum_id, uid):
        pass
        # self.chat_box.active_client() await self.channels[forum_id].create_thread(name=str(uid))

if __name__ == '__main__':
    server = DiscordServer("test")
    server.run("MTA3MjAxMDk1MjQ0MDAyMTA4NA.Gfgw-Z.qpT9kCwSoloS2kKe4a1Z5H6N2YFSnLUoAY_7Oo")
