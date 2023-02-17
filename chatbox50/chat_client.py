from uuid import UUID, uuid4
from chatbox50.db_session import SQLSession
from chatbox50.message import Message
import logging

logger = logging.getLogger("client")


class ChatClient:
    def __init__(self, session: SQLSession, uid: UUID | None = None):
        self.__session = session
        self.__messages: list[Message] = []
        self.__msg_num = 0
        if isinstance(uid, UUID):
            self.uid = uid
            if self.__get_history():  # if success
                self.__msg_num = len(self.__messages)
                return
            else:
                logger.info("otherwise, new client was created.")
        # if uid is wrong or None, create new client uid and add to DB
        self.uid = uuid4()
        self.__add_client()

    @property
    def messages(self):
        return self.__messages

    def add_message(self, content: Message | str):
        if isinstance(content, Message):
            self.__messages.append(content)
        elif isinstance(content, str):
            self.__messages.append(Message(content=content))
        else:
            raise ValueError(f"`value` must be `Message` or `str`, not {type(content)}")

    def commit_to_db(self):
        self.__session.add_messages(self.uid, messages=self.__messages[self.__msg_num:])

    def __get_history(self):
        histories: list | None = self.__session.get_history(client_uid=self.uid)
        if histories is None:
            logger.info(f"cancelled to get history from DB due not to find uid: {self.uid}")
            return False
        self.__messages.extend(histories)
        return True

    def __add_client(self):
        self.__session.add_client(self.uid)
