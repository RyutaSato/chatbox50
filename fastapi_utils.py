from asyncio import Queue
from uuid import UUID

from chatbox50 import Message

# the func should be replaced as class object in the future.

def get_message_classificator_and_message_callback():
    __que_dict: dict[UUID, Queue] = dict()
    __message_que: Queue[Message] = Queue()

    async def message_classificator(queue: Queue[Message]):
        while True:
            msg: Message = await queue.get()
            queue: Queue = __que_dict.get(msg.service1_id)
            await queue.put(msg)

    async def message_callback(message: Message):
        await __message_que.put(message)

    return message_classificator, message_callback
