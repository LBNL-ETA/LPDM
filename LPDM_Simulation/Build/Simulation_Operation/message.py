########################################################################################################################
# *** Copyright Notice ***
#
# "Price Based Local Power Distribution Management System (Local Power Distribution Manager) v2.0"
# Copyright (c) 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory
# (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All rights reserved.
#
# If you have questions about your rights to use or distribute this software, please contact
# Berkeley Lab's Innovation & Partnerships Office at  IPO@lbl.gov.
########################################################################################################################


"""
Implementation of the Message object which passed between Devices for communications in the simulation.
"""

from enum import Enum


class Message(object):

    def __init__(self, time, sender_id, message_type, value, extra_info=None):
        self.time = time  # timestamp of message in milliseconds
        self.sender_id = sender_id  # identify sender by their device ID.
        self.message_type = message_type  # Message type object, defined below.
        self.value = value  # the quantity associated with the messages (all messages are a quantity)
        self.extra_info = extra_info  # extra information associated with this message.


##
# Messages can be of five types: Register, power, price, request, and allocate.
#
# A register message indicates that a device is seeking to register or unregister a connection with another device;
# a positive value with Register indicates that it would like to be registered under that device's connected devices,
# while a negative value indicates that it is requesting to disconnect.
#
# A power message informs another device that power is now flowing between them in a certain direction.
# Once a device has received a power message with a certain quantity, that power flow must now exists between them --
# there is no further negotiation.

# A price message contains information about the sending device's local price.

# A request message indicates that a device is seeking to obtain power from another device. It must be a positive value.

# An allocate message indicates that how much a device is willing to provide to another device. It must be a positive
# value.


class MessageType(Enum):
    REGISTER = 1
    POWER = 2
    PRICE = 3
    REQUEST = 4
    ALLOCATE = 5

