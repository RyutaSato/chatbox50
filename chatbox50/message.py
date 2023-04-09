from datetime import datetime
from uuid import UUID


class Message:
    def __init__(self, uid: UUID | None, content: str, created_at: datetime = datetime.utcnow()):
        # if uid is None -> Message auther is Provider
        self.uid = uid
        self.created_at = created_at
        self.content = content

    def __str__(self):
        return f"{self.content}"
