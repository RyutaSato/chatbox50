import asyncio
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect
import logging

from chatbox50 import Message, SentBy, ServiceWorker

logger = logging.getLogger(__name__)
NAME = "ChatBox"


async def ws_messenger(ws: WebSocket, send_queue: asyncio.Queue, uid: UUID, web_api: ServiceWorker):
    send_task = asyncio.create_task(_ws_sender(ws, send_queue), name="websocket_sender")

    def __callback():
        return web_api.deactivate_client(uid)

    send_task.add_done_callback(__callback)
    logger.debug({"place": "ws_messenger", "action": "task_create", "object": "websocket_sender"})
    receive_task = asyncio.create_task(_ws_receiver(ws, uid, web_api), name="ws_receiver")
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


async def _ws_receiver(ws: WebSocket, uid: UUID, web_api: ServiceWorker):
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
