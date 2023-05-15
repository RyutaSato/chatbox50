
function addChatMessage(auther, body) {
    let list = document.getElementById('message-list');
    let item = document.createElement('ul');
    let className;
    if (auther === "you") {
        className = "chatbox-right"
    } else if (auther === "system") {
        className = "message"
    } else {
        className = "chatbox-left"
    }
    item.className = className
    item.innerHTML = "<b>" + auther + "<br></b> " + body;
    list.appendChild(item);
}
document.addEventListener('DOMContentLoaded', function (event) {
    addChatMessage('system', 'getting cookie...');
    const token = document.cookie
        .split('; ')
        .find(row => row.startsWith('token'))
        .split('=')[1];
    addChatMessage('system', 'your identification id:' + token);
    addChatMessage('system', 'connecting...');
    let socket = new WebSocket('ws://127.0.0.1:8000/ws/' + token);
    addChatMessage('system', 'waiting for server response...');
    socket.onopen = function (event) {
        addChatMessage('system', 'connection success!!');
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
    let send_button = document.getElementById('send-button');
    send_button.addEventListener('click', function () {
        let text = document.getElementById('message-content');
        socket.send(text.value);
        console.log(text.value);
        text.value = ""; // form clear
    });
});
