import asyncio
from fastapi import FastAPI, Response, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import FileResponse, HTMLResponse
from random import randint
from uuid import uuid4, UUID
import logging

from chatbox50 import Chatbox, ServiceWorker, ChatClient
from discord_server import DiscordServer
NAME = "sample"
cb = Chatbox(name=NAME,
             s1_name="FastAPI",
             s2_name="DiscordServer",
             s1_id_type=UUID,
             s2_id_type=int,
             debug=True)
gateway_for_fastapi: ServiceWorker = cb.get_worker1()
gateway_for_discord: ServiceWorker = cb.get_worker2()
ds = DiscordServer()
app = FastAPI(title=NAME)
logger = logging.getLogger(__name__)


# ds = DiscordServer()

@app.get("/")
def root(request: Request):
    token = request.cookies.get("token")
    file_response = FileResponse("index.html")
    if token is None:
        file_response.set_cookie("token", str(uuid4()))
    return file_response


@app.get("/main.js")
def main_js():
    return FileResponse("main.js", filename="main" + str(randint(0, 1000000)) + ".js")


@app.websocket("/ws/{uid}")  # TODO: UUIDをつける
async def websocket_endpoint(ws: WebSocket, uid: UUID):
    # TODO: Authentication
    logger.info(f"ws_endpoint: {str(uid)}")
    gateway_for_fastapi.access_new_client(uid)
    await ws.accept()
    ws_messenger_task = asyncio.create_task(ws_messenger(ws, send_queue, uid))
    await ws_messenger_task


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
        msg = await queue.get()
        logger.debug(f"sender: {msg}")
        await ws.send_json({"auther": "you", "content": msg})


async def _ws_receiver(ws: WebSocket, uid: UUID):
    """

    Args:
        ws:
        uid:

    Returns:

    """
    while True:
        msg: str = await ws.receive_text()

        cb[uid] = msg
