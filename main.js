
function addChatMessage(auther, body) {
    let list = document.getElementById('chat-list');
    let item = document.createElement('li');
    item.innerHTML = "<b>" + auther + "</b>: " + body;
    list.appendChild(item);
}
document.addEventListener('DOMContentLoaded', function (event) {
    let socket = new WebSocket('ws://127.0.0.1:8000/ws');
    addChatMessage('system', 'connecting...');
    socket.onopen = function (event) {
        addChatMessage('system', 'connection successes!!');
    }
    socket.onerror = function (event){
        addChatMessage('system', 'connection defused');
    }
    socket.onclose = function (event) {
        addChatMessage('system', 'disconnected');
    }
    socket.onmessage = function (event) {
        console.log(event.data);
        let msg = JSON.parse(event.data);
        addChatMessage(msg.auther, msg.content);
    }

    document.getElementById('send').addEventListener('click', function () {
        let text = document.getElementById('chat');
        socket.send(text.value);
        document.getElementById('send').value = ""; // form clear
    });
});
