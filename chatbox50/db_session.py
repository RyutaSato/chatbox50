import sqlite3
import logging
from uuid import UUID
from datetime import datetime

from chatbox50.message import Message, SentBy
from chatbox50.chat_client import ChatClient

logger = logging.getLogger("session")
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'


class SQLSession:
    def __init__(self, file_name, s1_id_type, s2_id_type, init=False, debug=False):
        # if debug mode is True, sqlite works in memory.
        self._s1_id_type = s1_id_type
        self._s2_id_type = s2_id_type
        if debug:
            file_name = ":memory:"
        self.__conn = sqlite3.connect(file_name)
        if init:
            self.__init_db()

    def __call__(self, sql: str, *parameter):
        cur = self.__conn.cursor()
        cur.execute(sql, parameter)
        return cur.fetchall()

    def add_new_client(self, cc: ChatClient):
        """

        Args:
            cc:
        """
        cur = self.__conn.cursor()
        cur.execute(
            "INSERT INTO client (uid, service1_id, service2_id, properties) VALUES (?, ?, ?, ?)",
            (str(cc.uid), str(cc.s1_id), str(cc.s2_id), cc.pickle_properties())
        )
        self.__conn.commit()

    def get_chat_client(self, sent_by: SentBy, service_id) -> None | ChatClient:
        """
        ** COMPLETED **
        Args:
            sent_by:
            service_id:

        Returns:

        """
        cur = self.__conn.cursor()
        if sent_by == SentBy.s1:
            cur.execute("SELECT uid, service1_id, service2_id, properties FROM client WHERE service1_id = ?",
                        (service_id,))
        elif sent_by == SentBy.s2:
            cur.execute("SELECT id, uid, service1_id, service2_id, properties FROM client WHERE service2_id = ?",
                        (service_id,))
        else:
            raise AttributeError()
        client = cur.fetchone()
        client_id: str = client[0]
        cc: ChatClient = ChatClient(uid=UUID(client[1]), s1_id=self._s1_id_type(client[2]), s2_id=self._s2_id_type(
            client[3]))
        cur = self.__conn.cursor()
        cur.execute("SELECT sent_by, content, created_at FROM history WHERE client_id=?", (client_id,))
        message_count = 0
        for row in cur.fetchall():
            cc.add_message(Message(chat_client=cc, sent_by=SentBy(int(row[0])), content=row[1],
                                   created_at=datetime.strptime(row[2], DATETIME_FORMAT)))
            message_count += 1
        cc.number_of_saved_messages = message_count
        return cc

    def _get_client_id_from_uid(self, uid: UUID) -> str | None:
        cur = self.__conn.cursor()
        cur.execute("SELECT id FROM client WHERE uid=?", (str(uid),))
        client_id = cur.fetchone()[0]
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
        client_id = self._get_client_id_from_uid(messages[0].uid)
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
        client_id = self._get_client_id_from_uid(message.uid)
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

    def get_history_from_uid(self, cc: ChatClient):
        """
        ** COMPLETED **
        Args:
            cc:

        Returns:

        """
        client_id = self._get_client_id_from_uid(cc.uid)
        if client_id is None:
            logger.info("get_history_from_uid: can't get history die not to find client_id")
            return None
        cur = self.__conn.cursor()
        cur.execute("SELECT content, created_at, sent_by FROM history WHERE history.client_id=?", (client_id,))
        for row in cur.fetchall():
            cc.add_message(Message(chat_client=cc,
                                   content=row[0],
                                   created_at=datetime.strptime(row[1], DATETIME_FORMAT),
                                   sent_by=SentBy(row[2])))
        return None

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
