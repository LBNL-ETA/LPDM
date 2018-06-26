#import abc
#from .current_type import CurrentType

#class Wire(abc.ABC):
    # def __init__(self, length_m, voltage):
    #     self.length_m = length_m 
    #     self.voltage = voltage
class Wire():
    def __init__(self, voltage, resistance, length, gauge, current_type):
        self.voltage = voltage
        try:
            float(resistance)
            resistance = float(resistance)
        except (ValueError, TypeError):
            resistance = None
        if resistance is not None:
            # set resistance to parameter from json
            self.resistance = float(resistance)
            self.length = -1
            self.gauge = '??'
            self.current_type = '??'
        else:
            # calculate resistance from length, gauge, and current type
            self.length = length # meters
            self.gauge = gauge
            self.current_type = current_type
            self.resistance = self.calculate_resistance(length, gauge, current_type) # ohms

    # calculate resistance from length, gauge, and current type (AC vs DC)
    def calculate_resistance(self, length, gauge, current_type):
        GAUGERESDC = {'18':26.1,'16':16.4,'14':10.3,'12':6.5,'10':4.07,'8':2.551, \
            '6':1.608,'4':1.01,'3':0.802,'2':0.634,'1':0.505,'1/0':0.399, \
            '2/0':0.317,'3/0':0.2512,'4/0':0.1996,'250':0.1687,'300':0.1409, \
            '350':0.1205,'400':0.1053,'500':0.0845,'600':0.0704}
        GAUGERESAC = {'14':10.2,'12':6.6,'10':3.9,'8':2.56,'6':1.61,'4':1.02, \
            '3':0.82,'2':0.66,'1':0.52,'1/0':0.43,'2/0':0.33,'3/0':0.269, \
            '4/0':0.220,'250':0.187,'300':0.161,'350':0.141,'400':0.125}
        try:
            if current_type == 'AC':
                resPerM = GAUGERESAC[gauge]/1000.0
            elif current_type == 'DC':
                resPerM = GAUGERESDC[gauge]/1000.0
            else:
                raise Exception('Wire Def Error: {}, {}, {}'.format(length, gauge, current_type))
        except:
            raise Exception('Wire Def Error: {}, {}, {}'.format(length, gauge, current_type))
        R = length*resPerM
        return R

    def __repr__(self):
        #current_name = "AC" if self.current_type == CurrentType.AC else "DC"
        #return "gauge: {}, mohm_per_m: {}, type of current: {}".format(self.gauge_awg, self.mohm_per_m, current_name)
        return "voltage {}, resistance: {}, length: {}, gauge: {}, type of current: {}".format( \
                self.voltage, self.resistance, self.length, self.gauge, self.current_type)
   
    # def resistance_mohm(self):
    #     "Calculate the total resistance"
    #     if not (self.mohm_per_m > 0 and self.length_m > 0):
    #         raise Exception("Error")
    #     else:
    #         return self.length_m * self.mohm_per_m
    
    def calculate_power(self, wire_power):
        "Calculate the power"
        wire_current = wire_power/self.voltage
        # return wire_current*wire_current * (self.resistance_mohm() / 1000)
        return wire_current * wire_current * (self.resistance)

    def calculate_energy(self, delta_t_sec):
        "Calculate the energy"
        return self.calculate_power() * delta_t_sec

    # @property
    # @abc.abstractmethod
    # def gauge_awg(self):
    #     pass

    # @property
    # @abc.abstractmethod
    # def mohm_per_m(self):
    #     pass

    # @property
    # @abc.abstractmethod
    # def current_type(self):
    #     pass
