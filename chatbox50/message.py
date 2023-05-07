from __future__ import annotations

from datetime import datetime
from enum import IntEnum
from uuid import UUID

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from chatbox50.chat_client import ChatClient


class SentBy(IntEnum):
    s1 = 0
    s2 = 1


class Message:
    def __init__(self,
                 chat_client: ChatClient,
                 sent_by: SentBy,
                 content: str,
                 created_at: datetime = datetime.utcnow()):
        self.__chat_client = chat_client
        self.created_at = created_at
        self.content = content
        self.sent_by = sent_by

    def __getitem__(self, item):
        return self.__chat_client[item]

    @property
    def uid(self) -> UUID:
        return self.__chat_client.uid

    @property
    def service1_id(self):
        return self.__chat_client.s1_id

    @property
    def service2_id(self):
        return self.__chat_client.s2_id

    def get_id(self, sent_by: SentBy):
        if sent_by == SentBy.s1:
            return self.service1_id
        elif sent_by == SentBy.s2:
            return self.service2_id
        else:
            raise AttributeError()


if __name__ == '__main__':
    a = SentBy.s1
    print(a.name)
