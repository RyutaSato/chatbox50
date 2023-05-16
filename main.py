import asyncio
import os
from contextlib import asynccontextmanager
from uuid import UUID
import logging
from fastapi import FastAPI, WebSocket

from chatbox50 import ChatBox, ServiceWorker
from discord_server import DiscordServer
from websocket_router import ws_messenger

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
    await web_api.access_new_client(uid)
    await ws.accept()
    send_queue: asyncio.Queue = web_api.get_client_queue(uid)
    ws_messenger_task = asyncio.create_task(ws_messenger(ws, send_queue, uid, web_api), name="messanger")
    await ws_messenger_task
    web_api.deactivate_client(uid)
    logger.debug({"place": "ws_endpoint", "action": "deactivate", "status": "success"})
