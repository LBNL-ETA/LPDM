"""
A default 'utility' file containing extra support functions and variables to be freely used by all classes.
"""

import datetime

SECONDS_IN_DAY = 86400
SECONDS_IN_HOUR = 3600
SECONDS_IN_MINUTE = 60

MIN_NONZERO_POWER = 0.01  # minimum value for power levels to be considered nonzero (to avoid floating point error).

##
# All power requests, unsatisfied power responses, and fluctuations that occur in the range of less than
# the min nonzero power are likely caused by floating point error and will be ignored by all devices.
# @param power_level the power level to determine whether it is significantly large to be considered nonzero
# @return a boolean value whether this power_level is significantly nonzero


def nonzero_power(power_level):
    return abs(power_level) > MIN_NONZERO_POWER


##
# Returns the absolute value of the difference between two values
def delta(a, b):
    return abs(a - b)


##
# Given a time in seconds, return a date in human readable format in the form of D HH:MM:SS
# where D = Day, HH = Hour, MM = Minute, SS = Seconds
# @param time_seconds the time in the simulation in seconds

def format_time_from_seconds(seconds):
    if seconds is None:
        return None
    (days, seconds) = divmod(seconds, SECONDS_IN_DAY)
    (hours, seconds) = divmod(seconds, SECONDS_IN_HOUR)
    (minutes, seconds) = divmod(seconds, SECONDS_IN_MINUTE)
    t_format = datetime.time(hour=hours, minute=minutes, second=seconds).isoformat()
    return "{} {}".format(days, t_format)