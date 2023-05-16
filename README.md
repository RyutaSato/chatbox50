# ChatBox50

#### Description: ChatBox50 is a Python library that allows users to exchange messages between different services.

It also persists their history properly and automatically by SQLite.

This work uses JavaScript on the web to perform WebSocket communication with a web server using FastAPI to exchange
messages with the Discord server.

When the program is executed, a website is accessed; a chat page is displayed on the website and a unique ID (UUID) is
automatically assigned.

chatbox50 creates a thread in DiscordServer via a callback that allows chatting with the accessing client.

In addition, chatbox50 persists the client's UUID and Discord channel ID in SQL, so that the client can continue the
conversation when accessing the server again.

In addition, the data of these messages are also stored in SQL.

All processes are asynchronous and work seamlessly even when there are many accesses.

This is an example of message exchange between the Web and a Discord application.

In fact, it is not limited to this example, but can be used in all cases.

ChatBox50 is designed to function as a platform- and library-independent Python library.

## Role of each file

#### [chatbox50](chatbox50): The main body of the chatbox50 library that mediates messages asynchronously while maintaining messages between the two services.

#### [chatbox50/__init__.py](chatbox50/__init__.py): Simplifies the description of importing library classes.

#### [chatbox50/_utils.py](chatbox50/_utils.py): has utility functions for some libraries.

The `run_as_await_func()` is used to execute a callback function.
If the callback is not registered, it is ignored; if it is registered and defined with `async def`, it is executed as
is, and if it is defined with
If the callback is defined with `def`, it is executed asynchronously in a separate thread.
`str_converter()` is used to store unique IDs in SQL. When storing unique IDs, they are stored as strings.
However, in some cases, such as UUID class, `str(UUID())` does not work well to convert the string back to the same type
as the original unique ID.
For this purpose, this function converts a string to a string.
`get_logger_with_nullhandler()` is a function to create a dedicated logger for the library.

#### [chatbox50/connection.py](chatbox50/connection.py): Classes that hold client connection information between two services, respectively.

- `s1_id`: unique ID of service1
- `s2_id`: unique ID of service2
- `uid`: UUID to identify the Connection
- `Connection.__another_property`: If you want to keep other connection information, you can set it here.

#### [chatbox50/db_session.py](chatbox50/db_session.py): Class for database CRUD processing.

#### [chatbox50/message.py](chatbox50/message.py): Class for defining messages.

#### [chatbox50/service_worker.py](chatbox50/service_worker.py): Gateway for passing messages to and from the service.

#### [discord_server.py](discord_server.py): Class for connecting to Discord API via Websocket. It sends messages managed by chatbox50 to the Queue of chatbox50.

#### [main.js](main.js): Executable program on the Web side that connects FastAPI and Websocket.

#### [index.html](index.html): HTML file

#### [style.css](style.css): CSS file for chat screen.

#### [main.py](main.py): The main executable file. It manages the message connection with the client and asynchronous tasks of DiscordServer and ChatBox classes.

#### [websocket_router](websocket_router.py): Executes tasks for sending and receiving messages to and from Web clients.

#### [requirements.txt](requirements.txt): External library to use.

#### [staticfiles_router.py](staticfiles_router.py): returns requests for static files.

## HOW TO USE

````python
import logging
from chatbox50 import ChatBox
from asyncio import Queue

# Declare the ChatBox.
logger = logging.getLogger(__name__)

cb = ChatBox(name="chatbox50",
             s1_name="WebServer", s2_name="HogServer", s3_name="HogServer", s4_name="HogServer")
s2_name = "HogeAPI", s2_id_type = int
s2_id_type = int, _logger = logger, _logger = logger, _logger = logger
_logger = logger, debug = True
debug = True)

web_server = WebServer()
worker_web = cb.get_worker1
worker_web.set_received_message_callback(web_server.receive_callback)
worker_web.set_create_callback(web_server.create_callback)
worker_web.set_new_access_callback(web_server.access_callback)

````

Creates a Chatbox instance at the top level of the project.
Add the following arguments: 1.

``name`: The name of the ChatBox. If `debug=False`, the name is stored as `name.db`. 2.
`s1_name`, `s2_name`: The name of each ServiceWorker, useful for monitoring the debug logs. 3.
Default is UUID. 4.
4.`_logger`: to reflect your own logging settings to the whole chatbox50 library.

After declaring, you can get a `ServiceWorker` instance from a `ChatBox` instance and send/receive messages and register
callbacks from it.

#### can register its own service functions as callbacks.

- `set_received_message_callback`: Executed when a message is received.
- `set_create_callback`: called when a new client is registered in the database.
- `set_new_access_callback`: called when a new or existing access is received.

```python
from chatbox50 import ServiceWorker

worker_web: ServiceWorker = cb.get_worker2
client_id = 12345
queue = worker_web.receive_queue
client_queue = worker_web.get_client_queue(client_id)
sender = worker_web.get_msg_sender(client_id)
await sender("hello world")
```

- `get_client_queue(service_id)`: get a dedicated Queue to receive messages from the peer.
- `get_msg_sender(service_id)`: get a dedicated sender function for the connection. You can send a message by simply
  giving a string argument such as `sender("hello")`.
- `receive_queue`: A queue that can receive messages sent to all ServiceWorkers.
- `send_queue`: A queue that can send messages to any connection. However, the destination must be specified. (
  Basically, a sender instance is used.)
