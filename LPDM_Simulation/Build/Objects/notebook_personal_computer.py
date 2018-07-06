from Build.Objects.eud import Eud
from Build.Simulation_Operation.support import SECONDS_IN_DAY

class NotebookPersonalComputer(Eud):

    ##
    # @param operating_power DC input voltage is typically 12[V]. Assuming on average, it consumes 5[A]
    def __init__(self, device_id, supervisor, total_runtime=SECONDS_IN_DAY, time=0, msg_latency=0, power_direct=False,
                 modulation_interval=600, schedule=None, multiday=0, connected_devices=None, operating_power=12*5):
        super().__init__(device_id, "personal_computer", supervisor, total_runtime = total_runtime, time=time, msg_latency=msg_latency, power_direct=power_direct,
                         modulation_interval=modulation_interval, schedule=schedule, multiday=multiday, connected_devices=connected_devices)
        self.operating_power = operating_power

    ##
    # Notebook Personal Computer does not have startup behavior
    def begin_internal_operation(self):
        pass

    ##
    # Notebook Personal Computer does not have end behavior
    def end_internal_operation(self):
        pass

    def calculate_desired_power_level(self):
        self._logger.debug("In PersonalComputer#calculate_desired_power_level")
        return self.operating_power

    ##
    # Notebook Personal Computer does not seem to have any particular responce to received power
    def respond_to_power(self, received_power):
        pass

    ##
    # Notebook Personal Computer does not seem to have any change of state
    def update_state(self):
        pass

    ##
    # Notebook Personal Computer does not seem to have any. Investigate more. 
    def device_specific_calcs(self):
        pass
