import SocketServer
import threading
from xml.dom.minidom import parseString
from base64 import b64encode
import os

class DBGPThread(threading.Thread):
    def __init__(self, connection, connection_fn):
        threading.Thread.__init__(self)
        self.server = DBGPServer(connection, connection_fn)

    def run(self):
        self.server.serve_forever()

    def stop(self):
        self.server.shutdown()


class DBGPServer(SocketServer.TCPServer):
    def __init__(self, connection, connection_fn):
        SocketServer.TCPServer.__init__(self, connection, DBGPTCPHandler)
        self.connection_fn = connection_fn

class DBGPTCPHandler(SocketServer.BaseRequestHandler):
    """
    A DBGP TCP handler, dealing with request following the DPBP protocol.
    """
    def handle(self):
        # @todo, generate unique ID.
        self.transaction_id = 1;
        dbgp = DebuggerConnection(self.request, self.transaction_id)
        self.server.connection_fn(dbgp)

class DebuggerConnection:
    """
    This is an implementation of the DBGP protocol.
    """
    def __init__(self, connection, transaction_id):
        self.connection = connection
        self.transaction_id = transaction_id
        self.breakpoints = {}
        self.initialize()
        
    def set_breakpoint(self, file, lineNumber=-1, type="line", state="enabled", function=None, exception=None, hit_value=0, hit_condition=None, temporary=0, expression=None):
        """
        Set a breakpoint
        @return: The id of the newly set breakpoint.
        """
        command = "breakpoint_set -i {0} -t {1} -n {2} -f {3} -r {4}\0".format(self.transaction_id, type, lineNumber, file, state)
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
        id = self.execute_command(command).getElementsByTagName("response")[0].getAttribute('id')
        self.breakpoints[id] = id
        return id

    def execute_command(self, command):
        self.connection.sendall(command)
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
        return self.execute_command("status -i {0}\0".format(self.transaction_id)).getElementsByTagName("response")[0].getAttribute('status')

    def run(self):
        return self.execute_command("run -i {0}\0".format(self.transaction_id)).getElementsByTagName("response")[0].getAttribute('status')

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
        self.initialized = True

class Debugger:
    def __init__(self, base_path, ui, port=9000, host="127.0.0.1"):
        self.base_path = base_path
        self.ui = ui
        self.port = 9000
        self.host = host
        self.thread = None
        self.running = False
        self.connected = False
        self.operations = []
        self.operation_event = threading.Event()
        self.operation_lock = threading.Lock()
        ui.set_debugger(self)

    def is_connected(self):
        return self.connected

    def start(self):
        self.thread = DBGPThread((self.host, int(self.port)), self.handle_connection)
        self.ui.print_message(u"Listening")
        self.thread.start()

    def stop(self):
        self.release()
        self.ui.print_message("SHUTTING DOWN")
        if self.thread:
            self.thread.stop()
        self.ui.stop()
    
    def execute_operation(self, operation):
        with self.operation_lock:
            self.operations.append(operation)
        self.operation_event.set()
        
    
    def handle_connection(self, con):
        self.con = con
        self.connected = True
        file = self.find_file(con.fileUri)
        self.ui.print_file(file, self.open_file(file))
        self.run()
    
    def run(self):
        """
        Run loop.
        """
        self.running = True
        while self.running:
            self.execute_operations()
            self.operation_event.wait()

    def execute_operations(self):
        while len(self.operations) > 0:
            with self.operation_lock:
                item = self.operations.pop();
            item.run()
    
    def release(self):
        """
        Release any locks we might have.
        """
        self.running = False
            
    def find_file(self, fileUri):
        # Split the path into path
        parts = str(fileUri).split('/')
        # Go down the path until we find the common base directory.
        # The first three parts are useless since the return values of dbgp
        # are file:///.
        for i in range(len(parts[3:])):
            if len(parts) > i+3:
                current_path = "{0}/{1}".format(self.base_path, parts[i+3])
                if os.path.exists(current_path):
                    return current_path
        return False

    def open_file(self, file, relative=False):
        if relative:
            file = "{0}/{1}".format(self.base_path, file)
        try:
            handle = open(file)
            return handle.read()
        except:
            return False

class RunOperation():
    def __init__(self, debugger):
        self.debugger = debugger
    
    def run(self):
        result = self.debugger.con.run()
        self.debugger.ui.print_message(result)

class BreakPointOperation():
    def __init__(self, debugger, file, **args):
        self.debugger = debugger
        self.file = file
        self.args = args
    
    def run(self):
        self.debugger.con.set_breakpoint(self.file, self.args)
