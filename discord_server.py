import asyncio
from uuid import UUID
import sqlite3
import discord.utils
import logging

logging.basicConfig(level=logging.DEBUG)
from discord import (
    Client, Intents, Message, Guild,  ForumChannel, Thread
)
import typing

from chatbox50 import Chatbox

FORUM_TEMPLATE = """
this is checkbox50.
set uid as `{}`

"""


class DiscordServer(Client):
    def __init__(self,
                 name: str,
                 chat_boxes: dict[UUID, Chatbox],
                 tasks: set[asyncio.Task],
                 *,
                 intents: Intents = Intents.all(),
                 **options: typing.Any):
        super().__init__(intents=intents, **options)
        self.name = name
        self.chat_boxes: dict[UUID, Chatbox] = chat_boxes  # dict[room_uid, Chatbox]
        self._tasks: set[asyncio.Task] = tasks
        self._forum_chat_box_id: dict[int, UUID] = dict()  # dict[ForumChannel.id, Chatbox.uid]
        self._thread_id_chat_box_uid: dict[int, UUID] = dict()
        self._client_uid_thread_id: dict[UUID, int] = dict()
        self._thread_id_client_uid: dict[int, UUID] = dict()
        self._que_thread_id_and_msg = asyncio.Queue()
        self._tasks.add(asyncio.create_task(self._message_broker()))

        self._db_conn = sqlite3.connect(name + '.db')
        cur = self._db_conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS server("
                    "forum_id INTEGER PRIMARY KEY,"
                    "name TEXT NOT NULL,"
                    "room_uid VARCHAR(40) NOT NULL)")
        cur.execute("SELECT name, forum_id, room_uid FROM server")

        for name, room_id, uid in cur.fetchall():
            print(name, room_id, uid)
            chat_box = Chatbox(name=name,
                               room_id=int(room_id),
                               uid=UUID(uid),
                               create_room_and_get_room_id_callback=self._create_thread_func(int(room_id)),
                               que_room_id_and_msg_tuple=self._que_thread_id_and_msg)
            self.chat_boxes[chat_box.uid] = chat_box
            self._forum_chat_box_id[chat_box.room_id] = chat_box.uid



    def get_chatbox(self, channel_id: int) -> Chatbox | None:
        chat_box_uid = self._forum_chat_box_id.get(channel_id)
        if chat_box_uid is None:
            return None
        chat_box = self.chat_boxes.get(chat_box_uid)
        return chat_box

    async def on_message(self, message: Message):
        # ignore a message sent by this bot.
        if message.author == self.user:
            return
        # TODO: need debug  chat_box_uid include client_uid
        # chat_box_uid: UUID | None = self._thread_id_chat_box_uid.get(message.channel.id)
        chat_box = self.get_chatbox(message.channel.parent_id)
        print(f"chat_box_uid:{chat_box.uid}")
        if chat_box is None:
            print(f"on_message: can't find chat_box_uid")
            return

        # chat_box = self.chat_boxes.get(chat_box_uid)
        # print(chat_box)
        client = await chat_box.get_client_or_create_new_client(UUID(message.channel.name))
        # client_uid = self._thread_id_client_uid.get(message.channel.id)
        # print(chat_box_uid, client_uid, message.author, message.content, self._thread_id_client_uid.get(
        #     message.channel.id))
        # chat_box.add_message(client_uid=client_uid,
        #                      content=message.content,
        #                      is_server=True)
        await client.add_message(content=message.content, is_server=True)


    async def get_thread_or_new_thread(self, room_uid: UUID, uid: UUID) -> Thread | None:
        chat_box = self.chat_boxes.get(room_uid)
        if chat_box is None:
            return None
        thread_id = self._client_uid_thread_id.get(uid)
        if thread_id is not None:
            thread: Thread = self.get_channel(thread_id)
        else:
            channel: ForumChannel = self.get_channel(chat_box.room_id)
            if not isinstance(channel, ForumChannel):
                raise SyntaxError("include chat_box uid includes non ForumChannel id")
            thread, _ = await channel.create_thread(name=str(uid))
        self._subscribe_thread(thread, uid, room_uid)
        return thread

    async def _message_broker(self):
        while True:
            thread_id, msg = await self._que_thread_id_and_msg.get()
            print(f"thread_id: {thread_id}, msg: {msg}")
            await self.send_message(thread_id, msg)

    async def send_message(self, thread_id: int, msg: str):
        thread: Thread = self.get_channel(thread_id)
        print(thread.name, thread.last_message)
        message = await thread.send(content=msg)
        print(f"sent: {message.channel} {message.id}")

    async def on_guild_channel_create(self, channel):
        print("is_called")
        if isinstance(channel, ForumChannel) and channel.name.lower().startswith("chatbox50_"):
            name = channel.name[10:]

            print("is_called")
            chat_box = Chatbox(name=name,
                               room_id=channel.id,
                               create_room_and_get_room_id_callback=self._create_thread_func(channel.id),
                               que_room_id_and_msg_tuple=self._que_thread_id_and_msg)
            self.chat_boxes[chat_box.uid] = chat_box
            self._forum_chat_box_id[chat_box.room_id] = chat_box.uid
            cur = self._db_conn.cursor()
            print("is_called")
            cur.execute("INSERT INTO server(forum_id, name, room_uid) VALUES (?, ?, ?)",
                        (channel.id, name, str(chat_box.uid)))
            self._db_conn.commit()
            print("is_called")
            await channel.edit(topic=f"clients can access the forum by\n http://127.0.0.1:8000/{chat_box.uid}")

    def _create_thread_func(self, channel_id):
        async def create_or_get_thread_id(uid: UUID) -> int:
            channel: ForumChannel = self.get_channel(channel_id)
            thread = discord.utils.get(channel.threads, name=str(uid))
            if thread is None:
                thread, _ = await channel.create_thread(name=str(uid), content="new client accessed")
            self._subscribe_thread(thread, uid)
            return thread.id
        return create_or_get_thread_id

    def _subscribe_thread(self, thread: Thread, uid: UUID, room_uid: UUID | None = None):
        self._client_uid_thread_id[uid] = thread.id
        self._thread_id_client_uid[thread.id] = uid
        if room_uid is not None:
            self._thread_id_chat_box_uid[thread.id] = room_uid

if __name__ == '__main__':
    server = DiscordServer("test", )
    server.run("MTA3MjAxMDk1MjQ0MDAyMTA4NA.Gfgw-Z.qpT9kCwSoloS2kKe4a1Z5H6N2YFSnLUoAY_7Oo")
