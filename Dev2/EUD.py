
################################################################################################################################
# *** Copyright Notice ***
#
# "Price Based Local Power Distribution Management System (Local Power Distribution Manager) v1.0"
# Copyright (c) 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory
# (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All rights reserved.
#
# If you have questions about your rights to use or distribute this software, please contact
# Berkeley Lab's Innovation & Partnerships Office at  IPO@lbl.gov.
################################################################################################################################

"""
    Implementation of a general EUD device, which requests and consumes cerain amounts of power. 
"""
from abc import ABCMeta, abstractmethod
from device.base.device import Device
import logging

class Eud(Device):
    def __init__(self, config = None):
        # call the super constructor
        Device.__init__(self, config)
        self.allocated = 0 


#abstract methods 
#__________________________________________________________________________________
    @abstractmethod 
    def on_power_change(self, source_device_id, target_device_id, time, new_power):
        pass

    @abstractmethod
    def on_capacity_change(self, source_device_id, target_device_id, time, value):
        pass


    @abstractmethod 
    def on_price_change(self, source_device_id, target_device_id, time, new_price):
        pass


    @abstractmethod
    def on_time_change(self, new_time):
        pass

    @abstractmethod 
    def process_events(self):
        pass

#___________________________________________________________________________________
    
    # eud messaging functions

    """
    Once a grid controller has sent an allocate message, the EUD stores the value allocated in a field. 
    The EUD can consume any amount of power up to the allocate received quantity. 

    """

    def set_allocated(self, allocate):
        self.allocated = allocate
        #make sure this works. Not sure how logger works. 
        self._logger.debug(
                self.build_message(
                    message="allocate received",
                    tag="receive allocation",
                    value=allocated
                )
            )


    """

    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^DEV_QUESTION^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

    Reqeusts to use up to request_amt in power from each connected grid controller. Does it ask grid controllers
    in order of price? For now, assume each EUD only has one grid controller. 

    """
    def send_request(self, request):
        #sends out a message to the connected grid controller 
        GC.receive_power(){
        
        }

        #gets put into a GC queue. That it will be in some order of priority, 
