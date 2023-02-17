from datetime import datetime


class Message:
    def __init__(self, uid, content: str, created_at: datetime = datetime.utcnow()):
        self.uid = uid
        self.created_at = created_at
        self.content = content
