from ..state_preference import StatePreference

class LogicB(object):
    def __init__(self, device_instance):
        self.di = device_instance

    def update_status(self):
        """
        """
        if not len(self.di._hourly_prices):
            # no hourly prices have been calculated
            return
        # update the charge on the device
        self.di.update_state_of_charge()
        # calculate the charge/discharge price thresholds
        (price_threshold_discharge, price_threshold_charge) = self.calculate_price_thresholds()
        # compare the current price to the calculated thresholds
        if self.di._current_soc >= 0.5:
            if self.di._price >= price_threshold_discharge:
                self.di._preference = StatePreference.DISCHARGE
            else:
                self.di._preference = StatePreference.NOTHING
        else:
            if self.di._price >= price_threshold_charge:
                self.di._preference = StatePreference.CHARGE
            else:
                self.di._preference = StatePreference.NOTHING

    def calculate_price_thresholds(self):
        if not len(self.di._hourly_prices):
            return
        avg_24 = sum(self.di._hourly_prices) / len(self.di._hourly_prices)
        min_24 = min(self.di._hourly_prices)
        max_24 = max(self.di._hourly_prices)

        # set the starting/ending threshold at 10% above/below the average
        price_threshold_discharge = avg_24 * 1.10
        price_threshold_charge = avg_24 * 0.90

        if self.di._current_soc >= 0.5:
            # charge at >= 50%
            soc_ratio = (self.di._current_soc - 0.5) / 0.5
            price_adjustment = (max_24 - price_threshold_discharge) * soc_ratio
            price_threshold_discharge += price_adjustment
            price_threshold_charge += price_adjustment

        else:
            # charge at < 50%
            soc_ratio = (0.5 - self.di._current_soc) / 0.5
            price_adjustment = (self.di._charge_price_threshold - min_24) * soc_ratio
            price_threshold_discharge -= price_adjustment
            price_threshold_charge -= price_adjustment

        self.di._logger.debug(self.di.build_message(
            message="avg_price {}, discharge = {}, charge = {}, soc = {}".format(
                avg_24,
                price_threshold_discharge,
                price_threshold_charge,
                self.di._current_soc
            ),
            tag="logic",
            value=1
        ))

        return (price_threshold_discharge, price_threshold_charge)
