import socket
import SocketServer
from xml.dom.minidom import parse, parseString
from base64 import b64encode

class DBGPServer(SocketServer.TCPServer):
    """
    A DBGP server class that can be used by any client to get notified about commands.
    """
    def __init__(self, connection):
        SocketServer.TCPServer.__init__(self, connection, DBGPTCPHandler)


class DBGPTCPHandler(SocketServer.BaseRequestHandler):
    """
    A DBGP TCP handler, dealing with request following the DPBP protocol.
    """
    def handle(self):
        # @todo, generate unique ID.
        self.transaction_id = 1;
        dbgp = DBGP(self.request, self.transaction_id)
        print dbgp.status()
        print dbgp.run()
        
class DBGP:
    """
    This is an implementation of the DBGP protocol.
    """
    def __init__(self, connection, transaction_id):
        self.connection = connection
        self.transaction_id = transaction_id
        self.initialize()

    def set_breakpoint(self, file, type="line", lineNumber=-1, state="enabled", function=None, exception=None, hit_value=0, hit_condition=None, temporary=0, expression=None):
        command = "set_breakpoint -i {0} -t {1} -n {1} -f {2} -r {3}\0".format(self.transaction_id, type, file, lineNumber, state) 
        if function:
            command = "{0} -m {1}".format(command, function)
        if exception:
            command = "{0} -x {1}".format(command, function)
        if hit_value:
            command = "{0} -h {1}".format(command, hit_value)
        if hit_condition:
            command = "{0} -o {1}".format(command, hit_condition)
        if temporary:
            command = "{0} -r {1}".format(command, hit_condition)
        if expression:
            command = "{0} -- {1}".format(command, b64encode(hit_condition))
        return self.execute_command(command)
        
    def execute_command(self, command):
        self.connection.sendall(command)
        print "Sending command {}".format(command)
        return self.receive()
        
    def receive(self):
        data = self.connection.recv(self.receive_size())
        self.connection.recv(1)
        dom = parseString(data)
        return dom

    def receive_size(self):
        val = ''
        size = ''
        while val != '\0':
            val = self.connection.recv(1)
            if val != '\0':
                size += val
        return int(size)

    def status(self):
        return self.execute_command("status -i {}\0".format(self.transaction_id)).getElementsByTagName("response")[0].getAttribute('status')

    def run(self):
        return self.execute_command("run -i {}\0".format(self.transaction_id)).getElementsByTagName("response")[0].getAttribute('status')
        
    def initialize(self):
        dom = self.receive()
        init = dom.getElementsByTagName("init")[0]
        self.idekey = init.getAttribute('idekey')
        self.session = init.getAttribute('session')
        self.thread = init.getAttribute('thread')
        self.parent = init.getAttribute('parent')
        self.language = init.getAttribute('language')
        self.protocolVersion = init.getAttribute('protocol_version')
        self.fileUri = init.getAttribute('fileuri')
        print self.fileUri
        self.initialized = True

if __name__ == "__main__":
    # @todo make this configurable
    HOST, PORT = "localhost", 9000
    server = DBGPServer((HOST, PORT))
    # Activate the server; this will keep running until you
    # interrupt the program with Ctrl-C
    server.serve_forever()
