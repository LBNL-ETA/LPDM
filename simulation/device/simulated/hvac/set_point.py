class SetPoint(object):
    def __init__(self, current_set_point=None, set_point_low=None, set_point_high=None,
            price_range_low=None, price_range_high=None, setpoint_schedule=None,
            price=None, setpoint_factor=None, setpoint_min=None, setpoint_max=None):
        self.current_set_point = current_set_point
        self.set_point_low = set_point_low
        self.set_point_high = set_point_high
        self.price_range_low = price_range_low
        self.price_range_high = price_range_high
        self.setpoint_schedule = setpoint_schedule

        self.price = None
        self.setpoint_factor = setpoint_factor
        self.setpoint_min = setpoint_min
        self.setpoint_max = setpoint_max

    def __repr__(self):
        return "setpoints: {}/{}, current = {}".format(
                self.set_point_low,
                self.set_point_high,
                self.current_set_point)

    def set_schedule(self, schedule):
        self.setpoint_schedule = schedule

    def set_initial_setpoints(self):
        if not self.setpoint_schedule:
            raise Exception("Error setting initial set points: set point schedule has not been initialized.")
        self.set_point_low = self.setpoint_schedule[0][1]
        self.set_point_high = self.setpoint_schedule[0][2]

    def set_price(self, new_price):
        self.price = new_price

    def set_setpoint_factor(self, new_value):
        self.setpoint_factor = new_value

    def set_setpoint_min(self, new_value):
        self.setpoint_min = new_value

    def set_setpoint_max(self, new_value):
        self.setpoint_max = new_value

    def set_setpoint_range(self, hour_of_day):
        """Change the set point range (low/high) according to the current hour of the day"""
        schedule_item = self.setpoint_schedule[hour_of_day - 1]
        if type(schedule_item) is list and len(schedule_item) == 3:
            self.set_point_low = schedule_item[1]
            self.set_point_high = schedule_item[2]
        else:
            raise Exception("Invalid setpoint schedule item {}".format(schedule_item))

    def reasses_setpoint(self):
        """
            determine the setpoint based on the current price and 24 hr. price history,
            and the current fuel price relative to price_range_low and price_range_high
        """
        # adjust setpoint based on price
        if self.price is None:
            # price hasn't been set yet, use the middle value
            new_setpoint = (self.set_point_low + self.set_point_high) / 2.0

        elif self.price > self.price_range_high:
            # price > price_range_high, then setpoint to max plus (price - price_range_high)/5
            new_setpoint = self.set_point_high + (self.price - self.price_range_high) / self.setpoint_factor
        elif self.price > self.price_range_low and self.price <= self.price_range_high:
            # fuel_price_low < fuel_price < fuel_price_high
            # new setpoint is relative to where the current price is between price_low and price_high
            new_setpoint = self.set_point_low + \
                    (self.set_point_high - self.set_point_low) * \
                    ((self.price - self.price_range_low) / (self.price_range_high - self.price_range_low))
        else:
            # price < price_range_low
            new_setpoint = self.set_point_low

        # adjust the setpoint for min/max limits if necessary
        if new_setpoint < self.setpoint_min:
            new_setpoint = self.setpoint_min
        elif new_setpoint > self.setpoint_max:
            new_setpoint = self.setpoint_max

        if new_setpoint != self.current_set_point:
            self.current_set_point = new_setpoint
            return True
        else:
            # setpoint was not changed
            return False
