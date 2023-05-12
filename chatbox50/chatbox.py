import asyncio
import json
from asyncio import Queue, create_task
from uuid import UUID, uuid4

from chatbox50._utils import ImmutableType, run_as_await_func
from chatbox50.db_session import SQLSession
from chatbox50.chat_client import ChatClient
from chatbox50.service_worker import ServiceWorker
from chatbox50.message import Message, SentBy
import logging


class ChatBox:
    """
    "Chatbox50" will automatically pass messages between the two services and log them to the database.
    """

    def __init__(self,
                 name: str = "ChatBox50",
                 s1_name: str = "server_1",
                 s2_name: str = "server_2",
                 s1_id_type: ImmutableType = UUID,
                 s2_id_type: ImmutableType = UUID,
                 debug: bool = False,
                 logger: logging.Logger = None):
        """

        Args:
             name: Used for SQL file name. Also, if you have multiple ChatBoxes, you can use it as an identifier.
             Must be unique.
             s1_name: Can be used to identify the first service.
             s2_name: Can be used to identify the second service. Must not overlap with s1_name.
             s1_id_type(str, int, UUID, complex, float, bool, tuple, bytes):
             s2_id_type(str, int, UUID, complex, float, bool, tuple, bytes):
             debug: If True, SQLite files are not generated.

        Returns:
             object:
        Warnings:
            ChatBox50 is multi-threaded and runs in the same event loop as the main function.
            If you want to run in multiple processes, create an event loop in each process.
            Add the event loop to the `loop` argument of ChatBox50. `Queue` is not shared.
            As a way to solve that problem,
            you can connect `multiprocessing.Queue` with `Queue` of `chatbox50.ServiceWorker`.
        """
        self._name = name
        self._uid = uuid4()
        self._s1_que = Queue()
        self._s2_que = Queue()
        self._s1_id_type = s1_id_type
        self._s2_id_type = s2_id_type
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        if debug:
            handler = logging.FileHandler("chatbox50.log", mode='w+', encoding="utf-8", )
        else:
            handler = logging.NullHandler()
        handler.setFormatter(formatter)
        if logger is None:
            self.logger = logging.getLogger(name)
        else:
            self.logger = logger.getChild(name)
        self.logger.addHandler(handler)

        self._service1 = ServiceWorker(name=s1_name, service_number=SentBy.s1, set_id_type=self._s1_id_type,
                                       upload_que=self._s1_que, new_access_callback=self.__access_from_service1,
                                       deactivate_callback=self.__deactivate_processing, logger=self.logger)
        self._service2 = ServiceWorker(name=s2_name, service_number=SentBy.s2, set_id_type=self._s2_id_type,
                                       upload_que=self._s2_que, new_access_callback=self.__access_from_service2,
                                       deactivate_callback=self.__deactivate_processing, logger=self.logger)
        self.__db = SQLSession(file_name=self._name, init=True, debug=debug, s1_id_type=self._s1_id_type,
                               s2_id_type=self._s2_id_type, logger=self.logger)

    @property
    def name(self) -> str:
        return self._name

    @property
    def uid(self) -> UUID:
        return self._uid

    @property
    def get_worker1(self) -> ServiceWorker:
        return self._service1

    @property
    def get_worker2(self) -> ServiceWorker:
        return self._service2

    def run(self) -> None:
        self._service1.run()
        self._service2.run()
        self.__message_broker()

    def get_uid_from_service_id(self, sent_by: SentBy, service_id: ImmutableType) -> UUID:
        if sent_by == SentBy.s1:
            uid: UUID | None = self._service1.get_uid_from_service_id(service_id)
        elif sent_by == SentBy.s2:
            uid: UUID | None = self._service2.get_uid_from_service_id(service_id)
        else:
            raise TypeError(f"get_uid_from_service_id: doesn't match the type {type(sent_by)} of `sent_by`")
        return uid

    async def __access_from_service1(self, service1_id: ImmutableType, create_client_if_no_exist=True,
                                     queue_in_previous_message=False) -> ChatClient:
        #  New access 2nd step
        sent_by = SentBy.s1
        cc = await self.__access_processing(sent_by, service1_id, create_client_if_no_exist)
        await run_as_await_func(self._service2.access_callback_from_other_worker, cc)
        return cc

    async def __access_from_service2(self, service2_id: ImmutableType,
                                     create_client_if_no_exist=True) -> ChatClient:
        #  New access 2nd step
        sent_by = SentBy.s2
        cc = await self.__new_access_processing(sent_by, service2_id, create_client_if_no_exist)
        await run_as_await_func(self._service1.access_callback_from_other_worker, cc)
        return cc

    # This function is called __new_access_service1 or __new_access_service2
    async def __access_processing(self, sent_by: SentBy, service_id: ImmutableType, create_client_if_no_exist: bool) \
            -> ChatClient:
        # New access 3rd step
        cc: ChatClient | None = self.__db.get_chat_client(sent_by, service_id)
        if cc is None and create_client_if_no_exist:
            cc = await self.__create_new_client(sent_by, service_id)
        await asyncio.sleep(0)
        return cc

    def __deactivate_processing(self, cc: ChatClient, sent_by: SentBy):
        if sent_by == SentBy.s1:
            self._service2.deactivate_client(cc.s2_id, True)
        if sent_by == SentBy.s2:
            self._service1.deactivate_client(cc.s1_id, True)

    def __message_broker(self):
        self.__task_broker1 = create_task(self.__broker_service1())
        self.__task_broker2 = create_task(self.__broker_service2())

    async def __broker_service1(self):  # service1 upload _s1_que -> service2 _rv_que
        while True:
            msg: Message = await self._s1_que.get()
            self.logger.debug({"action": "receive", "object": "broker_s1", "content": msg.content})
            if self.__db.commit_message(msg):
                self.logger.debug({"action": "commit", "object": "broker_s1", "content": msg.content,
                                   "status": "success"})
            else:
                self.logger.debug({"action": "commit", "object": "broker_s1", "content": msg.content,
                                   "status": "success",
                                   "info": {"uid": str(msg.uid),
                                            "content": msg.content}.__str__()})
            await self._service1.rv_que.put(msg)
            await self._service2.rv_que.put(msg)

    async def __broker_service2(self):  # service2 upload _s2_que -> service1 _rv_que
        while True:
            msg: Message = await self._s2_que.get()
            self.logger.debug({"place": "broker_s2", "action": "receive", "status": "success"})
            if self.__db.commit_message(msg):
                self.logger.debug({"place": "broker_s2", "action": "commit", "status": "success"})
            else:
                self.logger.error({"place": "broker_s2", "action": "commit", "status": "error",
                                   "info": {"uid": str(msg.uid),
                                            "content": msg.content}.__str__()})
            await self._service1.rv_que.put(msg)
            await self._service2.rv_que.put(msg)
            self.__db.commit_message(msg)
            await self._service1._rv_que.put(msg)

    # deprecated
    # async def subscribe(self, client_id, client_queue):
    #     user_id = self.__db.get_user_id_from_client_id(client_id)
    #     if user_id is None:
    #         await self.create_new_client(client_id)
    #     else:
    #         self.create_exist_client(client_queue)

    async def __create_new_client(self, sent_by: SentBy, service_id: ImmutableType) -> ChatClient:
        """

        Args:
            sent_by:
            service_id:

        Returns:

        """
        if sent_by == SentBy.s1:
            service2_id = await run_as_await_func(self._service2.create_callback_from_other_worker, service_id,
                                                  raise_error=True)
            service1_id = service_id
        elif sent_by == SentBy.s2:
            service1_id = await run_as_await_func(self._service1.create_callback_from_other_worker, service_id,
                                                  raise_error=True)
            service2_id = service_id
        else:
            raise AttributeError()
        return cc
