from abc import ABCMeta

class PowerType(metaclass=ABCMeta):
    def __init__(self):
        pass

class PowerGiver(PowerType):
    pass

class PowerTaker(PowerType):
    pass

class PowerGiverAndTaker(PowerType):
    pass
