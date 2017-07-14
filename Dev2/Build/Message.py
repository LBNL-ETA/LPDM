from enum import Enum

##
# A class to represent messages passed between devices
#
#


class Message:

    def __init__(self, time, sender, message_type, value):
        self.time = time
        self.sender = sender
        self.message_type = message_type
        self.value = value

##
# Messages can be of three types: Register, power, and price.
#
# A register message indicates that a device is seeking to register or unregister a connection with another device;
# a positive value with Register indicates that it would like to be registered under that device's connected devices,
# while a negative value indicates that it is requesting to disconnect.
#
# A power message indicates that a device is seeking to obtain or sell a quantity of power to/from another device.
# A positive value indicates that it wants to sell that amount, while a negative value indicates that it would like
# to purchase that amount.

# A price message indicates the device's new local price.


class MessageType(Enum):
    REGISTER = 1
    POWER = 2
    PRICE = 3

