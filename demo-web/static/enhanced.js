window.onload = function () {
    var ws = null;

    function _start() {
        if (ws === null) {
            connect();
        }
        console.log('start');
        ws.send("start " + 'sudoku.cnf' + ' ' + 100 + ' ' + 1);
    }

    function start() {
        var s = Snap("#svg");
        var bigCircle = s.circle(150, 150, 100)
        bigCircle.attr({
            fill: "#bada55",
            stroke: "#000",
            strokeWidth: 5
        });
        var smallCircle = s.circle(100, 150, 70);
        var discs = s.group(smallCircle, s.circle(200, 150, 70));
        discs.attr({
            fill: "#fff"
        });
        bigCircle.attr({
            mask: discs
        });
        smallCircle.animate({r: 50}, 1000);
        discs.select("circle:nth-child(2)").animate({r: 50}, 1000);
        var p = s.path("M10-5-10,15M15,0,0,15M0-5-20,15").attr({
            fill: "none",
            stroke: "#bada55",
            strokeWidth: 5
        });
        p = p.pattern(0, 0, 10, 10);
        bigCircle.attr({fill: p});
        discs.attr({fill: "r()#fff-#000"});
        discs.attr({fill: "R(150, 150, 100)#fff-#000"});
        p.select("path").animate({stroke: "#f00"}, 5000);
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