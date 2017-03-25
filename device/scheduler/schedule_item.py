class ScheduleItem:
    """
    Representation of a schedule task.
    """
    def __init__(self, last_day_time, time, value, time_unit='hour'):
        self.last_day_time = last_day_time
        self.day = None
        self.time= None
        self.value = None
        (self.day, self.time, self.value) = self.convert_units(time, value, time_unit)

    def __repr__(self):
        return "day {} - sec {} - value {}".format(self.day, self.time, self.value)

    def convert_units(self, time, value, time_unit):
        """Convert all units to seconds"""
        days = None
        secs = None
        if time_unit == 'day':
            # convert days to seconds
            days = time
            secs = 0
        elif time_unit == 'hour':
            # convert hours to seconds
            days = int(time / 24)
            secs = int((time * 3600) % (24 * 3600))
        elif time_unit == 'minute':
            # convert minutes to seconds
            days = int(time / 60 / 24)
            secs = int((time * 60) % (24 * 3600))
        elif time_unit == 'second':
            days = int(time / 3600 / 24)
            secs = time % (3600 * 24)
        else:
            raise Exception("Unable to convert time units ({}, {}, {})".format(
                time, value, time_unit
            ))

        # calculate the day that the schedule should run on
        if secs < self.last_day_time.time and days == 0:
            days = days + self.last_day_time.day + 1
        else:
            days = days + self.last_day_time.day
        # update the last calculated day
        self.last_day_time.day = days
        self.last_day_time.time = secs

        return (days, secs, value)
