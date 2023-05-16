# ChatBox50

#### VideoDemo: https://www.youtube.com/watch?v=O-ex9Hj1u_M

#### Description:　ChatBox50は，異なるサービス間でのメッセージのやりとりを可能にするPythonライブラリです．

#### また，それらの履歴を適切に自動的にSQLiteにより永続化します．

本作品では，Web上のJavaScriptを用いてFastAPIによるWebサーバーとWebSocket通信を行い，Discordサーバーとメッセージのやりとりを可能とします．

プログラムを実行すると，Webサイトにアクセスできます．Webサイト上にはチャットページが表示され，自動的にユニークなID（UUID）が割り当てられます．

chatbox50はコールバックにより，DiscordServerに，アクセスしたクライアントとチャットが可能なスレッドを作成します．

また，chatbox50は，そのクライアントのUUIDと，DiscordのチャンネルIDをSQLにより永続化しているため，再度アクセスした際も続きから会話が可能です．

さらに，それらのメッセージのデータもSQLに保存されます．

全ての処理は非同期で行われており，多数のアクセスがあった場合でも，シームレスに機能します．

これはWebと，Discordアプリケーションという異なるサービス間でメッセージのやりとりをする1つの例として作りました．

実際は，この例にとどまらず，あらゆるケースで利用可能です．

ChatBox50は，それらのプラットフォームやライブラリにとらわれないPythonライブラリとして機能するよう設計しました．

## 各ファイルの役割

#### [chatbox50](chatbox50): 2つのサービス間のメッセージを保持しながら，非同期でメッセージを仲介するchatbox50ライブラリ本体

#### [chatbox50/__init__.py](chatbox50/__init__.py): ライブラリのクラスのインポートの記述を簡素化します．

#### [chatbox50/_utils.py](chatbox50/_utils.py): いくつかのライブラリ用のユーティリティ関数を持ちます．

`run_as_await_func()`は，コールバック関数を実行する際に使います．
コールバックが登録されていない場合はそれを無視し，登録されておりかつ，`async def`で定義されている場合はそのまま実行され，
`def`で定義されている場合は，別スレッドで非同期的にじっこうされます．
`str_converter()`は，ユニークなIDをSQLに保存する際に使用されます．ユニークなIDを保存する際は，文字列として保存します．
しかし，UUIDクラスなど，`str(UUID())`では，文字列を元のユニークなIDと同じ型に戻すことがうまくいかない場合があります．
そのための文字列への変換関数です．
`get_logger_with_nullhandler()`は，ライブラリ専用のloggerを作成する関数です．

#### [chatbox50/connection.py](chatbox50/connection.py): それぞれ2つのサービス間のクライアント接続情報を保持するクラスです．

- `s1_id`: service1のユニークなID
- `s2_id`: service2のユニークなID
- `uid`: Connectionの識別UUID
- `Connection.__another_property`: それ以外の接続情報を保持したい場合は，ここに設定できます．

#### [chatbox50/db_session.py](chatbox50/db_session.py): データベースのCRUD処理を行うクラスです．

#### [chatbox50/message.py](chatbox50/message.py): メッセージを定義するクラスです．

#### [chatbox50/service_worker.py](chatbox50/service_worker.py): サービスとメッセージの受け渡しを行うゲートウェイです．

#### [discord_server.py](discord_server.py): DiscordのAPIとWebsocketで接続するためのクラスです．受信したメッセージのうち，chatbox50で管理されているメッセージをchatbox50のQueueに送ります．

#### [main.js](main.js): Web側の実行プログラム．FastAPIとWebsocket接続を行います．

#### [index.html](index.html): HTMLファイル

#### [style.css](style.css): チャット画面用のCSSファイル．

#### [main.py](main.py): 中心となる実行ファイルです．クライアントとのメッセージ接続や，DiscordServerクラス，ChatBoxクラスの非同期タスク管理を行います．

#### [websocket_router](websocket_router.py): Webのクライアントとの送受信タスクを実行します．

#### [requirements.txt](requirements.txt): 使用する外部ライブラリ．

#### [staticfiles_router.py](staticfiles_router.py): 静的ファイルのリクエストを返します．

## HOW TO USE

```python
import logging
from chatbox50 import ChatBox
from asyncio import Queue

# ChatBoxを宣言します．
logger = logging.getLogger(__name__)

cb = ChatBox(name="chatbox50",
             s1_name="WebServer",
             s2_name="HogeAPI",
             s2_id_type=int,
             _logger=logger,
             debug=True)

web_server = WebServer()
worker_web = cb.get_worker1
worker_web.set_received_message_callback(web_server.receive_callback)
worker_web.set_create_callback(web_server.create_callback)
worker_web.set_new_access_callback(web_server.access_callback)

```

Chatboxインスタンスをプロジェクトの最上位で作成します．
引数には以下のものを追加します．

1. `name`: ChatBoxの名前．`debug=False`の場合は，`name.db`の形式で保存されます．
2. `s1_name`, `s2_name`: ServiceWorkerごとの名前．debugログを監視する際に有益です．
3. `s1_id_type`, `s2_id_type`: ServiceWorkerごとのユニークなIDの型を指定します．defaultはUUID
4. `_logger`: 自身のログの設定をchatbox50ライブラリ全体に反映できます．

宣言した後は，`ChatBox`インスタンスから`ServiceWorker`インスタンスを取得して，そこからメッセージの送受信や，コールバックの登録を行います．

#### 自身の持つサービスの関数をコールバックに登録できます．

- `set_received_message_callback`: メッセージを受け取った時に実行されます．
- `set_create_callback`: 新しいクライアントがあり，データベースに新規登録された際に呼ばれます．
- `set_new_access_callback`: 既存，新規いずれの場合も，アクセスがあった際に呼ばれます．

```python
from chatbox50 import ServiceWorker

worker_web: ServiceWorker = cb.get_worker2
client_id = 12345
queue = worker_web.receive_queue
client_queue = worker_web.get_client_queue(client_id)
sender = worker_web.get_msg_sender(client_id)
await sender("hello world")
```

- `get_client_queue(service_id)`: 相手側からのメッセージを受信する専用のQueueを取得できます．
- `get_msg_sender(service_id)`: そのConnection専用の送信用関数を取得できます．`sender("hello")`のように文字列を引数で与えるだけでメッセージを送れます．
- `receive_queue`: 全てのServiceWorkerに送られてきたメッセージを受け取ることができるQueueです．
- `send_queue`: どのConnectionへも送信できます．ただし送信先を指定する必要があります．(基本的に，senderインスタンスを使用する)
