import zerorpc
from tug_simulation import TugSimulation
import json
import sys

class RpcController(object):
    interrupt = False
    sim = None
    config = None
    app_instance_id = None

    def initialize(self, params):
        print('initialize sim')
        print(params)

        RpcController.config = {
            "end_time": int(params["run_time_days"]) * 60 * 60 * 24 if params and 'run_time_days' in params.keys() and params['run_time_days'] else 60 * 60 * 24 * 7,
            "poll_interval": int(params["poll_interval_mins"]) * 60 if params and 'poll_interval_mins' in params.keys() and params['poll_interval_mins'] else 60 * 60
        }

        RpcController.sim = None
        RpcController.sim = TugSimulation(RpcController.config)
        device_info = RpcController.sim.initializeSimulation(params['config'])

        RpcController.app_instance_id = RpcController.sim.app_instance_id
        print('sim initialized {0}'.format(RpcController.app_instance_id))
        return {'app_instance_id': RpcController.app_instance_id, 'device_info': device_info}

    def getSimulations(self):
        print(RpcController.sim.simulations)
        return RpcController.sim.simulations if RpcController.sim else None

    def resetSimulation(self):
        RpcController.sim = None
        return True

    def runSimulation(self, params):
        if not RpcController.sim and params:
            self.initialize(params)

        if RpcController.sim:
            return RpcController.sim.run(step=int(params['step']))

        # if RpcController.sim and RpcController.sim.app_instance_id == RpcController.app_instance_id:
        #     # print('run sim {0}'.format(RpcController.app_instance_id))
        #     print(params);
        #     if not RpcController.sim and params:
        #         RpcController.initialize(params)

        #     if RpcController.sim:
        #         return RpcController.sim.run(step=int(params['step']))
        #     # print(RpcController.sim.deviceStatus())
        #     # return json.dumps(RpcController.sim.deviceStatus())
        # else:
        #     print('unable to run simulation ({0} != {1}'.format(RpcController.sim.app_instance_id, RpcController.app_instance_id))
        #     return null

    @zerorpc.stream
    def streamSimulation(self):
        print('stream simulation')
        if RpcController.sim and RpcController.sim.app_instance_id == RpcController.app_instance_id:
            print('run sim {0}'.format(RpcController.app_instance_id))
            return RpcController.sim
        else:
            print('unable to run simulation ({0} != {1}'.format(RpcController.sim.app_instance_id, RpcController.app_instance_id))
            return null

    def hello(self, params):
        # interrupt = False
        print('received event interrupt = {0}'.format(RpcController.interrupt))
        print(params)
        print(type(params))
        return "finished here"

    def stopSimulation(self):
        print('stop simulation')
        RpcController.interrupt = True
        return 500

s = zerorpc.Server(RpcController())
if len(sys.argv) > 1 and sys.argv[1] == '-local':
    # don't accept connections from outside if -local is passed in as a command line argument
    s.bind("tcp://0.0.0.0:4242")
else:
    # accept connections from all ips
    s.bind("tcp://*:4242")

s.run()


# sim = TugSimulation(sim_config)
# sim.initializeSimulation()
# sim.run(60*60)
# sim.dumpLog()
# print(sim.deviceStatus())

# sim.run(60 * 60)
# sim.dumpLog()
# print(sim.deviceStatus())
