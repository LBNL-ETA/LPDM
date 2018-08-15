from Build.Objects.eud import Eud
from Build.Simulation_Operation.support import SECONDS_IN_DAY

class NotebookPersonalComputer(Eud):

    NOMINAL_DC_INPUT_VOLTAGE = 12

    ##
    # @param operating_power DC input voltage is typically 12[V]. Assuming on average, it consumes 5[A]
    def __init__(self, device_id, supervisor, total_runtime=SECONDS_IN_DAY, time=0, msg_latency=0, power_direct=False,
                 modulation_interval=600, schedule=None, multiday=0, connected_devices=None, operating_power=12*5):
        super().__init__(device_id, "personal_computer", supervisor, total_runtime = total_runtime, time=time, msg_latency=msg_latency, power_direct=power_direct,
                         modulation_interval=modulation_interval, schedule=schedule, multiday=multiday, connected_devices=connected_devices)
        self.operating_power = operating_power
        self.internal_battery = self.Battery()

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

    def respond_to_power(self, received_power):
        if received_power > self.operating_power:
           self.internal_battery.charge(received_power - self.operating_power)

    ##
    # Notebook Personal Computer does not seem to have any change of state
    def update_state(self):
        pass

    ##
    # Notebook Personal Computer does not seem to have any. Investigate more.
    def device_specific_calcs(self):
        pass

    class Battery(object):

        #
        # Use the data for "Battery and Power" for MacBook 2018 for now
        # (https://www.apple.com/macbook/specs/)
        #  "Up to 10 hours wireless web3
        #   Up to 12 hours iTunes movie playback3
        #   Up to 30 days of standby time3
        #   Built-in 41.4-watt-hour lithium-polymer battery
        #   29W USB-C Power Adapter; USB-C power port"
        #
        __capacity = 41.4 / 12  # 41.4[Wh] / 12[V] in order to get value in [Ah]
        __state_of_charge = 0.0

        # def __init__(self, capacity):
        #     self.__capacity = capacity

        def set_capacity(self, capacity):
            self.__capacity = capacity

        def set_stat_of_charge(self, state_of_charge):
            self.__state_of_charge = state_of_charge

        def state_of_charge(self):
            return self.__state_of_charge

        # Note: Simple implementation as a start
        def charge(self, power):
            # Note: Energy is measured in [Wh] thus assuming time has a unit of hour:
            current = power / NotebookPersonalComputer.NOMINAL_DC_INPUT_VOLTAGE
            capacity_change = current * 1 # [Ah]
            state_of_charge_change = capacity_change / self.__capacity
            if self.__state_of_charge + state_of_charge_change <= 1.0:
                self.__state_of_charge += state_of_charge_change
            else:
               self.__state_of_charge = 1.0
