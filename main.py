import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, Request, WebSocketDisconnect
from uuid import uuid4, UUID
import logging

from chatbox50 import ChatBox, SentBy, ServiceWorker, Message
from discord_server import DiscordServer

TOKEN = os.getenv("DISCORD_TOKEN")
debug = False
logging.basicConfig(level=logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler = logging.FileHandler("chatbox50.log", mode='w+', encoding="utf-8", )
handler.setFormatter(formatter)
logger = logging.getLogger(__name__)
logger.addHandler(handler)
NAME = "chatbox50"
cb = ChatBox(name=NAME,
             s1_name="FastAPI",
             s2_name="DiscordServer",
             s2_id_type=int,
             debug=debug,
             _logger=logger)
web_api: ServiceWorker = cb.get_worker1


# discord_api: ServiceWorker = cb.get_worker2


@asynccontextmanager
async def lifespan(app: FastAPI):
    if TOKEN is None:
        raise TypeError("TOKEN doesn't find")
    tasks: list[asyncio.Task] = []
    tasks.extend(cb.run())
    discord_api: ServiceWorker = cb.get_worker2
    ds = DiscordServer(api=discord_api, _logger=logger)
    ds_task = asyncio.create_task(ds.start(TOKEN), name="Discord Server")
    tasks.append(ds_task)
    logger.debug(tasks)
    yield
    logger.debug(tasks)
    for task in tasks:
        logger.debug({
            "action": "task_cancel",
            "status": "start",
            "object": task.get_name()
        })
        task.cancel()
    await ds.close()
    await asyncio.sleep(2)
    for task in tasks:
        if not task.done():
            logger.error({"action": "shutdown",
                          "status": "error",
                          "content": "task couldn't be canceled.the task was killed.",
                          "object": task.get_name()})
            del task


app = FastAPI(title=NAME, lifespan=lifespan)


@app.websocket("/ws/{uid}")
async def websocket_endpoint(ws: WebSocket, uid: UUID):
    # TODO: Authentication
    logger.info({"place": "ws_endpoint", "action": "access", "status": "success"})
    await web_api.access_new_client(uid)
    logger.debug({"place": "ws_endpoint", "action": "create", "status": "success"})
    await asyncio.sleep(1)
    await ws.accept()
    logger.debug({"place": "ws_endpoint", "action": "accept", "status": "success"})
    send_queue: asyncio.Queue = web_api.get_client_queue(uid)
    logger.debug({"place": "ws_endpoint", "action": "get_queue", "status": "success"})
    ws_messenger_task = asyncio.create_task(ws_messenger(ws, send_queue, uid), name="messanger")
    logger.debug({"place": "ws_endpoint", "action": "task_create", "object": "messanger"})
    await ws_messenger_task
    logger.debug({"place": "ws_endpoint", "action": "task_done", "object": "messanger"})
    web_api.deactivate_client(uid)
    logger.debug({"place": "ws_endpoint", "action": "deactivate", "status": "success"})


async def ws_messenger(ws: WebSocket, send_queue: asyncio.Queue, uid: UUID):
    send_task = asyncio.create_task(_ws_sender(ws, send_queue), name="websocket_sender")

    def __callback():
        return web_api.deactivate_client(uid)

    send_task.add_done_callback(__callback)
    logger.debug({"place": "ws_messenger", "action": "task_create", "object": "websocket_sender"})
    receive_task = asyncio.create_task(_ws_receiver(ws, uid), name="ws_receiver")
    logger.debug({"place": "ws_messenger", "action": "task_create", "object": "ws_receiver"})
    await send_task
    logger.debug({"place": "ws_endpoint", "action": "task_done", "object": "websocket_sender"})
    await receive_task
    logger.debug({"place": "ws_endpoint", "action": "task_done", "object": "ws_receiver"})


async def _ws_sender(ws: WebSocket, queue: asyncio.Queue):
    """ ** This function is completed **
    Notes:
        Queueから受け取ったメッセージをクライアントに送信します．
    Args:
        ws: WebSocket
        queue: Discordからクライアントへ送るためのQueueです．

    Returns:

    """
    logger.debug({"place": "ws_sender", "action": "loop_started", "object": "send_queue"})
    try:
        await ws.send_json({"auther": NAME + "Service", "content": "waiting for response"})
        while True:
            msg: Message = await queue.get()
            logger.debug({"place": "ws_sender", "action": "get_msg", "sent_by": msg.sent_by, "content": msg.content})
            auther = "you" if msg.sent_by == SentBy.s1 else NAME + "Service"
            send_data = {"auther": auther, "content": msg.content}
            await ws.send_json(send_data)
            logger.debug({"place": "ws_sender", "action": "send", "status": "success", "content": send_data})
    except WebSocketDisconnect:
        logger.debug({"action": "send", "status": "disconnect"})
        return


async def _ws_receiver(ws: WebSocket, uid: UUID):
    """

    Args:
        ws:
        uid:

    Returns:

    """
    msg_receiver = web_api.get_msg_sender(uid)
    logger.debug({"place": "ws_sender", "action": "loop_started", "object": "ws_receive"})
    try:
        while True:
            msg: str = await ws.receive_text()
            logger.debug({"place": "ws_sender", "action": "get_msg", "sent_by": str(uid), "content": msg})
            await msg_receiver(msg)
    except WebSocketDisconnect:
        logger.debug({"action": "receive", "status": "disconnect"})
        return

# ** DEPRECATED NO NEED ANY MORE
# logger.info(f"  {task.get_name()} {task.get_stack(limit=1)}" for task in asyncio.all_tasks())
# loop = asyncio.get_running_loop()
#
#
# async def task_checker(loop):
#     await asyncio.sleep(5)
#     for task in asyncio.all_tasks(loop):
#         if task.done():
#             logger.debug({"action": "task_check", "name": task.get_name(),
#                           "status_done": task.done(), "exception": str(task.get_stack(limit=1)[0])})
#     loop.create_task(task_checker(loop), name="task_checker")
#     return
#
#
# asyncio.create_task(task_checker(asyncio.get_running_loop()), name="task_checker")
