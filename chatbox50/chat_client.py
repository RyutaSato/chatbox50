import asyncio
from uuid import UUID, uuid4
from chatbox50.db_session import SQLSession
from chatbox50.message import Message
import logging

logger = logging.getLogger("client")


class ChatClient:
    def __init__(self,
                 uid: UUID | str,
                 messages=None,
                 ):
        if messages is None:
            self.__messages = []
        else:
            self.__messages: list[Message] = messages
        self.__msg_num = 0
        if isinstance(uid, str):
            self.__uid = UUID(uid)
        elif isinstance(uid, UUID):
            self.__uid = uid
        else:
            raise AttributeError(f"the type of `uid` must be `UUID` or unique `str` not `{type(uid)}`")

    @property
    def uid(self):
        return self.__uid

    def add_message(self, message):
        self.__messages.append(message)
