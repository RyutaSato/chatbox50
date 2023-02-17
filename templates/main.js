
function addChatMessage(auther, body) {
    let list = document.getElementById('chat');
    let item = document.createElement('li');
    item.innerHTML = "<b>" + auther + "</b>: " + body;
    list.appendChild(item);
}
document.addEventListener('DOMContentLoaded', function (event) {
    const uid = document.cookie
      .split('; ')
      .find(row => row.startsWith('uid'))
      .split('=')[1];
    var socket = new WebSocket('ws://127.0.0.1:8000/ws/{{room_uid}}/' + uid);
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
        let msg = JSON.parse(event.data);
        addChatMessage(msg.auther, msg.content);
    }
    let send_button = document.getElementById('send');
    send_button.addEventListener('click', function () {
        let text = document.getElementById('send-message');
        socket.send(text.value);
        console.log(typeof(text))
        text.value = ""; // form clear
    });
});
