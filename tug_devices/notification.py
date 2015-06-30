"""
    Defines the interface for message sending between devices
"""
import abc

class NotificationReceiver:
    "Defines the interface for devices receiving messages"
    __metaclass__ = abc.ABCMeta

    def onTimeChange(self, new_time):
        "Message a device receives when a time change has occured"
        return

    @abc.abstractmethod
    def onPowerChange(self, source_device_id, target_device_id, time, new_power):
        "Message a device receives when a power change has occured"
        return

    @abc.abstractmethod
    def onPriceChange(self, source_device_id, target_device_id, time, new_price):
        "Message a device receives when a price change has occured"
        return

class NotificationSender:
    "Defines the interface for devices sending messages"
    __metaclass__ = abc.ABCMeta

    def broadcastNewPrice(self, source_device_id, target_device_id, time, new_price):
        "Broadcasts a 'new price' message for a device"
        return

    def broadcastNewPower(self, source_device_id, target_device_id, time, new_price):
        "Broadcasts a 'new power' message for a device"
        return

    # @abc.abstractmethod
    def broadcastNewTTIE(self, new_ttie):
        "Broadcasts a 'new TTIE' message for a device"
        return
