from uuid import UUID, uuid4
import asyncio
from fastapi import (
    FastAPI, WebSocket, HTTPException, WebSocketException, WebSocketDisconnect, status,
    Cookie, Request)
from fastapi.templating import Jinja2Templates
import logging
from chatbox50 import ChatClient, Chatbox
from discord_server import DiscordServer
import os

logger = logging.getLogger(__name__)

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
templates = Jinja2Templates(directory='templates')
loop = asyncio.get_running_loop()
tasks: set[asyncio.Task] = set()
chat_boxes: dict[UUID, Chatbox] = dict()

app = FastAPI()
service = DiscordServer(name="ChatBox50", chat_boxes=chat_boxes, tasks=tasks)

tasks.add(loop.create_task(service.start(DISCORD_TOKEN), name="discord_server"))


@app.on_event("shutdown")
def shutdown():
    for task in tasks:
        task.cancel()


@app.get("/{room_uid}")
async def get(request: Request, room_uid: UUID, uid: UUID | None = Cookie(default=None)):
    print(chat_boxes)
    if room_uid not in service.chat_boxes:
        raise HTTPException(status_code=403, detail=f"{room_uid} is invalid")
    response = templates.TemplateResponse("index.html", {"request": request, "room_uid": str(room_uid)})
    if uid is None:
        response.set_cookie(key='uid', value=str(uuid4()))
    return response


@app.get("/{room_uid}/main.js")
async def get(request: Request, room_uid: UUID):
    return templates.TemplateResponse("main.js", {"request": request, "room_uid": str(room_uid)})


@app.websocket("/ws/{room_uid}/{uid}")
async def ws_endpoint(websocket: WebSocket, room_uid: UUID, uid: UUID):
    chat_box = chat_boxes.get(room_uid)
    if not isinstance(chat_box, Chatbox):
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
    client = await chat_box.get_client_or_create_new_client(uid)
    await websocket.accept()
    await websocket.send_json({"auther": "server", "content": "connected"})
    try:
        async with asyncio.TaskGroup() as tg:
            s_task = tg.create_task(send_task(websocket, client))
            r_task = tg.create_task(receive_task(websocket, client))
            await s_task
    except* WebSocketDisconnect:
        s_task.cancel()
        r_task.cancel()
        logger.info(f"Disconnected uid:{uid} chat_box:{chat_box.name}")
        chat_box.deactivate_client(uid)


async def send_task(websocket: WebSocket, client: ChatClient):
    print(f"waiting send task... uid: {client.uid}")
    while True:
        msg = await client.msg_thread_to_client.get()
        print(f"message got {msg}")
        await websocket.send_json({"auther": "server", "content": msg.content})
        print(client.messages)


async def receive_task(websocket: WebSocket, client: ChatClient):
    print('waiting for message')
    while True:
        msg = await websocket.receive_text()
        print(f"received: {msg}")
        await websocket.send_json({"auther": "you", "content": msg})
        await client.add_message(msg)
