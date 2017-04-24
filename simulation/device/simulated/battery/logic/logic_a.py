class LogicA(object):
    def __init__(self, device_instance):
        self.di = device_instance

    def update_status(self):
        """
        Update the status of the battery:
            * Ok to discharge?
            * Ok to charge?
            * Neither
            * Discharging?
            * Charging?
        """
        if self.di.power_source_manager is None:
            raise LpdmMissingPowerSourceManager()

        # update the charge on the device
        self.di.update_state_of_charge()

        if self.di._can_discharge:
            # if battery is discharging
            # if self.di.power_source_manager.total_load() - self.di._power_level > 0:
                # is there other load besides from this device?
            if self.di.power_source_manager.output_capacity() > 0.70 and self.di._current_soc < 0.65:
                # stop discharging and do nothing
                self.di.disable_discharge()
            elif self.di._current_soc < self.di._min_soc:
                # stop discharging and start charging
                self.di.disable_discharge()
                self.di.enable_charge()
                # self.di.start_charging()
            # else:
                # # stop discharging if there is no other load on the system
                # self.di.disable_discharge()
        elif self.di._can_charge:
            # battery is charging
            if self.di._current_soc >= self.di._max_soc \
            or (self.di.power_source_manager.output_capacity() < 0.3 and self.di._current_soc > 0.65):
                # stop discharging dn do nothing
                if self.di.is_charging():
                    self.di.stop_charging()
                self.di.disable_charge()
                if not self.di._can_discharge and self.di.power_source_manager.output_capacity() < 0.3 and self.di._current_soc > 0.65:
                    # start to discharge the battery
                    self.di.enable_discharge()
        else:
            # Neither - not charging and not discharging (load == 0)
            # if self.di.power_source_manager.total_load() > 0 \
            if not self.di._can_discharge and self.di.power_source_manager.output_capacity() < 0.3 and self.di._current_soc > 0.65:
                # start to discharge the battery
                self.di.enable_discharge()
