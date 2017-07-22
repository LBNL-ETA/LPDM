"""
The grid controller is the fundamental building block of the nanogrid simulation.
The role of the grid controller is to manage power flows between the End Use Devices (EUD's),
power sources (such as Utility and PV), storage (batteries), and other grid controllers
(for the purposes of allocating power efficiently between them."""


from Build import Device
from Build import Priority_queue


class GridController(Device):

    # self.allocated (a dictionary of places from whom its been allocated).
    # self.

    def __init__(self, device_id, supervisor):
        super().__init__(self, device_id, supervisor)
        self._allocated = {}  # dictionary of devices and the amount the GC has been allocated from those devices. 



    def on_allocate(self, target, allocate_amt):
        self.set_allocated(allocate_amt)
        self.modulate_consumption()

    ##
    # Sets the amount that a Grid Controller has been allocated with respect to a particular device.
    #

    def set_allocated(self, target, allocate_amt):
        pass

    ##
    # Calculate this after a device has
    #
    def modulate_price(self):
        pass
