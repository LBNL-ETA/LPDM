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
        return None

def build_message(message="", time_seconds=None, device_id="", tag="", value=""):
    """Format the message for the log file/console output"""
    return "time: {0}; seconds: {1}; device_id: {2}; tag: {3}; value: {4}; message: {5}".format(
        format_time_seconds(time_seconds) if not time_seconds is None else "",
        time_seconds,
        device_id,
        tag,
        value,
        message
    )
