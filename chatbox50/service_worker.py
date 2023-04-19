from asyncio import Queue
from chatbox50.message import Message
from chatbox50.chat_client import ChatClient


class ServiceWorker:
    def __init__(self,
                 name: str,
                 set_message_type,
                 set_user_type,
                 ):
        self._name = name
        self._msg_type = set_message_type
        self._user_type = set_user_type
        self._rv_que: Queue[set_message_type] = Queue()
        self._sd_que: Queue[set_message_type] = Queue()
        self._access_callback = None
        self._create_callback = None
        self._actives_ids: dict = dict()

    def __setattr__(self, key, value):
        if not isinstance(key, self._user_type):
            raise TypeError(f"key must be `{type(self._user_type)}` not `{type(key)}`")
        if not isinstance(value, self._msg_type):
            raise TypeError(f"value must be `{type(self._msg_type)}` not `{type(value)}`")
        client = self._actives_ids.get(key.uid)
        if client is None:
            raise KeyError(f"{self._name}: uid:{key.uid} didn't find in active_uid.")



        cc: ChatClient | None = self._active_client_ids.get(key)
        # if key is client_id
        if cc is ChatClient:
            msg = Message(cc.client_id, SentBy.client, value)
            self._server_send_queue.put_nowait(msg)
        else:
            cc: ChatClient | None = self._active_server_ids.get(key)
            if cc is None:
                raise KeyError(f"key must be active client_id or server_id")
            # if key is server_id
            msg = Message(cc.client_id, SentBy.server, value)
            cc.queue.put_nowait()
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
