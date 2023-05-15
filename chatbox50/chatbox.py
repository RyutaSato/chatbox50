import asyncio
import json
from asyncio import CancelledError, Queue, Task, create_task
from uuid import UUID, uuid4

from chatbox50._utils import ImmutableType, run_as_await_func, get_logger_with_nullhandler
from chatbox50.db_session import SQLSession
from chatbox50.connection import Connection
from chatbox50.service_worker import ServiceWorker
from chatbox50.message import Message, SentBy
import logging

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


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
                 _logger: logging.Logger = None):
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
        if _logger is None:
            _logger = get_logger_with_nullhandler(self._name)
        global logger
        logger = _logger.getChild(name)

        self._service1 = ServiceWorker(name=s1_name, service_number=SentBy.s1, set_id_type=self._s1_id_type,
                                       upload_que=self._s1_que, new_access_callback=self.__access_from_service1,
                                       deactivate_callback=self.__deactivate_processing, _logger=logger)
        self._service2 = ServiceWorker(name=s2_name, service_number=SentBy.s2, set_id_type=self._s2_id_type,
                                       upload_que=self._s2_que, new_access_callback=self.__access_from_service2,
                                       deactivate_callback=self.__deactivate_processing, _logger=logger)
        self.__db = SQLSession(file_name=self._name, init=True, debug=debug, s1_id_type=self._s1_id_type,
                               s2_id_type=self._s2_id_type, logger=logger)

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

    def __dict__(self):
        return json.dumps({"place": self.name})

    def run(self) -> list[Task]:
        tasks = []
        logger.info({"place": "cc_run", "action": "task_start", "object": "service1"})
        tasks.extend(self._service1.run())
        logger.info({"place": "cc_run", "action": "task_start", "object": "service2"})
        tasks.extend(self._service2.run())
        logger.info({"place": "cc_run", "action": "task_start", "object": "broker"})
        tasks.extend(self.__message_broker())
        return tasks

    def get_uid_from_service_id(self, sent_by: SentBy, service_id: ImmutableType) -> UUID:
        if sent_by == SentBy.s1:
            uid: UUID | None = self._service1.get_uid_from_service_id(service_id)
        elif sent_by == SentBy.s2:
            uid: UUID | None = self._service2.get_uid_from_service_id(service_id)
        else:
            raise TypeError(f"get_uid_from_service_id: doesn't match the type {type(sent_by)} of `sent_by`")
        return uid

    async def __access_from_service1(self, service1_id: ImmutableType, create_client_if_no_exist=True,
                                     queue_in_previous_message=False) -> Connection:
        #  New access 2nd step
        sent_by = SentBy.s1
        cc = await self.__access_processing(sent_by, service1_id, create_client_if_no_exist)
        await run_as_await_func(self._service2.access_callback_from_other_worker, cc)
        return cc

    async def __access_from_service2(self, service2_id: ImmutableType,
                                     create_client_if_no_exist=True) -> Connection:
        #  New access 2nd step
        sent_by = SentBy.s2
        cc = await self.__access_processing(sent_by, service2_id, create_client_if_no_exist)
        await run_as_await_func(self._service1.access_callback_from_other_worker, cc)
        return cc

    # This function is called __new_access_service1 or __new_access_service2
    async def __access_processing(self, sent_by: SentBy, service_id: ImmutableType, create_client_if_no_exist: bool) \
            -> Connection:
        # New access 3rd step
        cc: Connection | None = self.__db.get_connection(sent_by, service_id)
        if cc is None and create_client_if_no_exist:
            cc = await self.__create_new_client(sent_by, service_id)
        await asyncio.sleep(0)
        return cc

    def __deactivate_processing(self, cc: Connection, sent_by: SentBy):
        if sent_by == SentBy.s1:
            self._service2.deactivate_client(cc.s2_id, True)
        if sent_by == SentBy.s2:
            self._service1.deactivate_client(cc.s1_id, True)

    def __message_broker(self):
        logger.info({"action": "task_start", "object": "broker_s1"})
        self.__task_broker1 = create_task(self.__broker_service1(), name="broker_service1")
        logger.info({"action": "task_start", "object": "broker_s2"})
        self.__task_broker2 = create_task(self.__broker_service2(), name="broker_service2")
        return [self.__task_broker1, self.__task_broker2]

    async def __broker_service1(self):  # service1 upload _s1_que -> service2 _rv_que
        try:
            logger.debug({"action": "start", "object": "broker_s1"})
            while True:
                msg: Message = await self._s1_que.get()
                logger.debug({"action": "receive", "object": "broker_s1", "content": msg.content})
                if self.__db.commit_message(msg):
                    logger.debug({"action": "commit", "object": "broker_s1", "content": msg.content,
                                  "status": "success"})
                else:
                    logger.debug({"action": "commit", "object": "broker_s1", "content": msg.content,
                                  "status": "success",
                                  "info": {"uid": str(msg.uid),
                                           "content": msg.content}.__str__()})
                await self._service1.rv_que.put(msg)
                await self._service2.rv_que.put(msg)
        except CancelledError:
            return

    async def __broker_service2(self):  # service2 upload _s2_que -> service1 _rv_que
        try:
            logger.debug({"place": "broker_s2", "action": "start"})
            while True:
                msg: Message = await self._s2_que.get()
                logger.debug({"place": "broker_s2", "action": "receive", "status": "success"})
                if self.__db.commit_message(msg):
                    logger.debug({"place": "broker_s2", "action": "commit", "status": "success"})
                else:
                    logger.error({"place": "broker_s2", "action": "commit", "status": "error",
                                  "info": {"uid": str(msg.uid),
                                           "content": msg.content}.__str__()})
                await self._service1.rv_que.put(msg)
                await self._service2.rv_que.put(msg)
                self.__db.commit_message(msg)
                await self._service1._rv_que.put(msg)
        except CancelledError:
            return

    # deprecated
    # async def subscribe(self, client_id, client_queue):
    #     user_id = self.__db.get_user_id_from_client_id(client_id)
    #     if user_id is None:
    #         await self.create_new_client(client_id)
    #     else:
    #         self.create_exist_client(client_queue)

    async def __create_new_client(self, sent_by: SentBy, service_id: ImmutableType) -> Connection:
        """
        New access 4th step
        Args:
            sent_by:
            service_id:

        Returns:

        """
        log_dict = {"place": "cc_create_new_client", "action": "create", "status": "start",
                    "sent_by": sent_by, "service_id": str(service_id)}
        logger.debug(log_dict)
        log_dict["action"] = "callback"
        if sent_by == SentBy.s1:
            log_dict["object"] = "s2_create_callback_from_other_worker"
            logger.debug(log_dict)
            service2_id = await run_as_await_func(self._service2.create_callback_from_other_worker, service_id,
                                                  raise_error=True)
            service1_id = service_id
        elif sent_by == SentBy.s2:
            log_dict["object"] = "s1_create_callback_from_other_worker"
            logger.debug(log_dict)
            service1_id = await run_as_await_func(self._service1.create_callback_from_other_worker, service_id,
                                                  raise_error=True)
            service2_id = service_id
        else:
            log_dict["status"] = "error"
            logger.critical(log_dict)
            raise AttributeError()
        log_dict["status"] = "success"
        log_dict["service1_id"], log_dict["service2_id"] = service1_id, service2_id
        logger.debug(log_dict)
        cc = Connection(s1_id=service1_id, s2_id=service2_id)
        self.__db.add_new_connection(cc)

        return cc
