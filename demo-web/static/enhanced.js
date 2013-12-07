window.onload = function () {
    var ws = null;
    var width = window.innerWidth;
    var height = window.innerHeight;
    var maxheight = window.innerHeight;
    var elem_message = document.getElementById("message");
    var elem_status = document.getElementById("status");

    var svg = d3.select("#svg");
    var lit_svg = svg.append('g').attr('id', 'literals');
    var clause_svg = svg.append('g').attr('id', 'clauses');
    var imp_svg = svg.append('g').attr('id', 'implication');
    var zero_svg = svg.append('g').attr('id', 'zeros');

    var clause_lit_dic = null;
    
    var clause_svg_left = 0.4*width;
    
    function _start() {
        var data = [1, 4, 6, 2, 1];

        var x = d3.scale.linear()
            .domain([0, d3.max(data)])
            .range(["0px", "420px"]);
        var y = d3.scale.ordinal()
            .domain(data)
            .rangeBands([0, 120]);

        svg.selectAll("rect")
            .data(data)
            .enter().append("rect")
            .attr("y", y)
            .attr("width", x)
            .attr("height", y.rangeBand())
    }

    function clear() {
        d3.selectAll('.literal').remove();
        d3.selectAll('.clause').remove();
    }

    function close() {
        ws.close();
        ws = null;
    }

    function start() {
        clear();

        width = window.innerWidth;
        height = window.innerHeight;

        clause_lit_dic = null;

        if (ws === null) {
            connect();
        }
        var filename = document.getElementById('filename').value;
        var time = document.getElementById('time').value;
        var is_random = 0;
        if (document.getElementById('is_random').cheched) {
            is_random = 1;
        }
        ws.send("start " + filename + ' ' + time + ' ' + is_random);
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
            if(data['status']===true){
                elem_status.innerHTML = 'SAT'
            }else if(data['status']===false){
                elem_status.innerHTML='UNSAT'
            }else{
                elem_status.innerHTML='----'
            }
            update(data);
            elem_message.innerHTML = string;
        };
    }

    function update(data) {
        function calc_position(lit_id) {
        }

        var text_color = 'white';
        var lit_elem = {};
        var clause_elem = {};
        var max_lit_id = 0;

        
        svg.selectAll('#marker')
            .data([""])
            .enter().append('defs').append("marker")
            .attr('id','marker')
            .attr('viewBox','0 0 10 10')
            .attr('refX','15')
            .attr('refY','5')
            .attr('markerUnits','strokeWidth')
            .attr('markerWidth','6')
            .attr('markerHeight','4')
            .attr('orient','auto')
            .append('path')
            .attr('fill','darkblue')
            .attr('stroke','white')
            .attr('stroke-width',1.3)
            .attr('d','M 0 0 L 15 5 L 0 10 z')
        
        /* literal column */
        lit_svg.attr('transform', 'translate(' + 0.88 * width + ',0)')
        var lit_data = Object.keys(data['lit']).map(function (key) {
            var t = data['lit'][key];
            t['id'] = parseInt(key);
            if (max_lit_id < t['id']) {
                max_lit_id = t['id']
            }
            return t
        });
        var lit_num = Object.keys(data['lit']).length;
        var lit_text_width = 0;
        var lit = lit_svg.selectAll(".literal")
            .data(lit_data)
        var lit_inner = lit
            .enter().append('g')
//            .attr('xml:space', 'preserve')
            .attr('class', 'literal');
        lit_inner.append('circle')
            .attr('r', 4.3)
        lit_inner.append('text')
            .attr('class', 'lit_id')
            .text(function (d) {
                return d['id']
            })
            .attr('dx', 8)
            .attr('dy', 6)
            .attr('fill', text_color)
        lit.select('.lit_id').each(function (d, i) {
            if (this.getBBox().width > lit_text_width) {
                lit_text_width = this.getBBox().width;
            }
        });
        lit_inner.append('text')
            .attr('class', 'lit_sign');

        lit.select('.lit_sign')
            .attr('dx', 8 + lit_text_width + 20)
            .attr('dy', 6)
            .attr('fill', text_color)
            .text(function (d) {
                var sign = '';
                var level = ''
                
                if(d['level']!==null){
                    level = d['level'].toString();
                    while(level.length<lit_num.toString().length){
                        level='0'+level;
                    }
                }else{
                    while(level.length<lit_num.toString().length){
                        level=' '+level;
                    }
                }
                switch (d['sign']) {
                    case true:
                        sign += 'True ';
                        break;
                    case false:
                        sign += 'False';
                        break;
                    case null:
                        sign += '     ';
                        break;
                }
                return sign+' '+level;
            })

        lit.classed('lit_decide', function (d) {
            return d['reason'] === null
        })
            .attr('transform', function (d) {
                var dy = (height - 6) / lit_num;
                var y = dy * (d.id - 1) + 10;
                if (y > maxheight) {
                    maxheight = y
                }
                return "translate(" + 0 + "," + y + ")";
            })
        lit.select('circle')
            .attr('fill', function (d) {
                switch (d['sign']) {
                    case true:
                        return 'white';
                        break;
                    case false:
                        return 'black';
                        break;
                    case null:
                        return 'none';
                        break;
                }
            })
            .attr('stroke', function (d) {
                switch (d['sign']) {
                    case true:
                        return 'white';
                        break;
                    case false:
                        return 'white';
                        break;
                    case null:
                        return 'none';
                        break;
                }

            })
            .attr('stroke-width', '1.5');
        lit.exit().remove();


        /* clause column */
        clause_svg.attr('transform', 'translate(' +clause_svg_left+ ',20)');
        var clause_data = Object.keys(data['clause']).map(function (key) {
            var t = data['clause'][key];
            t['id'] = parseInt(key);
            return t
        });
        var clause_num = Object.keys(data['clause']).length;
        var clause = clause_svg.selectAll('.clause')
            .data(clause_data);
        var clause_inner = clause
            .enter().append('g')
            .classed('clause', true)
            .classed('learnt', function (d) {
                return d['is_learnt']
            })
            .attr('xml:space', 'preserve')

        if (clause_lit_dic === null) {
            clause_lit_dic = {};
            for (var i = 1; i <= lit_num; i++) {
                clause_lit_dic[(i).toString()] = [];
                clause_lit_dic[(-i).toString()] = [];
            }
        }
        var clause_width_dic = {};
        clause_inner.append('text')
            .attr('fill', text_color)
            .attr('textLength', '100px');
        clause_inner.select('text').each(function (d, idx) {
            var here = d3.select(this);
            here.append('tspan').text('(');
            var first_flag = true;
            for (var key in d['data']) {
                if (!first_flag) {
                    here.append('tspan').text(' ∨ ').classed('clause_or', true)
                } else {
                    first_flag = false;
                }
                var v = d['data'][key];
                var left_space = '';
                for (var i = 0; i <= max_lit_id.toString().length - v.toString().length; i++) {
                    left_space += ' '
                }

                var elem = here.append('tspan').text(left_space + v);
                (clause_lit_dic[v.toString()]).push(elem);
            }
            here.append('tspan').text(')');
        });
        clause_width_dic['0'] = 0;
        clause.each(function (d, i) {
            var idx = (Math.floor(i / 40) + 1).toString();
            if (!(idx in clause_width_dic) || clause_width_dic[idx] < this.getBBox().width) {
                clause_width_dic[idx] = clause_width_dic[idx - 1] + this.getBBox().width + 10;
            }
        });
        var t = [];
        clause.attr('transform', function (d, i) {
            var oneline_num = 40;
            var x = clause_width_dic[Math.floor(i / oneline_num)];
            t.push(x);
            var dy = (height - 6) / oneline_num;
            var y = (i % 40) * dy - 3;
            return 'translate( ' + x + ', ' + y + ')';
        });
        clause.exit().remove();
        for (var i = 1; i <= lit_num; i++) {
            var d = data['lit'][i];
            var plus = d['id'].toString();
            var minus = -d['id'].toString();
            if (d['sign'] !== null) {
                for (var idx = 0; idx < clause_lit_dic[plus].length; idx++) {
                    clause_lit_dic[plus][idx].classed('lit_true', d['sign']);
                    clause_lit_dic[plus][idx].classed('lit_false', !d['sign']);
                }
                for (var idx = 0; idx < clause_lit_dic[minus].length; idx++) {
                    clause_lit_dic[minus][idx].classed('lit_true', !d['sign']);
                    clause_lit_dic[minus][idx].classed('lit_false', d['sign']);
                }
            } else {
                for (var idx = 0; idx < clause_lit_dic[plus].length; idx++) {
                    clause_lit_dic[plus][idx].classed('lit_true', false);
                    clause_lit_dic[plus][idx].classed('lit_false', false);
                }
                for (var idx = 0; idx < clause_lit_dic[minus].length; idx++) {
                    clause_lit_dic[minus][idx].classed('lit_true', false);
                    clause_lit_dic[minus][idx].classed('lit_false', false);
                }
            }
        }
        
        /* implication graph */
        imp_svg.attr('transform', 'translate(20,80)');
        
        var imp_dic = {};
        var imp_y = {"-1":0}; // idx -> height
        var imp_x = {"-1":0}
        var imp_min_y = {};
        
        var imp_r = 12;
        var imp_space = imp_r
        
        append_circle = function(obj){
            obj.append('circle')
                .attr('r',imp_r)
            obj.append('text')
                .attr('text-anchor','middle')
                .attr('dy',5)
                .text(function(id){return id})
        };
        
        // level zero literals
        zero_svg.attr('transform','translate(20,60)')
        var zero_literals = []
        for(var i=1; i<= lit_num;i++){
            if(data['lit'][i.toString()]['level']===0){
                zero_literals.push(data['lit'][i.toString()])
            }
        }
        var zeros = zero_svg.selectAll(".zeros").data(zero_literals)
        var inner_zeros = zeros.enter().append('g')
            .classed('zeros',true)
        append_circle(inner_zeros)
        zeros.exit().remove()
        zeros.select('text').text(function(d){
            if(d['sign']===true){
                return d['id']
            }else if(d['sign']===false){
                return -d['id']
            }else{
                return ''
            }
        })
        zeros.selectAll('circle').each(function(d){
            var i = Math.abs(d['id'])
            if(i in imp_dic){
                imp_dic[i].push(this)
            }else{
                imp_dic[i] = [this]
            }
        })
        zeros.attr('transform',function(_,i){
            var dx = clause_svg_left/zero_literals.length;
            var x = dx*i-imp_r;
            return 'translate('+x+',0)';
        })
            
        
        // draw history
        var imp_data = Object.keys(data['history']).map(function(key){
            return data['history'][key]
        })
        for(var i=0;i<imp_data.length;i++){
            imp_min_y[i.toString()] = 0;
        }
        var imp = imp_svg.selectAll('.imp').data(imp_data);
        imp.enter().append('g')
            .attr('level', function(d,idx){return idx+1})
            .classed('imp',true);
        
        var imp_one_decide_flag = true;
        imp.each(function(oneline,idx){
            var it = d3.select(this).selectAll('.it').data(oneline);
            var inner_it = it.enter().append('g')
                .classed('decided',function(id,idx){return idx===0})
                .classed('propagated',function(id,idx){return idx!==0})
                .classed('it',true)
                .attr('litid',function(d){return d});
            append_circle(inner_it)
            it.exit().remove();
            it.selectAll('circle').each(function(d){
                var i = Math.abs(d)
                if(i in imp_dic){
                    imp_dic[i].push(this)
                }else{
                    imp_dic[i] = [this]
                }
            })
            it.attr('transform',function(_,i){
                var x = i*3*imp_r;
                var y = (i%2?imp_r*(i+2):(i/2)*imp_r);
                //var t = i;
                //var x = t*imp_r*2+imp_r*t*(t-1)/4
                //var y = t*imp_r*3-imp_r*t*(t-1)/4
                if(imp_min_y[idx.toString()]>y){
                    imp_min_y[idx.toString()] = y;
                }
                return 'translate('+x+','+y+')';
            })
            if(imp_one_decide_flag && oneline.length == 1){
                imp_y[(idx-1).toString()] = 0;
                imp_y[(idx).toString()] = this.getBBox().height+imp_space;
                imp_x[(idx).toString()] = (this.getBBox().width+imp_space)*idx;
            }else{
                imp_one_decide_flag = false
                imp_y[(idx).toString()] = imp_y[(idx-1).toString()]+this.getBBox().height+imp_space;
                imp_x[(idx).toString()] = 0;
            }
        });
        imp.attr('transform',function(d,idx){
            var x = imp_x[(idx).toString()]
            var y = imp_y[(idx-1).toString()]-imp_min_y[idx.toString()]+imp_r;
            return 'translate('+x+','+y+')'
        })
        var imp_line = imp_svg.selectAll('path').data(Object.keys(imp_y));
        imp_line.enter().append('path').attr('level',function(_,idx){return idx});
        imp_line.exit().remove();
        imp_line
            .classed('imp_rule',true)
            .attr('d','M 0 0 L '+(clause_svg_left)+' 0')
            .attr('transform',function(_,idx){
                return 'translate(-20,'+(imp_y[(idx-1).toString()]-imp_space/2)+')'
            })
        imp.exit().remove();
        
        // gen path data
        var path_data = [];
        var imp_dic_keys = Object.keys(imp_dic);
        for(var idx=0;idx<imp_dic_keys.length;idx++){
            var key = imp_dic_keys[idx]
            var elem = imp_dic[key];
            if(typeof data['lit'][key]=="undefined"){
                console.log("hoge")
            }
            var reason = data['lit'][key]['reason'];
            if(reason !== null){
                var sources = data['clause'][reason.toString()]["data"];
                for(var i=0;i<sources.length;i++){
                    sources[i] = Math.abs(sources[i]).toString();
                }
                for(var i=0;i<sources.length;i++){
                    if(sources[i]!==key){
                        if(typeof imp_dic[sources[i]]=="undefined"){
                            // level0からの推論の場合implication graphにないためundefinedとなる
//                            console.log(imp_dic)
//                            console.log(sources[i])
//                            console.log(sources)
                        }else{
                            path_data.push({'from':imp_dic[sources[i]],'to':elem})
                        }
                    }
                }
            }
        }
        
        
        imp_svg.select('#path').remove();
        var imp_pathes_svg = imp_svg.insert('g','g')
            .attr('id','path');
        var imp_pathes = imp_pathes_svg.selectAll('.imp_path').data(path_data)
        imp_pathes.enter().append('path')
            .classed('imp_path',true)
            .attr('d',function(d){
                getpos = function(obj){
                    var dic = obj.getBoundingClientRect()
                    var res = {}
                    res.x = dic.left+dic.width/2-20
                    res.y = dic.top+dic.height/2-80
                    return res
                }
                var from = getpos(d['from'][0])
                var to = getpos(d['to'][0])
                var res = 'M '+from.x+' '+from.y+' L '+to.x+' '+to.y;
                return res
            })
            .attr('stroke-width',3)
            .attr('marker-end','url(#marker)')
        
        for(var i=0;i<data['analyze'].length;i++){
            var elem = imp_dic[data['analyze'][i]]
            d3.selectAll(elem).classed('analyzing',true)
        }

        /* svg size */
        svg.attr('width', width)
            .attr('height', maxheight);
    }

    document.getElementById('start').onclick = start;
    document.getElementById('clear').onclick = clear;
    document.getElementById('close').onclick = close;
};