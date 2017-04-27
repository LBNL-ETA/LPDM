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
        if self.di.is_discharging() and self.di._price < price_threshold_discharge:
            # stop discharging if price is below the threshold
            self.di.stop_discharging()
        elif not self.di.is_discharging() and self.di._price < price_threshold_discharge:
            self.di.enable_discharge()
        elif self.di.is_charging() and self.di._price > price_threshold_charge:
            self.di.stop_charging()

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
            if price_threshold_discharge >= self.di._discharge_price_threshold:
                price_threshold_discharge = self.di._discharge_price_threshold
                price_threshold_charge = self.di._charge_price_threshold
            else:
                soc_ratio = (self.di._current_soc - 0.5) / 0.5
                price_adjustment = (max_24 - price_threshold_discharge) * soc_ratio
                price_threshold_discharge += price_adjustment
                price_threshold_charge += price_adjustment

        else:
            # charge at < 50%
            if price_threshold_charge <= self.di._charge_price_threshold:
                price_threshold_charge = self.di._charge_price_threshold
                price_threshold_discharge = self.di._discharge_price_threshold
            else:
                soc_ratio = self.di._current_soc / 0.5
                price_adjustment = (self.di._charge_price_threshold - min_24) * soc_ratio
                price_threshold_discharge += price_adjustment
                price_threshold_charge += price_adjustment

        return (price_threshold_discharge, price_threshold_charge)


