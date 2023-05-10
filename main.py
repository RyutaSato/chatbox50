import asyncio
import os

from fastapi import FastAPI, Response, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import FileResponse, HTMLResponse
from random import randint
from uuid import uuid4, UUID
import logging

from chatbox50 import ChatBox, SentBy, ServiceWorker, ChatClient, Message
from discord_server import DiscordServer

debug = True
if debug:
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
             debug=debug)
web_api: ServiceWorker = cb.get_worker1
app = FastAPI(title=NAME)
discord_api: ServiceWorker = cb.get_worker2
ds = DiscordServer(api=discord_api)
logger = logging.getLogger(__name__)


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
    logger.info(f"ws_endpoint: {str(uid)}")
    web_api.access_new_client(uid)
    await ws.accept()
    send_queue: asyncio.Queue = web_api.get_client_queue(uid)
    ws_messenger_task = asyncio.create_task(ws_messenger(ws, send_queue, uid))
    await ws_messenger_task
    web_api.deactivate_client(uid)


async def ws_messenger(ws: WebSocket, send_queue: asyncio.Queue, uid: UUID):
    send_task = asyncio.create_task(_ws_sender(ws, send_queue))
    receive_task = asyncio.create_task(_ws_receiver(ws, uid))
    await send_task
    await receive_task


async def _ws_sender(ws: WebSocket, queue: asyncio.Queue):
    """ ** This function is completed **
    Notes:
        Queueから受け取ったメッセージをクライアントに送信します．
    Args:
        ws: WebSocket
        queue: Discordからクライアントへ送るためのQueueです．

    Returns:

    """
    while True:
        msg: Message = await queue.get()
        logger.debug(f"sent by: {msg.sent_by.name}, content: {msg.content}")
        auther = "you" if msg.sent_by == SentBy.s1 else "receptionist"
        await ws.send_json({"auther": auther, "content": msg.content})


async def _ws_receiver(ws: WebSocket, uid: UUID):
    """

    Args:
        ws:
        uid:

    Returns:

    """
    msg_receiver = web_api.get_msg_sender(uid)
    while True:
        msg: str = await ws.receive_text()
        logger.debug(f"uid: {uid} received: {msg}")
        await msg_receiver(msg)


cb.run()
asyncio.create_task(ds.start(TOKEN))
