import asyncio
from uuid import UUID
from chatbox50.db_session import SQLSession
from chatbox50.message import Message
import logging

logger = logging.getLogger("client")


class ChatClient:
    def __init__(self,
                 session: SQLSession,
                 thread_id: int,
                 que_thread_id_and_msg_tuple: asyncio.Queue,
                 uid: UUID):
        self._session = session
        self._messages: list[Message] = []
        self._msg_num = 0
        self.thread_id = thread_id
        self._que_thread_id_and_msg_tuple = que_thread_id_and_msg_tuple
        self._uid = uid
        self.msg_client_to_room: asyncio.Queue[Message] = asyncio.Queue()
        self.msg_thread_to_client: asyncio.Queue[Message] = asyncio.Queue()
        self._send_task = asyncio.create_task(self._send_to_room())
        if isinstance(uid, UUID):
            if self._get_history():  # if success
                self.__msg_num = len(self._messages)
            else:
                logger.info("otherwise, new client was created.")
                # if uid is wrong or None, create new client uid and add to DB
                self._commit_client_to_db()

    def __del__(self):
        self.commit_to_db()
        self._send_task.cancel()

    @property
    def messages(self):
        return self._messages

    @property
    def uid(self):
        return self._uid

    async def add_message(self, content: Message | str, is_server=False):
        if isinstance(content, Message):
            self._messages.append(content)
            if is_server:
                await self.msg_thread_to_client.put(content)
            else:
                await self.msg_client_to_room.put(content)
        elif isinstance(content, str):
            if is_server:
                msg = Message(uid=None, content=content)
                self._messages.append(msg)
                await self.msg_thread_to_client.put(msg)
            else:
                msg = Message(uid=self._uid, content=content)
                self._messages.append(msg)
                await self.msg_client_to_room.put(msg)
        else:
            raise ValueError(f"`value` must be `Message` or `str`, not {type(content)}")

    def commit_to_db(self):
        self._session.add_messages(self._uid, messages=self._messages[self._msg_num:])
        self._msg_num = len(self._messages)

    def _get_history(self):
        histories: list | None = self._session.get_history(client_uid=self._uid)
        if histories is None:
            logger.info(f"cancelled to get history from DB due not to find uid: {self._uid}")
            return False
        self._messages.extend(histories)
        return True

    def _commit_client_to_db(self):
        self._session.add_new_client(self._uid)

    async def _send_to_room(self):
        while True:
            msg = await self.msg_client_to_room.get()
            await self._que_thread_id_and_msg_tuple.put((self.thread_id, msg.content))
