import tornado.ioloop
import tornado.web
import tornado.websocket

from tornado.options import define, options, parse_command_line

import os
import json

define('port', default=8888, help='run on the given port', type=int)

here = os.path.abspath(os.path.dirname(__file__))

clients = dict()


class IndexHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self, *args, **kwargs):
        self.set_header('Content-Type','application/json')
        self.set_header('Access-Control-Allow-Origin','*')
        
        cnf_files = os.listdir(here+'/../sample_cnf')
        res = json.dumps(cnf_files)
        self.write(res)
        self.finish()
        

class WebSocketHandler(tornado.websocket.WebSocketHandler):
    def open(self):
        self.id = self.get_argument("id")
        self.stream.set_nodelay(True)
        clients[self.id] = {"id": self.id, "object":self}
        
        self.p = None
    
    def on_message(self, message):
        print("Client %s received a message: %s" % (self.id, message))
        l = message.split(' ')
        cnf_files = os.listdir(here+'/../sample_cnf')
        filename = 'input.cnf'
        if len(l)>=2:
            if l[1] in cnf_files:
                filename = l[1]
        if len(l)>0 and l[0]=='start':
            from subprocess import Popen, PIPE, STDOUT
            if self.p:
                self.p.kill()
            self.p = Popen(['python', '-OO', '../pysat/pysat-extended.py' ,'--sleep','100','--output-type','json', '../sample_cnf/'+filename], stdout=PIPE,stderr=STDOUT)
            for line in iter(self.p.stdout.readline, b''):
                print(line)
                self.write_message(line)
    
    def on_close(self):
        if self.id in clients:
            del clients[self.id]
        print('closed')
        if self.p:
            self.p.kill()
            self.p = None

app = tornado.web.Application([
    (r'/', WebSocketHandler),
    (r'/filename', IndexHandler),
])


if __name__ == '__main__':
    parse_command_line()
    app.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()