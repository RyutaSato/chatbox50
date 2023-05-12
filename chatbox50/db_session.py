import sqlite3
import logging
from uuid import UUID
from datetime import datetime

from chatbox50._utils import Immutable, str_converter
from chatbox50.message import Message, SentBy
from chatbox50.chat_client import ChatClient

logger = logging.getLogger("session")
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'


class SQLSession:
    def __init__(self, file_name: str, s1_id_type: ImmutableType, s2_id_type: ImmutableType, init: bool = False,
                 debug: bool = False, logger: logging.Logger = None):
        self._logger = logger if logger is None else logger.getChild("sql")
        self._s1_id_type = s1_id_type
        self._s2_id_type = s2_id_type
        # if debug mode is True, sqlite works in memory.
        self.__conn = sqlite3.connect(file_name + ".db" if not debug else ":memory:")
        if init:
            self.__init_db()

    def __call__(self, sql: str, *parameter):
        cur = self.__conn.cursor()
        cur.execute(sql, parameter)
        return cur.fetchall()

    def add_new_client(self, cc: ChatClient) -> bool:
        """

        Args:
            cc:
        """
        self._logger.debug({"place": "db_new_client", "action": "insert", "status": "start", "info": cc.__dict__()})
        cur = self.__conn.cursor()
        str_uid = str_converter(cc.uid)
        str_s1 = str_converter(cc.s1_id)
        str_s2 = str_converter(cc.s2_id)
        cur.execute(
            "INSERT INTO client (uid, service1_id, service2_id, properties) VALUES (?, ?, ?, ?)",
            (str_uid, str_s1, str_s2, cc.pickle_properties())
            # TODO: chatclient might be updated.
        )
        self.__conn.commit()

    def get_chat_client(self, sent_by: SentBy, service_id: Immutable) -> None | ChatClient:
        """
        ** COMPLETED **
        Args:
            sent_by:
            service_id:

        Returns:

        """
        service_id = str_converter(service_id)
        cur = self.__conn.cursor()
        if sent_by == SentBy.s1:
            cur.execute("SELECT id, uid, service1_id, service2_id, properties FROM client WHERE service1_id = ?",
                        (service_id,))
        elif sent_by == SentBy.s2:
            cur.execute("SELECT id, uid, service1_id, service2_id, properties FROM client WHERE service2_id = ?",
                        (service_id,))
        else:
            raise AttributeError()

        client = cur.fetchone()
        if client is None:
            log_dict["status"] = "not_found"
            log_dict["msg"] = "can't find cc from db. returned None"
            self._logger.debug(json.dumps(log_dict))
            return None
        cc: ChatClient = ChatClient(uid=UUID(client[1]), s1_id=self._s1_id_type(client[2]), s2_id=self._s2_id_type(
            client[3]))
        log_dict["status"] = "success"
        log_dict["info"]["result"] = str(client)
        self._logger.debug(json.dumps(log_dict))
        self.insert_history_to_chat_client(cc)
        # client_id: str = client[0]
        # cur = self.__conn.cursor()
        # cur.execute("SELECT sent_by, content, created_at FROM history WHERE client_id=?", (client_id,))
        # message_count = 0
        # for row in cur.fetchall():
        #     cc.add_message(Message(chat_client=cc, sent_by=SentBy(int(row[0])), content=row[1],
        #                            created_at=datetime.strptime(row[2], DATETIME_FORMAT)))
        #     message_count += 1
        # cc.number_of_saved_messages = message_count
        return cc

    @cache
    def _get_client_id_from_uid(self, uid: UUID) -> str | None:
        uid = str_converter(uid)
        self._logger.debug({"action": "get_client_id_from_uid", "uid": uid})
        cur = self.__conn.cursor()
        cur.execute("SELECT id FROM client WHERE uid=?", (uid,))
        client_id: tuple | None = cur.fetchone()
        if client_id is None:
            logger.error(f"_get_client_id_from_uid: can't find uid: {client_id} from DB")
            return None
        return client_id

    def commit_messages(self, messages: list[Message]) -> bool:
        """
        メッセージは随時DBに保存するように変更します．この関数は使いません．
        ** DEPRECATED **
        ** COMPLETED **
        Args:
            messages:

        Returns: bool

        """
        client_id: str | None = self._get_client_id_from_uid(messages[0].uid)
        if client_id is None:
            logger.info(f"commit_messages: can't add messages due not to find client_id")
            return False
        cur = self.__conn.cursor()
        cur.executemany("INSERT INTO history (client_id, created_at, content, sent_by) VALUES (?, ?, ?, ?)",
                        [(client_id,
                          str(message.created_at.strftime(DATETIME_FORMAT)),
                          message.content,
                          message.sent_by) for message in messages])
        self.__conn.commit()
        return True

    def commit_message(self, message: Message) -> bool:
        """
        ** COMPLETED **
        Args:
            message:

        Returns:

        """
        client_id: str | None = self._get_client_id_from_uid(message.uid)
        if client_id is None:
            logger.info(f"commit_messages: can't add messages due not to find client_id")
            return False
        cur = self.__conn.cursor()
        cur.execute("INSERT INTO history (client_id, created_at, content, sent_by) VALUES (?, ?, ?, ?)",
                    (client_id,
                     str(message.created_at.strftime(DATETIME_FORMAT)),
                     message.content,
                     message.sent_by))
        self.__conn.commit()
        return True

    def insert_history_to_chat_client(self, cc: ChatClient) -> bool:
        """
        ** COMPLETED **
        Args:
            cc:

        Returns:

        """
        client_id: str | None = self._get_client_id_from_uid(cc.uid)
        if client_id is None:
            logger.info("get_history_from_uid: can't get history die not to find client_id")
            return None
        cur = self.__conn.cursor()
        cur.execute("SELECT content, created_at, sent_by FROM history WHERE history.client_id=?", (client_id,))
        count = 0
        for row in cur.fetchall():
            cc.add_message(Message(chat_client=cc,
                                   content=row[0],
                                   created_at=datetime.strptime(row[1], DATETIME_FORMAT),
                                   sent_by=SentBy(int(row[2]))))
            count += 1
        cc.number_of_saved_messages = count
        return True

    def __init_db(self):
        cur = self.__conn.cursor()
        self.__conn.execute("PRAGMA foreign_keys = ON")
        cur.execute("CREATE TABLE IF NOT EXISTS client("
                    "id         INTEGER PRIMARY KEY AUTOINCREMENT, "
                    "created_at TEXT DEFAULT CURRENT_TIMESTAMP,"
                    "uid    VARCHAR(127) NOT NULL,"
                    "service1_id  VARCHAR(127) NOT NULL,"
                    "service2_id  VARCHAR(127) NOT NULL,"
                    "properties   BLOB NOT NULL)")
        cur.execute("CREATE TABLE IF NOT EXISTS history("
                    "id         INTEGER PRIMARY KEY AUTOINCREMENT, "
                    "created_at TEXT,"
                    "client_id  INTEGER NOT NULL, "
                    "content    TEXT NOT NULL,"
                    "sent_by    INTEGER NOT NULL,"  # 0:client 1:server
                    "FOREIGN KEY (client_id) REFERENCES client(id))")
        cur.close()
        return

    def __del__(self):
        self.__conn.commit()
        self.__conn.close()
