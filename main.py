from uuid import UUID, uuid4
import asyncio
from fastapi import FastAPI, WebSocket, Query, WebSocketException, status, Cookie
from fastapi.templating import Jinja2Templates
from starlette.responses import FileResponse
from discord_server import DiscordServer
import os

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
templates = Jinja2Templates(directory='templates')
loop = asyncio.get_running_loop()
accepted_uid: set[UUID] = set()
tasks: set[asyncio.Task] = set()

app = FastAPI()
service = DiscordServer(name="ChatBox50", accepted_uid=accepted_uid)

tasks.add(loop.create_task(service.start(DISCORD_TOKEN)))


@app.on_event("shutdown")
def shutdown():
    for task in tasks:
        task.cancel()


@app.get("/")
async def get(uid: UUID | None = Cookie(default=None)):
    response = FileResponse("templates/index.html")
    if uid is None:
        response.set_cookie(key='uid', value=str(uuid4()))
    return response


@app.get("/main.js")
async def get():
    return templates.TemplateResponse("main.js", {"room_id": "44a6a4b3-1b45-4c30-9187-1578c4ac4b98"})


@app.websocket("/ws/{room_id}/{uid}")
async def ws_endpoint(websocket: WebSocket, room_id: UUID, uid: UUID):
    if uid not in accepted_uid:
        raise WebSocketException
    await websocket.accept()
    await websocket.send_json({"auther": "server", "content": "connected"})
    while True:
        msg = await websocket.receive_text()
        print(msg)
        await websocket.send_json({"auther": f"{websocket.client.host}", "content": msg})
