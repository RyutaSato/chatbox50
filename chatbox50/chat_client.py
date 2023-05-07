import asyncio
import pickle
from uuid import UUID, uuid4
from chatbox50.db_session import SQLSession
from chatbox50.message import Message
import logging

logger = logging.getLogger("client")


class ChatClient:
    def __init__(self,
                 uid: UUID | None = None,
                 s1_id: UUID | str | int | None = None,
                 s2_id: UUID | str | int | None = None,
                 ):
        self.__messages: list[Message] = []
        self._s1_id = s1_id
        self._s2_id = s2_id
        self.__another_property = dict()
        self.number_of_saved_messages = 0
        if uid is None:
            self.__uid = uuid4()
        elif isinstance(uid, UUID):
            self.__uid = uid
        else:
            raise AttributeError(f"the type of `uid` must be `UUID` or unique `str` not `{type(uid)}`")

    def __setitem__(self, key, value):
        self.__another_property[key] = value

    def __getitem__(self, item):
        return self.__another_property[item]

    @property
    def uid(self):
        return self.__uid

    @property
    def s1_id(self):
        return self._s1_id

    @property
    def s2_id(self):
        return self._s2_id

    @property
    def items(self):
        return self.__another_property

    @property
    def unsaved_messages(self) -> list[Message]:
        return self.__messages[self.number_of_saved_messages:]

    def add_message(self, message):
        if isinstance(message, Message) and message.uid == self.__uid:
            self.__messages.append(message)
        else:
            raise AttributeError()

    def set_s1_id(self, service_id):
        if self._s1_id is not None:
            logger.warning("service1_id is already set. You are trying to overwrite it.")
        self._s1_id = service_id

    def set_s2_id(self, service_id):
        if self._s2_id is not None:
            logger.warning("service2_id is already set. You are trying to overwrite it.")
        self._s2_id = service_id

    def pickle_properties(self) -> bytes:
        return pickle.dumps(self.__another_property)


