import asyncio
import os

from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import FileResponse, HTMLResponse
from uuid import uuid4, UUID
import logging

from chatbox50 import ChatBox, SentBy, ServiceWorker, Message
from discord_server import DiscordServer

debug = False
logging.basicConfig(level=logging.DEBUG)
TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN is None:
    raise TypeError("TOKEN doesn't find")
NAME = "chatbox50"
cb = ChatBox(name=NAME,
             s1_name="FastAPI",
             s2_name="DiscordServer",
             s1_id_type=UUID,
             s2_id_type=int,
             debug=debug, )
web_api: ServiceWorker = cb.get_worker1
app = FastAPI(title=NAME)
discord_api: ServiceWorker = cb.get_worker2
ds = DiscordServer(api=discord_api, _logger=cb.logger)

logger = cb.logger.getChild("main")
@app.get("/")
async def root(request: Request):
    token = request.cookies.get("token")
    file_response = FileResponse("index.html")
    if token is None:
        file_response.set_cookie("token", str(uuid4()))
    return file_response


@app.get("/main.js")
async def main_js():
    return FileResponse("main.js")


@app.websocket("/ws/{uid}")
async def websocket_endpoint(ws: WebSocket, uid: UUID):
    # TODO: Authentication
    logger.info({"place": "ws_endpoint", "action": "access", "status": "success"})
    await web_api.access_new_client(uid)
    logger.debug({"place": "ws_endpoint", "action": "create", "status": "success"})
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
    await ws.send_json({"auther": "receptionist", "content": "waiting for response"})
    while True:
        msg: Message = await queue.get()
        logger.debug({"place": "ws_sender", "action": "get_msg", "sent_by": msg.sent_by, "content": msg.content})
        auther = "you" if msg.sent_by == SentBy.s1 else "receptionist"
        send_data = {"auther": auther, "content": msg.content}
        await ws.send_json(send_data)
        logger.debug({"place": "ws_sender", "action": "send", "status": "success", "content": send_data})


async def _ws_receiver(ws: WebSocket, uid: UUID):
    """

    Args:
        ws:
        uid:

    Returns:

    """
    msg_receiver = web_api.get_msg_sender(uid)
    logger.debug({"place": "ws_sender", "action": "loop_started", "object": "ws_receive"})

    while True:
        msg: str = await ws.receive_text()
        logger.debug({"place": "ws_sender", "action": "get_msg", "sent_by": str(uid), "content": msg})
        await msg_receiver(msg)


cb.run()
asyncio.create_task(ds.start(TOKEN), name="Discord Server")

logger.info(f"  {task.get_name()} {task.get_stack(limit=1)}" for task in asyncio.all_tasks())
loop = asyncio.get_running_loop()


async def task_checker(loop):
    await asyncio.sleep(5)
    for task in asyncio.all_tasks(loop):
        if task.done():
            logger.debug({"action": "task_check", "name": task.get_name(),
                          "status_done": task.done(), "exception": str(task.get_stack(limit=1)[0])})
    loop.create_task(task_checker(loop), name="task_checker")
    return


asyncio.create_task(task_checker(asyncio.get_running_loop()), name="task_checker")
