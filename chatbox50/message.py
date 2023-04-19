from datetime import datetime
from enum import IntEnum


class SentBy(IntEnum):
    s1 = 0
    s2 = 1


class Message:
    def __init__(self,
                 client_id,
                 sent_by: SentBy | int,
                 content: str,
                 created_at: datetime = datetime.utcnow()):
        self.client_id = client_id
        self.created_at = created_at
        self.content = content
        self.sent_by = sent_by

if __name__ == '__main__':
    a = SentBy.s1
    print(a.name)
