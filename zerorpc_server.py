import zerorpc
from tug_simulation import TugSimulation
import json
import sys
import threading
import time

def runSimulation(params):
    print('run simulation')
    zerorpc_client = zerorpc.Client()
    zerorpc_client.connect("tcp://***REMOVED***:4245")

    sim = TugSimulation(params, zerorpc_client)
    sim.run()

class RpcController(object):
    def runSimulation(self, params):
        print('run sim')
        print(params)
        if threading.activeCount() < 5:
            t = threading.Thread(target=runSimulation, args=(params,))
            t.start()
            return True
        else:
            raise Exception("Too many simulations are running on the server.")

s = zerorpc.Server(RpcController())
if len(sys.argv) > 1 and sys.argv[1] == '-local':
    # don't accept connections from outside if -local is passed in as a command line argument
    s.bind("tcp://0.0.0.0:4242")
else:
    # accept connections from all ips
    s.bind("tcp://*:4242")

s.run()
