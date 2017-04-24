import datetime

def format_time_seconds(time_seconds):
    """
    Given a time in seconds, return a date in human readable format,
    in the form of Day X: YY:ZZ
    where X = days,
    YY = hours,
    ZZ = seconds
    """
    try:
        return "Day #{0} {1}".format(
            1 + int(time_seconds / (60 * 60 * 24)),
            datetime.datetime.utcfromtimestamp(time_seconds).strftime('%H:%M:%S')
        )
    except:
        return ""

def build_message(message="", time_seconds=None, device_id="", tag="", value=""):
    """Format the message for the log file/console output"""
    # time_string; seconds; device_id, tag, value, message
    return "{0}; {1}; {2}; {3}; {4}; {5}".format(
        format_time_seconds(time_seconds) if not time_seconds is None else "",
        time_seconds,
        device_id,
        tag,
        value,
        message
    )
