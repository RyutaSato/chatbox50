from asyncio import Queue, create_task
from uuid import UUID, uuid4
from chatbox50.db_session import SQLSession
from chatbox50.chat_client import ChatClient
from chatbox50.service_worker import ServiceWorker
from chatbox50.message import Message, SentBy
import logging

logger = logging.getLogger(__name__)


class Chatbox:
    def __init__(self,
                 name: str = "chatbox50",
                 s1_name: str = "server_1",
                 s2_name: str = "server_2",
                 # デフォルトのQueueに追加されるメッセージの型を指定します
                 set_user_type=ChatClient,
                 set_message_type=Message,
                 debug=False):
        """
        **** 全て文字列で管理 ****

        Args:
            name:
            s1_name:
            s2_name:
            set_user_type:
            set_message_type:
            debug:
        """
        self._name = name
        self._uid = uuid4()
        self._s1_que = Queue()
        self._s2_que = Queue()
        self._service1 = ServiceWorker(name=s1_name,
                                       set_user_type=set_user_type,
                                       set_message_type=set_message_type,
                                       set_service_number=SentBy.s1,
                                       upload_que=self._s1_que
                                       )
        self._service2 = ServiceWorker(name=s2_name,
                                       set_user_type=set_user_type,
                                       set_message_type=set_message_type,
                                       set_service_number=SentBy.s2,
                                       upload_que=self._s2_que
                                       )

    @property
    def name(self):
        return self._name

    @property
    def uid(self):
        return self._uid

    @property
    def service1(self):
        return self._service1

    @property
    def service2(self):
        return self._service2

    def run(self):
        self._service1.run()
        self._service2.run()

    async def blocking_run(self):
        if self._service1.is_running():
            await self._service1.tasks[0]
        if self._service2.is_running():
            await self._service2.tasks[0]
        return

    async def new_access_from_service1(self, uid, create_client_if_no_exist=True):
        client = await self.__new_access_processing(SentBy.s2, uid)
        return client

    async def new_access_from_service2(self, uid, create_client_if_no_exist=True):
        await self.__new_access_processing(SentBy.s2, uid)

    async def __new_access_processing(self, sent_by: SentBy, uid):
        # ChatClientを作成する．
        # ChatClientインスタンスに，メッセージ可能なコールバックを含める

        # ChatClientを返す
        pass

    async def subscribe(self, client_id, client_queue):
        user_id = self.session.get_user_id_from_client_id(client_id)
        if user_id is None:
            await self.create_new_client(client_id)
        else:
            self.create_exist_client(client_queue)

    async def create_new_client(self, client_id, client_queue):
        """
        subscribe new ChatClient to Chatbox._active
        Returns:
            UUID: new ChatClient client_id
        """
        channel_id = await self.create_new_channel(client_id)
        client = ChatClient(self.session, client_id, channel_id, client_queue)
        self._active_client_ids[client.client_id] = client
        self._active_server_ids[client.server_id] = client
        return client.client_id

    def create_exist_client(self, client_id):
        cc: ChatClient = self._active_client_ids.get(client_id)
        if cc is None:
            cc = ChatClient(self.session, client_id, cc)
        return cc

    def deactivate_client(self, uid: UUID):
        self._active_client_ids[uid].commit_to_db()
        del self._active_client_ids[uid]
