import logging
from asyncio import Queue, create_task
from typing import Any, Callable, Coroutine
from uuid import UUID, uuid4

from chatbox50._utils import Immutable, ImmutableType, run_as_await_func
from chatbox50.message import Message, SentBy
from chatbox50.chat_client import ChatClient


class ServiceWorker:
    def __init__(self,
                 name: str,
                 service_number: SentBy,
                 set_id_type: ImmutableType,
                 upload_que: Queue,
                 new_access_callback: Callable[[Immutable, ...], Coroutine[Any, Any, ChatClient]],
                 deactivate_callback: Callable[[ChatClient, SentBy], None],
                 logger: logging.Logger
                 ):
        self._name = name
        self.__service_number = service_number
        self._id_type = set_id_type  # Noneが入る可能性があります．
        self.__upload_que = upload_que
        self.__new_access_callback_to_cb = new_access_callback
        self.__deactivate_callback = deactivate_callback
        self.__logger = logger.getChild(name)
        self._rv_que: Queue[Message] = Queue()
        self._sd_que: Queue[Message] = Queue()
        self._receive_msg_que: Queue[Message] = Queue()
        self._access_callback = None
        self._create_callback = None
        self._received_message_callback = None
        self._active_ids: dict[Immutable, ChatClient] = dict()
        self._queue_dict: dict[Immutable, Queue] = dict()
        self.tasks = None

    def __setitem__(self, key, value):
        if not isinstance(key, ChatClient):
            raise TypeError(f"key must be `ChatClient` not `{type(key)}`")
        if not isinstance(value, Message):
            raise TypeError(f"value must be `Message` not `{type(value)}`")

        if key in self._active_ids:
            self._sd_que.put_nowait(value)
            return
        else:
            raise KeyError(f"{self._name}: uid:{key.uid} didn't find in active_uid.")

    def run(self) -> None:
        # coroutine task
        self.tasks = [create_task(self.__send_task(), name="send_task"),
                      create_task(self.__receive_task(), name="receive_task")]

    def is_running(self) -> bool:
        if self.tasks is None:
            return False
        for task in self.tasks:
            if task.done():
                return False
        return True

    async def __send_task(self):  # _sd_que -> ServiceWorker -> upload_que -> ChatBox
        while True:
            msg: Message = await self._sd_que.get()
            await self.__upload_que.put(msg)

    async def __receive_task(self):  # _rv_queue -> ServiceWorker -> _receive_msg_que
        while True:
            msg: Message = await self._rv_que.get()
            # ** it's not error TODO: 自分のメッセージも受け取るかを選択できるようにする
            # if msg.sent_by == self.__service_number:
            #     raise TypeError(f"MessageSentByAutherError: This is service `{self.__service_number.name}` \n"
            #                     f"but the message is also sent by the same service.\n"
            #                     f"content: {msg.content}\n created at: {msg.created_at}")
            client: ChatClient = self._active_ids.get(msg.get_id(self.__service_number))
            if client is not None:
                # If the client is active.
                client.add_message(msg)
                await run_as_await_func(self._received_message_callback, msg)
                client_queue: Queue = self._queue_dict.get(msg.get_id(self.__service_number))
                await client_queue.put(msg)
                await self._receive_msg_que.put(msg)
            else:
                # TODO:If the client isn't active,
                pass

    @property
    def receive_queue(self) -> Queue[Message]:
        return self._receive_msg_que

    @property
    def send_queue(self) -> Queue[Message]:
        return self._sd_que

    @property
    def create_callback_from_other_worker(self):
        return self._create_callback

    @property
    def access_callback_from_other_worker(self) -> Callable[[ChatClient], Coroutine[Any, Any, None]]:
        async def __access_func(cc: ChatClient):
            service_id = self.__active_client(cc)
            await run_as_await_func(self._access_callback, service_id)

        return __access_func

    def set_new_access_callback(self, callback: Callable[[Immutable], ...]) -> None:
        """
        このコールバックは，他のServiceWorkerからの既存のクライアントのアクセスの際に呼び出されます．
        新規クライアントの場合でも，create_callbackの後に呼び出されます．
        Args:
            callback: this callback doesn't have any arguments. it must return this new service id.

        Returns:

        """
        self._access_callback = callback

    def set_create_callback(self, callback: Callable[[Immutable], Immutable] | Callable[[Immutable], Coroutine[Any,
    Any, Immutable]]):
        """
        このコールバックは，他のServiceWorkerからの新規クライアントの作成の際に呼び出されます．
        Args:
            callback: コールバックは，必ずservice_idと同じ型を返す必要があります．
        """
        self._create_callback = callback

    def set_received_message_callback(self, callback: Callable[[Message], None]):
        self._received_message_callback = callback

    async def access_new_client(self, service_id: Immutable = None, create_client_if_no_exist=True) -> Immutable:
        """
        New Access 1st steep
        Args:
            service_id: ChatBox.s?_id_typeが設定されている場合は同じ型かつユニークである必要があります．
                        設定されていないかつ，Noneの場合はUUIDが自動で生成されます．
            create_client_if_no_exist:
                True: データベースに同じIDが見つからなかった場合，新規作成します．
                False: エラーログを出力し，None を返します．

        Returns:

        """
        if service_id is None and self._id_type == UUID:
            service_id = uuid4()
        else:
            if not isinstance(service_id, self._id_type):
                raise TypeError(f"{self._name}.access_new_client: service_id must be `{type(self._id_type)}` not `"
                                f"{type(service_id)}`")
        cc: ChatClient = await self.__new_access_callback_to_cb(service_id, create_client_if_no_exist)
        self.__active_client(cc)
        return service_id

    def __active_client(self, cc: ChatClient) -> Immutable:
        if self.__service_number == SentBy.s1:
            service_id = cc.s1_id
        else:
            service_id = cc.s2_id
        self._active_ids[service_id] = cc
        self._queue_dict[service_id] = Queue()
        return service_id

    def deactivate_client(self, service_id: Immutable, called_by_chat_box=False):
        cc = self._active_ids.pop(service_id)
        self._queue_dict.pop(service_id)
        if not called_by_chat_box:
            self.__deactivate_callback(cc, self.__service_number)

    def get_msg_sender(self, service_id: Immutable) -> Callable[[str], Coroutine[Any, Any, None]]:
        """
        get message receiver function which is available to send str message to chatbox.
        Args:
            service_id:

        Returns:

        """

        async def _msg_sender(content: str) -> None:
            client = self._active_ids.get(service_id)
            msg = Message(client, self.__service_number, content)
            await self._sd_que.put(msg)

        return _msg_sender

    def get_uid_from_service_id(self, service_id: Immutable) -> UUID | None:
        cc = self._active_ids.get(service_id)
        if cc is None:
            return None
        return cc.uid

    def get_client_queue(self, service_id: Immutable) -> Queue | None:
        return self._queue_dict.get(service_id)
