import optparse
from src.debugger import *
if __name__ == "__main__":
    debugger = Debugger()
    debugger.start('127.0.0.1', 9000)
    def print_info(result):
        print result
    debugger.add_operation(RunOperation(debugger, print_info))
    
