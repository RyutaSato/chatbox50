import sqlite3
import logging
from uuid import UUID
from datetime import datetime

from chatbox50 import Message

logger = logging.getLogger("session")


class SQLSession:
    def __init__(self, file_name, init=False, debug=False):
        file_name += ".db"
        # if debug mode is True, sqlite works in memory.
        if debug:
            self.file_name = ":memory:"
        self.__conn = sqlite3.connect(file_name)
        if init:
            self.__init_db()

    def __call__(self, sql: str, *parameter):
        cur = self.__conn.cursor()
        cur.execute(sql, parameter)
        return cur.fetchall()

    def add_new_client(self, uid: UUID):
        cur = self.__conn.cursor()
        cur.execute("INSERT INTO client (uid) VALUES (?)", (str(uid),))
        self.__conn.commit()

    def get_or_add_new_client_id(self, uid: UUID) -> int:
        """ uidがDB上に存在するとき，DB上のprimary keyであるidを返します．
        存在しない場合は，そのuidを追加し，idを返します．

        Args:
            uid:

        Returns:

        """
        client_db_id = self.get_client_id(uid)
        if client_db_id is None:
            self.add_new_client(uid)
            client_db_id = self.get_client_id(uid)
        return client_db_id

    def get_client_all_uid(self):
        cur = self.__conn.cursor()
        cur.execute("SELECT uid FROM client")
        return set(map(lambda x: UUID(x[0]), cur.fetchall()))

    def get_client_id(self, uid: UUID):
        cur = self.__conn.cursor()
        cur.execute("SELECT id FROM client WHERE uid=?", (str(uid),))
        client_id = cur.fetchone()
        if client_id is None:
            logger.info(f"can't find uid: {uid} from DB")
            return None
        return int(client_id[0])

    def add_messages(self, uid: UUID, messages: list[Message]):
        print(f"db_session: uid:{uid} messages: {messages}")
        client_id = self.get_client_id(uid)
        print(f"db_session: uid:{uid} client_id:{client_id} messages: {messages}")
        if client_id is None:
            logger.info(f"can't add messages due not to find client")
            return
        cur = self.__conn.cursor()
        cur.executemany("INSERT INTO history (client_id, created_at, content, created_at) VALUES (?, ?, ?, ?)",
                        [(client_id, str(message.created_at), message.content, message.created_at) for message in messages])
        self.__conn.commit()

    def get_history(self, client_uid: UUID):
        histories: list[Message] = []
        client_id = self.get_client_id(client_uid)
        if client_id is None:
            return None
        cur = self.__conn.cursor()
        cur.execute("SELECT content, created_at FROM history WHERE history.client_id=?", (str(client_id),))
        for content, created_at in cur.fetchall():
            histories.append(Message(uid=client_uid,
                                     content=content,
                                     created_at=datetime.strptime(created_at, 'YYYY-MM-DD hh:mm:ss.ffffff')))
        return histories

    def __init_db(self):
        cur = self.__conn.cursor()
        self.__conn.execute("PRAGMA foreign_keys = ON")
        cur.execute("CREATE TABLE IF NOT EXISTS client("
                    "id         INTEGER PRIMARY KEY AUTOINCREMENT, "
                    "created_at TEXT DEFAULT CURRENT_TIMESTAMP,"
                    "uid        VARCHAR(40) NOT NULL)")
        cur.execute("CREATE TABLE IF NOT EXISTS history("
                    "id         INTEGER PRIMARY KEY AUTOINCREMENT, "
                    "created_at TEXT DEFAULT CURRENT_TIMESTAMP,"
                    "client_id  INTEGER NOT NULL, "
                    "content    TEXT NOT NULL,"
                    "FOREIGN KEY (client_id) REFERENCES client(id))")
        cur.close()
        return

    def __del__(self):
        self.__conn.commit()
        self.__conn.close()


if __name__ == '__main__':
    session = SQLSession('', init=True, debug=True)
