
function addChatMessage(auther, body) {
    let list = document.getElementById('chat-list');
    let item = document.createElement('li');
    item.innerHTML = "<b>" + auther + "</b>: " + body;
    list.appendChild(item);
}
document.addEventListener('DOMContentLoaded', function (event) {
    addChatMessage('system', 'getting cookie...');
    const token = document.cookie
        .split('; ')
        .find(row => row.startsWith('token'))
        .split('=')[1];
    addChatMessage('system', 'got uid:' + token + " from cookie.");
    addChatMessage('system', 'connecting...');
    let socket = new WebSocket('ws://127.0.0.1:8000/ws/' + token);
    addChatMessage('system', 'waiting for server response...');
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
        let msg = JSON.parse(event.data);
        addChatMessage(msg.auther, msg.content);
    }
    let send_button = document.getElementById('send');
    send_button.addEventListener('click', function () {
        let text = document.getElementById('chat');
        socket.send(text.value);
        console.log(text.value);
        text.value = ""; // form clear
    });
});
