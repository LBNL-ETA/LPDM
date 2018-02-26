from .wire import Wire
from .current_type import CurrentType

class Wire18Dc(Wire):
    @property
    def gauge_awg(self):
        return 18

    @property
    def mohm_per_m(self):
        return 20.95
    
    @property
    def current_type(self):
        return CurrentType.DC

if __name__ == "__main__":
    print("main")
    wire = Wire18Dc(200, 220)
    print(wire.gauge_awg) 
    print(wire.mohm_per_m)
    print("resistance {}".format(wire.resistance_mohm()))
    print("power {}".format(wire.calculate_power()))
    print("energy {}".format(wire.calculate_energy(60)))
    print(wire)
