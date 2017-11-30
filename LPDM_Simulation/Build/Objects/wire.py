""" A class to represent a wire layer physical connection between two devices.
Devices will maintain knowledge of all physical connections associated with that particular wire """


class Wire:

    # TODO: Add whatever else you want here. This is a placeholder.
    def __init__(self, length, gauge, voltage):
        self._length = length
        self._gauge = gauge
        self._voltage = voltage
