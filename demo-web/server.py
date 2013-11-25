import tornado.ioloop
import tornado.web
import tornado.websocket

from tornado.options import define, options, parse_command_line

define('port', default=8888, help='run on the given port', type=int)


clients = dict()


class IndexHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self, *args, **kwargs):
        self.write("this is your response")
        self.finish()
        

class WebSocketHandler(tornado.websocket.WebSocketHandler):
    def open(self):
        self.id = self.get_argument("id")
        self.stream.set_nodelay(True)
        clients[self.id] = {"id": self.id, "object":self}
    
    def on_message(self, message):
        print("Client %s received a message: %s" % (self.id, message))
        if message == 'start':
            from subprocess import Popen, PIPE, STDOUT
            p = Popen(['python', '../pysat/pysat.py','../sample_cnf/hoge.cnf'], stdout=PIPE,stderr=STDOUT)
            for line in iter(p.stdout.readline, b''):
                print(line)
                self.write_message(line)
    
    def on_close(self):
        if self.id in clients:
            del clients[self.id]

app = tornado.web.Application([
    (r'/', WebSocketHandler),
    (r'/start', IndexHandler)
])


if __name__ == '__main__':
    parse_command_line()
    app.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()