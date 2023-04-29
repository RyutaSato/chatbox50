import logging
from asyncio import Queue, Task, create_task, TaskGroup
from chatbox50.message import Message, SentBy
from chatbox50.chat_client import ChatClient

logger = logging.getLogger(__name__)


class ServiceWorker:
    def __init__(self,
                 name: str,
                 set_service_number: SentBy,
                 set_message_type,
                 set_user_type,
                 upload_que: Queue
                 ):
        self._name = name
        self.__service_number = set_service_number
        self._msg_type = set_message_type
        self._user_type = set_user_type
        self.__upload_que = upload_que
        self._rv_que: Queue[set_message_type] = Queue()
        self._sd_que: Queue[set_message_type] = Queue()
        self._access_callback = None
        self._create_callback = None
        self._received_message_awaitable_callback = None
        self._actives_ids: dict = dict()
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

        if key in self._actives_ids:
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
            client: ChatClient = self._actives_ids.get(msg.client_id)
            if client is not None:
                # If the client is active.
                client.add_message(msg)
                if self._received_message_awaitable_callback is None:
                    logger.info(f"the callback that called when service worker received message doesn't set."
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

    def set_access_callback(self, callback: callable):
        self._access_callback = callback

    def set_create_callback(self, callback: callable):
        self._create_callback = callback

    def set_received_message_callback(self, awaitable_callback: callable):
        self._received_message_awaitable_callback = awaitable_callback
