"""
A default 'utility' file containing extra support functions and variables to be freely used by all classes.
"""

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


