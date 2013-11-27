window.onload=function(){
    var ws = null;
    var elem_message = document.getElementById("message");
    var elem_status = document.getElementById("status");
    function start() {
        if (ws === null ){
            connect();
        }
        var filename = document.getElementById('filename').value;
        var time = document.getElementById('time').value;
        var is_random = 0;
        if(document.getElementById('is_random').cheched){
            is_random = 1;
        }
        ws.send("start " + filename+' '+time+' '+is_random);
    }
    function connect(){
        ws = new WebSocket("ws://0.0.0.0:8888/start");
        ws.onopen = function(){
            elem_message.innerHTML = "connected.";
            elem_status.innerHTML = 'connected';
            ws.send("");
            console.log("connected.");
        };
        ws.onclose = function () {
            elem_message.innerHTML = "closed";
            console.log("closed.");
            elem_status.innerHTML = 'closed';
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
    document.getElementById('start').onclick=start;
    document.getElementById('connect').onclick=connect;
    document.getElementById('clear').onclick=function(){elem_message.innerHTML=""};

    function refresh_literal(data){
        var new_elem_lit = document.createElement('table');
        new_elem_lit.id = 'literal';
        lit_data = data['lit'];
        var lit = document.createElement('tr');
        lit.innerHTML = "<th>id</th><th>sign</th><th>level</th><th>reason</th>"
        new_elem_lit.appendChild(lit);
        for(var key in lit_data){
            var lit = document.createElement('tr');

            var c = [];

            var id = document.createElement('td');
            var sign = document.createElement('td');
            var level = document.createElement('td');
            var propagate = document.createElement('td');

            id.innerHTML = key;

            switch (lit_data[key]["sign"]){
                case true: sign.innerHTML = "True";c.push('lit_true');break;
                case false: sign.innerHTML = "False";c.push('lit_false');break;
                default: sign.innerHTML = "Unassign";break;
            }

            if(lit_data[key]["level"] == null){
                level.innerHTML = "----";
            }else{
                level.innerHTML = lit_data[key]["level"];
            }

            if(lit_data[key]['reason'] == null && lit_data[key]["level"]!=null){
                propagate.innerHTML = "decide";
                c.push('lit_decide');
            }else if(lit_data[key]['reason'] != null){
                propagate.innerHTML = "clasuse: "+lit_data[key]['reason'];
                c.push('lit_propagate');
            }

            lit.className = c.join(' ')

            lit.appendChild(id);
            lit.appendChild(sign);
            lit.appendChild(level);
            lit.appendChild(propagate);
            new_elem_lit.appendChild(lit);
        }
        var elem_lit = document.getElementById('literal');
        elem_lit.parentNode.replaceChild(new_elem_lit,elem_lit);
    }
    function refresh_clause(data){
        var new_elem_clause = document.createElement('table');
        new_elem_clause.id = 'clause';
        clause_data = data['clause'];

        for(var key in clause_data){
            var clause = document.createElement('tr');
            var id = document.createElement('td');
            var data = document.createElement('td');

            if(clause_data[key]['is_learnt']){
                clause.className = "clause_learnt"
            }

            id.innerHTML = key;
            tmp = ""
            clause_data[key]['data'].forEach(
                function(v,i,a){
                    if(clause_data[key]['wl'].indexOf(i)>=0){
                        tmp+="<span>"+v+", </span>"
                    }else{
                        tmp+=v+", "
                    }
            });

            data.innerHTML = tmp;

            clause.appendChild(id);
            clause.appendChild(data);
            new_elem_clause.appendChild(clause);
        }
        var elem_clause = document.getElementById('clause');
        elem_clause.parentNode.replaceChild(new_elem_clause,elem_clause);
    }
    function refresh_implication(data){
        var history = data['history'];
        var elem = document.getElementById('implication');
        var wrap = document.getElementById('wrap_implication');
        elem.width = wrap.offsetWidth;
        elem.height = wrap.offsetHeight-30;
        var ctx = elem.getContext('2d');
        ctx.clearRect(0,0,elem.width,elem.height);
        ctx.font = "20pt Ricty"
        var def_x = 10;
        var def_y = 30;
        var offset_y = def_y;
        var offset_x = def_x;
        var dy = 40;
        var dx = 40;
        function point(c){
            ctx.fillStyle = "#FFF"
            ctx.fillText(c, offset_x+5,offset_y-5);
            offset_x += dx;
        }
        function nextLevel(){
            offset_x = def_x;
            offset_y += dy;
        }
        for(var level in history){
            var line = history[level];
            console.log(line)
            for(var i=0;i<line.length;i++){
                point(line[i]);
            }
            nextLevel();
        }
    }
};