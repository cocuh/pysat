import tornado.ioloop
import tornado.web
import tornado.websocket

from tornado.options import define, options, parse_command_line

import os
import json

define('port', default=8888, help='run on the given port', type=int)

here = os.path.abspath(os.path.dirname(__file__))

clients = []


class StaticFileHandler(tornado.web.StaticFileHandler):
    def set_extra_headers(self, path):
        self.set_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')

class PrototypeHandler(tornado.web.RequestHandler):
    def get(self, *args, **kwargs):
        cnf_files = sorted(os.listdir(here+'/../sample_cnf'))
        options = []
        for filename in cnf_files:
            l = open(here+'/../sample_cnf/'+filename).read().split('p cnf ')[1].strip().split(' ')
            num_l = l[0].split('\n')[0]
            num_c = l[1].split('\n')[0]
            options.append((filename,num_l,num_c))
        self.render('prototype.html',options=options)

class IndexHandler(tornado.web.RequestHandler):
    def get(self, *args, **kwargs):
        self.render('index.html')

class EnhancedHandler(tornado.web.RequestHandler):
    def get(self, *args, **kwargs):
        cnf_files = sorted(os.listdir(here+'/../sample_cnf'))
        options = []
        for filename in cnf_files:
            l = open(here+'/../sample_cnf/'+filename).read().split('p cnf ')[1].strip().split(' ')
            num_l = l[0].split('\n')[0]
            num_c = l[1].split('\n')[0]
            options.append((filename,num_l,num_c))
            #options.append('<option value="{s}">{s} {l} {c}</option>'.format(s=filename,l=num_l,c=num_c))
        #print(options)
        self.render('enhanced.html',options=options)


class SlideHandler(tornado.web.RequestHandler):
    def get(self, *args, **kwargs):
    #    self.render('slide.html')
        self.set_header('Content-Type','image/svg+xml')
        data = open(here+'/slide.svg').read()
        if os.path.exists(here+'/name'):
            data = data.replace("foobar", open(here+'/name').read())
        self.finish(data)

class WebSocketHandler(tornado.websocket.WebSocketHandler):
    def open(self):
        self.stream.set_nodelay(True)
        clients.append(self)

        self.p = None
    
    def on_message(self, message):
        print("Client  received a message: %s" % ( message))
        l = message.split(' ')
        cnf_files = os.listdir(here+'/../sample_cnf')
        filename = 'input.cnf'
        time = 100
        is_random = False
        if len(l)>=2:
            if l[1] in cnf_files:
                filename = l[1]
        if len(l)>=3:
            if l[2].isdigit():
                time = int(l[2])
        if len(l)>=4:
            if l[3].isdigit():
                is_random = (int(l[3])>0)
        if len(l)>0 and l[0]=='start':
            from subprocess import Popen, PIPE, STDOUT
            if self.p:
                self.p.kill()
            self.p = Popen(['python', '-OO', '../pysat/pysat-extended.py',
                            '--choose-type','random' if is_random else'order' ,'--sleep',str(time),
                            '--output-type','json', '../sample_cnf/'+filename],
                           stdout=PIPE,stderr=STDOUT)
            for line in iter(self.p.stdout.readline, b''):
                print(line)
                for client in clients:
                    client.write_message(line)

    def on_close(self):
        clients.remove(self)
        print('closed')
        if self.p:
            self.p.kill()
            self.p = None


app = tornado.web.Application([
    (r'/', IndexHandler),
    (r'/prototype', PrototypeHandler),
    (r'/slide', SlideHandler),
    (r'/enhanced', EnhancedHandler),
    (r'/start', WebSocketHandler),
    (r'/static/(.*)',StaticFileHandler, {"path":here+'/static/'})
],)


if __name__ == '__main__':
    parse_command_line()
    app.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
