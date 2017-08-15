import datetime


##
# Given a time in seconds, return a date in human readable format in the form of Day #X HH:MM:SS
# where HH = Hour, MM = Minute, SS = Seconds
# @param time_seconds the time in the simulation in seconds
def format_time_from_seconds(seconds):
    if seconds is None:
        return None
    (days, seconds) = divmod(seconds, (24 * 60 * 60))
    (hours, seconds) = divmod(seconds, (60 * 60))
    (minutes, seconds) = divmod(seconds, 60)
    t_format = datetime.time(hour=hours, minute=minutes, second=seconds).isoformat()
    return "Day #{0} {1}".format(days, t_format)


##
# Builds a message string to include in the logger
# @param message the message to include in the logging string
# @param time seconds the time of the message
# @param device_id the device id
# @param tag the tag value to include in log
# @param value the value to include in message

def build_log_msg(message="", time_seconds=None, device_id="", tag="", value=""):

    return "{0}; {1}; {2}; {3}; {4}; {5}".format(
        format_time_from_seconds(time_seconds),
        time_seconds,
        device_id,
        tag,
        value,
        message
    )
