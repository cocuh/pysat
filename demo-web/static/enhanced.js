window.onload = function () {
    var ws = null;
    function start() {
        if (ws === null) {
            connect();
        }
        console.log('start');
        ws.send("start " + 'sudoku.cnf' + ' ' + 100 + ' ' + 1);
    }

    function connect() {
        ws = new WebSocket("ws://0.0.0.0:8888/start");
        ws.onopen = function () {
            ws.send("");
            console.log("connected.");
        };
        ws.onclose = function () {
            console.log("closed.");
        };
        ws.onmessage = function (e) {
            var string = e.data;
            var data = JSON.parse(string);
            refresh_literal(data);
            refresh_clause(data);
            refresh_implication(data);
            elem_message.innerHTML = string;
        };
    }
    document.getElementById('start').onclick = start;
};