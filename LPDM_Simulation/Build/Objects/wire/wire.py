import abc
from .current_type import CurrentType

class Wire(abc.ABC):
    def __init__(self, length_m, voltage):
        self.length_m = length_m 
        self.voltage = voltage

    def __repr__(self):
        current_name = "AC" if self.current_type == CurrentType.AC else "DC"
        return "gauge: {}, mohm_per_m: {}, type of current: {}".format(self.gauge_awg, self.mohm_per_m, current_name)
    
    def resistance_mohm(self):
        "Calculate the total resistance"
        if not (self.mohm_per_m > 0 and self.length_m > 0):
            raise Exception("Error")
        else:
            return self.length_m * self.mohm_per_m
    
    def calculate_power(self):
        "Calculate the power"
        return self.voltage * self.voltage / (self.resistance_mohm() * 1000)

    def calculate_energy(self, delta_t_sec):
        "Calculate the energy"
        return self.calculate_power() * delta_t_sec
    
    @property
    @abc.abstractmethod
    def gauge_awg(self):
        pass

    @property
    @abc.abstractmethod
    def mohm_per_m(self):
        pass

    @property
    @abc.abstractmethod
    def current_type(self):
        pass
