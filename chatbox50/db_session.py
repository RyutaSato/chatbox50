import sqlite3
import logging
from uuid import UUID
from datetime import datetime

from chatbox50 import Message, SentBy

logger = logging.getLogger("session")


class SQLSession:
    def __init__(self, file_name, init=False, debug=False):
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

    def add_new_client(self, client_id, server_id):
        cur = self.__conn.cursor()
        cur.execute("INSERT INTO user (client_id, server_id) VALUES (?, ?)", (str(client_id), str(server_id)))
        self.__conn.commit()

    def get_server_id(self, client_id):
        cur = self.__conn.cursor()
        cur.execute("SELECT server_id FROM user")
        return cur.fetchone()

    def get_client_uid(self):  #未修正
        cur = self.__conn.cursor()
        cur.execute("SELECT uid FROM client")
        return set(map(lambda x: UUID(x[0]), cur.fetchall()))

    def get_user_id_from_client_id(self, client_id) -> str | None:
        cur = self.__conn.cursor()
        cur.execute("SELECT id FROM user WHERE client_id=?", (str(client_id),))
        client_id = cur.fetchone()
        if client_id is None:
            logger.info(f"can't find uid: {client_id} from DB")
            return None
        return client_id[0]

    def commit_messages(self, client_id, messages: list[Message]):
        user_id = self.get_user_id_from_client_id(client_id)
        if user_id is None:
            logger.info(f"can't add messages due not to find user")
            return
        cur = self.__conn.cursor()
        cur.executemany("INSERT INTO history (user_id, created_at, content, sent_by) VALUES (?, ?, ?, ?)",
                        [(client_id, str(message.created_at), message.content, message.sent_by) for message in messages])
        self.__conn.commit()

    def get_history_from_client_id(self, client_id):
        histories: list[Message] = []
        user_id = self.get_user_id_from_client_id(client_id)
        if user_id is None:
            return None
        cur = self.__conn.cursor()
        cur.execute("SELECT content, created_at, sent_by FROM history WHERE history.user_id=?", (user_id,))
        for row in cur.fetchall():
            histories.append(Message(client_id=client_id,
                                     content=row[0],
                                     created_at=datetime.strptime(row[1], "%Y-%m-%d %H:%M:%S.%f"),
                                     sent_by=SentBy(row[2])))
        return histories

    def __init_db(self):
        cur = self.__conn.cursor()
        self.__conn.execute("PRAGMA foreign_keys = ON")
        cur.execute("CREATE TABLE IF NOT EXISTS user("
                    "id         INTEGER PRIMARY KEY AUTOINCREMENT, "
                    "created_at TEXT DEFAULT CURRENT_TIMESTAMP,"
                    "client_id  VARCHAR(40) NOT NULL,"
                    "server_id  VARCHAR(40) NOT NULL)")
        cur.execute("CREATE TABLE IF NOT EXISTS history("
                    "id         INTEGER PRIMARY KEY AUTOINCREMENT, "
                    "created_at TEXT DEFAULT CURRENT_TIMESTAMP,"
                    "user_id  INTEGER NOT NULL, "
                    "content    TEXT NOT NULL,"
                    "sent_by    INTEGER NOT NULL,"  # 0:client 1:server
                    "FOREIGN KEY (user_id) REFERENCES user(id))")
        cur.close()
        return

    def __del__(self):
        self.__conn.commit()
        self.__conn.close()


if __name__ == '__main__':
    session = SQLSession('', init=True, debug=True)
