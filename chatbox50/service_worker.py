import logging
from asyncio import Queue, Task, create_task, TaskGroup
from uuid import UUID, uuid4

from chatbox50.message import Message, SentBy
from chatbox50.chat_client import ChatClient

logger = logging.getLogger(__name__)


class ServiceWorker:
    def __init__(self,
                 name: str,
                 service_number: SentBy,
                 set_message_type,
                 set_user_type,
                 set_id_type,
                 upload_que: Queue,
                 new_access_callback_to_cb: callable,
                 ):
        self._name = name
        self.__service_number = service_number
        self._msg_type = set_message_type
        self._user_type = set_user_type
        self._id_type = set_id_type  # Noneが入る可能性があります．
        self.__upload_que = upload_que
        self.__new_access_callback_to_cb = new_access_callback_to_cb
        self._rv_que: Queue[set_message_type] = Queue()
        self._sd_que: Queue[set_message_type] = Queue()
        self._access_callback = None
        self._create_callback = None
        self._received_message_awaitable_callback = None
        self._active_ids: dict = dict()
        self.tasks = None

    # def __await__(self):
    #     if self.tasks is None:
    #         return
    #     yield from self.__await()
    #
    # async def __await(self):
    #     for task in self.tasks:
    #         await task
    #     return

    def __setattr__(self, key, value):
        if not isinstance(key, self._user_type):
            raise TypeError(f"key must be `{type(self._user_type)}` not `{type(key)}`")
        if not isinstance(value, self._msg_type):
            raise TypeError(f"value must be `{type(self._msg_type)}` not `{type(value)}`")

        if key in self._active_ids:
            self._sd_que.put_nowait(value)
            return
        else:
            raise KeyError(f"{self._name}: uid:{key.uid} didn't find in active_uid.")

    def run(self):
        # coroutine task
        self.tasks = [create_task(self.__send_task(), name="send_task"),
                      create_task(self.__receive_task(), name="receive_task")]

    def is_running(self):
        if self.tasks is None:
            return False
        for task in self.tasks:
            if task.done():
                return False
        return True

    async def __send_task(self):
        while True:
            msg = await self._sd_que.get()
            await self.__upload_que.put(msg)

    async def __receive_task(self):
        while True:
            msg: Message = await self._rv_que.get()
            if msg.sent_by == self.__service_number:
                raise TypeError(f"MessageSentByAutherError: This is service `{self.__service_number.name}` \n"
                                f"but the message is also sent by the same service.\n"
                                f"content: {msg.content}\n created at: {msg.created_at}")
            client: ChatClient = self._active_ids.get(msg.client_id)
            if client is not None:
                # If the client is active.
                client.add_message(msg)
                if self._received_message_awaitable_callback is None:
                    logger.info(f"the callback that called when the {self._name} service worker received message "
                                f"doesn't set."
                                f"That's why the process was skipped. "
                                f"If you want to solve it, set using `set_received_message_callback`")
                    continue
                await self._received_message_awaitable_callback(msg)
                continue
            else:
                # TODO:If the client isn't active,
                pass

        # client: ChatClient = self._actives_ids.get(key.uid)
        # if client is None:
        #     raise KeyError(f"{self._name}: uid:{key.uid} didn't find in active_uid.")
        # self.

        # cc: ChatClient | None = self._active_client_ids.get(key)
        # # if key is client_id
        # if cc is ChatClient:
        #     msg = Message(cc.client_id, SentBy.client, value)
        #     self._server_send_queue.put_nowait(msg)
        # else:
        #     cc: ChatClient | None = self._active_server_ids.get(key)
        #     if cc is None:
        #         raise KeyError(f"key must be active client_id or server_id")
        #     # if key is server_id
        #     msg = Message(cc.client_id, SentBy.server, value)
        #     cc.queue.put_nowait()

    @property
    def receive_queue(self):
        return self._rv_que

    @property
    def send_queue(self):
        return self._sd_que

    def set_accessed_callback(self, callback: callable):
        """

        Args:
            callback: 第1引数には，service_idが渡されます．型は，id_typeでセットされた型です．

        Returns:

        """
        self._access_callback = callback

    def set_created_callback(self, callback: callable):
        """

        Args:
            callback: コールバックは，必ずservice_idと同じ型を返す必要があります．
        """
        self._create_callback = callback

    def set_received_message_callback(self, awaitable_callback: callable):
        self._received_message_awaitable_callback = awaitable_callback

    def access_new_client(self, service_id=None, create_client_if_no_exist=True):
        """

        Args:
            service_id: ChatBox.s?_id_typeが設定されている場合は同じ型かつユニークである必要があります．
                        設定されていないかつ，Noneの場合はUUIDが自動で生成されます．
            create_client_if_no_exist:
                True: データベースに同じIDが見つからなかった場合，新規作成します．
                False: エラーログを出力し，None を返します．

        Returns:

        """
        if service_id is None:
            if self._id_type is None:
                service_id = uuid4()
            else:
                raise TypeError(f"{self._name}.access_new_client: service_id must be `{type(self._id_type)}` not None")
        else:
            if isinstance(service_id, self._id_type):
                pass
            else:
                raise TypeError(f"{self._name}.access_new_client: service_id must be `{type(self._id_type)}` not `"
                                f"{type(service_id)}`")
        cc: ChatClient = self.__new_access_callback_to_cb(service_id, create_client_if_no_exist=create_client_if_no_exist)
        self.__active_client(service_id, cc)
        return service_id


    def __active_client(self, service_id, chat_client: ChatClient):
        self._active_ids[service_id] = chat_client

    def deactivate_client(self, uid: UUID):
        del self._active_ids[uid]
