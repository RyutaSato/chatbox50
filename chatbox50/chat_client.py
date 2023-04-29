import asyncio
from uuid import UUID, uuid4
from chatbox50.db_session import SQLSession
from chatbox50.message import Message
import logging

logger = logging.getLogger("client")


class ChatClient:
    def __init__(self,
                 uid: UUID | None = None,
                 messages=None,
                 ):
        if messages is None:
            self.__messages = []
        else:
            self.__messages: list[Message] = messages
        self.message_callback = None
        self._s1_id = None
        self._s2_id = None
        self.__msg_num = 0
        if uid is None:
            self.__uid = uuid4()
        elif isinstance(uid, UUID):
            self.__uid = uid
        else:
            raise AttributeError(f"the type of `uid` must be `UUID` or unique `str` not `{type(uid)}`")

    @property
    def uid(self):
        return self.__uid

    @property
    def s1_id(self):
        return self._s1_id

    @property
    def s2_id(self):
        return self._s2_id



    def add_message(self, message):
        self.__messages.append(message)
