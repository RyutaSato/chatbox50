# ChatBox50
#### VideoDemo: TODO:
#### Description:　ChatBox50は，異なるサービス間でのメッセージのやりとりを可能にするPythonライブラリです．

#### また，それらの履歴を適切に自動的にSQLに保存します．

本作品では，Web上のJavaScriptを用いてFastAPIサーバーとWebSocket通信を行い，Discordサーバーとメッセージのやりとりを可能とします．

これはWebと，Discordアプリケーションという異なるサービス間でメッセージのやりとりをする1つの例として作りました．

実際は，この例にとどまらず，あらゆるケースで利用可能です．

ChatBox50は，それらのプラットフォームやライブラリにとらわれないPythonライブラリとして機能するよう設計しました．

Chatbox50は，特に次のようなケースを想定しています．

#### REQUIREMENT
利用する上で以下のような制約があります．
今後の説明において，2つの異なるサービス間を1stSP, 2ndSPと呼びます．
1. 1stSPの各クライアントおよび，2ndSPの各クライアントは，それぞれ固有のIDを持たなければなりません．
2. 固有のIDは1stSP及び，2ndSP間で重複してはいけません．
3. IDは，immutableな変数でなければなりません．(UUIDv4がおすすめです)
4. IDは，文字列と可逆変換できなければなりません．またその文字列はユニークでなければなりません．
5. 2ndSPのクライアントからメッセージを送り始めることはできません．


#### HOW TO USE
```python
from chatbox50 import Chatbox
from asyncio import Queue
from server import Server  # For example

receive_que = Queue()
send_que = Queue()

server = Server(receive_que, send_que)

cb = Chatbox(
    name="sample",
    server_send_que=send_que,
    server_receive_que=receive_que,
    create_channel_awaitable_callback=server.callback,
    debug=False
)
```

Chatboxインスタンスをプロジェクトの最上位で作成します．
引数には以下のものを追加します．    
1. `create_channel_awaitable_callback`: クライアントからアクセスがあったことをサーバーに通知するためのコールバック
2. `name`: 名前
3. `server_send_que`: Chatboxからサーバーにメッセージを送るためのQueue
4. `server_receive_que`: サーバーからのメッセージをChatboxが受け取るためのQueue



これだけです．
Chatboxに，メッセージを追加したり，クライアントからのアクセスがある，あるいはアクセスが切れた時，自動的にSQLにデータを永続化します．

