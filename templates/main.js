
function addChatMessage(auther, body) {
    let list = document.getElementById('chat');
    let item = document.createElement('li');
    item.innerHTML = "<b>" + auther + "</b>: " + body;
    list.appendChild(item);
}
document.addEventListener('DOMContentLoaded', function (event) {
    var socket = new WebSocket('ws://127.0.0.1:8000/ws');
    addChatMessage('system', 'connecting...')
    socket.onopen = function (event) {
        addChatMessage('system', 'connection successes!!');
    }
    socket.onerror = function (event){
        addChatMessage('system', 'connection defused');
    }
    socket.onclose = function (event) {
        addChatMessage('system', 'disconnected')
    }
    socket.onmessage = function (event) {
        let msg = JSON.parse(event.data);
        addChatMessage(msg.auther, msg.body);
    }

    document.getElementById('send').addEventListener('click', function () {
        let text = document.getElementById('send-message').value;
        socket.send(text);
        document.getElementById('send-message').value = ""; // form clear
    });
});
