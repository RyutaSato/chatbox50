import json
import pickle
from uuid import UUID, uuid4

from chatbox50._utils import Immutable
from chatbox50.message import Message
import logging

logger = logging.getLogger("chatbox.client")


class ChatClient:
    def __init__(self,
                 s1_id: Immutable,
                 s2_id: Immutable,
                 uid: UUID = uuid4(),
                 ):
        self.__messages: list[Message] = []
        self._s1_id = s1_id
        self._s2_id = s2_id
        self.__another_property = dict()
        self.number_of_saved_messages = 0
        if isinstance(uid, UUID):
            self.__uid = uid
        else:
            raise AttributeError(f"the type of `uid` must be `UUID` or unique `str` not `{type(uid)}`")

    def __setitem__(self, key, value):
        self.__another_property[key] = value

    def __getitem__(self, item):
        return self.__another_property[item]

    def __dict__(self):
        return json.dumps({"uid": str(self.__uid), "s1_id": str(self._s1_id), "s2_id": str(self._s2_id), "properties":
            self.__another_property})

    @property
    def uid(self) -> UUID:
        return self.__uid

    @property
    def s1_id(self) -> Immutable:
        return self._s1_id

    @property
    def s2_id(self) -> Immutable:
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

    # ** DEPRECATED ** because those id is set by Chatbox constractor in advance.
    # def set_s1_id(self, service_id: Immutable):
    #     if self._s1_id is not None:
    #         logger.warning("service1_id is already set. You are trying to overwrite it.")
    #     self._s1_id = service_id
    #
    # def set_s2_id(self, service_id: Immutable):
    #     if self._s2_id is not None:
    #         logger.warning("service2_id is already set. You are trying to overwrite it.")
    #     self._s2_id = service_id

    def pickle_properties(self) -> bytes:
        return pickle.dumps(self.__another_property)
