from asyncio import Queue, create_task
from uuid import UUID, uuid4

from chatbox50._utils import run_as_await_func
from chatbox50.db_session import SQLSession
from chatbox50.chat_client import ChatClient
from chatbox50.service_worker import ServiceWorker
from chatbox50.message import Message, SentBy
import logging

logger = logging.getLogger(__name__)


class ChatBox:
    def __init__(self,
                 name: str = "ChatBox50",
                 s1_name: str = "server_1",
                 s2_name: str = "server_2",
                 s1_id_type=None,
                 s2_id_type=None,
                 debug=False):
        """

        Args:
            name: SQLのファイル名に使用されます．また，複数のChatBoxを持つ場合は，識別子として使用できます．ユニークである必要があります．
            s1_name: 1つ目のサービスの識別に利用できます．
            s2_name: 2つ目のサービスの識別に利用できます．s1_name と重複してはいけません．
            debug: Trueの場合，SQLiteのファイルは生成されません．
        """
        self._name = name
        self._uid = uuid4()
        self._s1_que = Queue()
        self._s2_que = Queue()
        self._s1_id_type = s1_id_type if s1_id_type is not None else UUID
        self._s2_id_type = s2_id_type if s2_id_type is not None else UUID

        self._service1 = ServiceWorker(name=s1_name, service_number=SentBy.s1, set_id_type=self._s1_id_type,
                                       upload_que=self._s1_que, new_access_callback=self.__new_access_from_service1,
                                       deactivate_callback=self.__deactivate_processing)
        self._service2 = ServiceWorker(name=s2_name, service_number=SentBy.s2, set_id_type=self._s2_id_type,
                                       upload_que=self._s2_que, new_access_callback=self.__new_access_from_service2,
                                       deactivate_callback=self.__deactivate_processing)
        self.__db = SQLSession(file_name=self._name, init=True, debug=debug, s1_id_type=self._s1_id_type,
                               s2_id_type=self._s2_id_type)

    @property
    def name(self):
        return self._name

    @property
    def uid(self):
        return self._uid

    @property
    def get_worker1(self) -> ServiceWorker:
        return self._service1

    @property
    def get_worker2(self) -> ServiceWorker:
        return self._service2

    def run(self):
        self._service1.run()
        self._service2.run()
        self.__message_broker()

    async def blocking_run(self):
        if self._service1.is_running():
            await self._service1.tasks[0]
        if self._service2.is_running():
            await self._service2.tasks[0]
        return

    def get_uid_from_service_id(self, sent_by: SentBy, service_id) -> UUID:
        # service_id は型が決まっていない．全て，DBにアクセスする際は，str型にする
        if sent_by == SentBy.s1:
            uid: UUID | None = self._service1.get_uid_from_service_id(service_id)
        elif sent_by == SentBy.s2:
            uid: UUID | None = self._service2.get_uid_from_service_id(service_id)
        else:
            raise TypeError(f"get_uid_from_service_id: doesn't match the type {type(sent_by)} of `sent_by`")
        return uid

    def __new_access_from_service1(self, service1_id, create_client_if_no_exist=True,
                                   queue_in_previous_message=False) -> ChatClient:
        sent_by = SentBy.s1
        cc = await self.__new_access_processing(sent_by, service1_id, create_client_if_no_exist)
        return cc

    def __new_access_from_service2(self, service2_id, create_client_if_no_exist=True) -> ChatClient:
        sent_by = SentBy.s2
        cc = await self.__new_access_processing(sent_by, service2_id, create_client_if_no_exist)
        return cc

    # This function is called __new_access_service1 or __new_access_service2
    async def __new_access_processing(self, sent_by: SentBy, service_id, create_client_if_no_exist) -> ChatClient:
        cc: ChatClient | None = self.__db.get_chat_client(sent_by, service_id)
        if cc is None and create_client_if_no_exist:
            cc = await self.create_new_client(sent_by, service_id)

        return cc

    def __deactivate_processing(self, cc: ChatClient, sent_by: SentBy):
        if sent_by == SentBy.s1:
            self._service2.deactivate_client(cc.s2_id, True)
        if sent_by == SentBy.s2:
            self._service1.deactivate_client(cc.s1_id, True)

    async def __message_broker(self):
        self.__task_broker1 = create_task(self.__broker_service1())
        self.__task_broker2 = create_task(self.__broker_service2())

    async def __broker_service1(self):
        while True:
            msg: Message = await self._s1_que.get()
            self.__db.commit_message(msg)
            await self._service2._rv_que.put(msg)

    async def __broker_service2(self):
        while True:
            msg: Message = await self._s2_que.get()
            self.__db.commit_message(msg)
            await self._service1._rv_que.put(msg)

    # deprecated
    # async def subscribe(self, client_id, client_queue):
    #     user_id = self.__db.get_user_id_from_client_id(client_id)
    #     if user_id is None:
    #         await self.create_new_client(client_id)
    #     else:
    #         self.create_exist_client(client_queue)

    async def create_new_client(self, sent_by: SentBy, service_id) -> ChatClient:
        """

        Args:
            sent_by:
            service_id:

        Returns:

        """
        if sent_by == SentBy.s1:
            service2_id = await run_as_await_func(self._service2.new_access_callback_from_other_worker, service_id)
            cc = ChatClient(s1_id=service_id, s2_id=service2_id)
            self.__db.add_new_client(cc)
        elif sent_by == SentBy.s2:
            service1_id = await run_as_await_func(self._service1.new_access_callback_from_other_worker, service_id)
            cc = ChatClient(s1_id=service1_id, s2_id=service_id)
            self.__db.add_new_client(cc)
        else:
            raise AttributeError()
        return cc

    # async def create_new_client(self, client_id, client_queue):
    #     """
    #     subscribe new ChatClient to Chatbox._active
    #     Returns:
    #         UUID: new ChatClient client_id
    #     """
    #     channel_id = await self.create_new_channel(client_id)
    #     client = ChatClient(self.session, client_id, channel_id, client_queue)
    #     self._active_client_ids[client.client_id] = client
    #     self._active_server_ids[client.server_id] = client
    #     return client.client_id
