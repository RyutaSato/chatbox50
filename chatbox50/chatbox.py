import asyncio
from uuid import UUID, uuid4
from chatbox50.db_session import SQLSession
from chatbox50.chat_client import ChatClient
from chatbox50.message import Message


class Chatbox:
    def __init__(self,
                 name: str,
                 room_id,
                 create_room_and_get_room_id_callback: callable,
                 que_room_id_and_msg_tuple: asyncio.Queue,
                 uid: UUID | None = None,
                 debug=False):
        self._name = name
        self._room_id = room_id
        if not callable(create_room_and_get_room_id_callback):
            raise TypeError(f"create_room_and_get_room_id_callback is invalid argument. type: "
                            f"{create_room_and_get_room_id_callback}, "
                            f"{type(create_room_and_get_room_id_callback)}")
        self._create_room_and_get_room_id_callback = create_room_and_get_room_id_callback
        self.que_room_id_and_msg_tuple = que_room_id_and_msg_tuple
        self.session = SQLSession(name, init=True, debug=debug)
        if isinstance(uid, UUID):
            self._uid = uid
        else:
            self._uid = uuid4()
        self._monitored: set[int] = set()
        self._active: dict[UUID, ChatClient] = dict()
        # self._message_broker = create_task(self.__message_broker())

    @property
    def name(self):
        return self._name

    @property
    def room_id(self):
        return self._room_id

    @property
    def uid(self):
        return self._uid

    @property
    def monitored(self):
        return self._monitored

    #
    # def create_new_client(self):
    #     """
    #     subscribe new ChatClient to Chatbox._active
    #     Returns:
    #         UUID: new ChatClient uid
    #     """
    #     client = ChatClient(self.session)
    #     self._active[client.uid] = client
    #     return client.uid

    async def get_client_or_create_new_client(self, uid: UUID) -> ChatClient:
        client = self._active.get(uid)
        if client is None:
            self.session.get_or_add_new_client_id(uid)
            thread_id = await self._create_room_and_get_room_id_callback(uid)
            client = ChatClient(session=self.session,
                                thread_id=thread_id,
                                que_thread_id_and_msg_tuple=self.que_room_id_and_msg_tuple,
                                uid=uid)
            self._active[uid] = client
        return client

    def deactivate_client(self, uid: UUID):
        client = self._active.get(uid)
        client.commit_to_db()
        del self._active[uid]

    def add_message(self, client_uid: UUID, content: str, is_server=False):
        client = self._active.get(client_uid)
        print(client)
        print(f"add_message: client: {client.thread_id} {client.messages}")
        client.add_message(content, is_server)
