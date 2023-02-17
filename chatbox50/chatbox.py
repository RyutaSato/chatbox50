from asyncio import Queue, create_task
from uuid import UUID, uuid4
from chatbox50.db_session import SQLSession
from chatbox50.chat_client import ChatClient
from chatbox50.message import Message


class Chatbox:
    def __init__(self, name: str, debug=False):
        self._name = name
        self.session = SQLSession(name, init=True, debug=debug)
        self._uid = uuid4()
        self._monitored: set[int] = set()
        self._active: dict[UUID, ChatClient] = dict()
        self.msg_que: Queue[Message] = Queue()
        # self._message_broker = create_task(self.__message_broker())

    @property
    def name(self):
        return self._name

    @property
    def uid(self):
        return self._uid

    @property
    def monitored(self):
        return self._monitored

    def create_new_client(self):
        """
        subscribe new ChatClient to Chatbox._active
        Returns:
            UUID: new ChatClient uid
        """
        client = ChatClient(self.session)
        self._active[client.uid] = client
        return client.uid

    def active_client(self, uid: UUID | None):
        client = self._active.get(uid)
        if client is None:
            client = ChatClient(self.session, uid)
        return client

    def deactivate_client(self, uid: UUID):
        self._active[uid].commit_to_db()
        del self._active[uid]

    def add_message(self, client_uid: UUID, content: str):
        self._active[client_uid].add_message(content)

    async def __message_broker(self):
        while True:
            msg: Message = await self.msg_que.get()


if __name__ == '__main__':
    test1 = Chatbox("test1")
    print(test1.uid)
    test2 = Chatbox("test2")
    print(test2.monitored)
