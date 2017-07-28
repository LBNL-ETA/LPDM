from last_day_time import LastDayTime
from schedule_item import ScheduleItem
from lpdm_exception import LpdmScheduleInvalid
from lpdm_event import LpdmEvent
import logging
from simulation_logger import message_formatter

SECS_IN_DAY = (24 * 60 * 60)
class Scheduler(object):
    def __init__(self, schedule, start_time=0):
        self.start_time = start_time
        self.schedule = schedule
        self.last_day_time = LastDayTime()
        self.scheduled_items = []
        self.last_item_index = None
        self.task_name = None
        self._logger = logging.getLogger('lpdm')

    def set_schedule(self, schedule):
        self.schedule = schedule

    def set_task_name(self, task_name):
        """Set the names for all scheduled tasks"""
        self.task_name = task_name

    def parse_schedule(self):
        """parse the schedule"""
        if not type(self.schedule) is list:
            # the schedule must be a List
            raise Exception("Schedule is not a List object.")

        day = 0
        self.scheduled_items = []
        for schedule_item in self.schedule:
            if type(schedule_item) is list:
                if len(schedule_item) in (2,3):
                    self.scheduled_items.append(ScheduleItem(self.last_day_time, *schedule_item))
                else:
                    raise Exception("Schedule item not valid length ({})".format(schedule_item))
            elif type(schedule_item) is dict:
                self.scheduled_items.append(ScheduleItem(self.last_day_time, **schedule_item))
        self._logger.debug(message_formatter.build_message(message="built schedule {}".format(self.scheduled_items), device_id="scheduler"))

    def get_next_scheduled_task(self, time_seconds):
        """Get the next scheduled task given a time in seconds"""
        # make sure the time passed is a valid number
        if not type(time_seconds) in (int, float):
            raise TypeError("Scheduler: invalid type for time_seconds ({}), must be int or float".format(type(time_seconds)))
        elif time_seconds < 0:
            raise ValueError("Scheduler: negative time values ({}) are not allowed.".format(time_seconds))

        # calculate the current day number
        day = int(time_seconds / SECS_IN_DAY)
        # calculate the number of seconds that have elapsed since midnight
        secs = time_seconds % SECS_IN_DAY

        # find the next scheduled event
        found_item = None
        for item in self.scheduled_items:
            if item.day == day and item.time > secs:
                # if there's a scheduled item for the current day then use it
                found_item = item
                break
            elif item.day == 0 and day == 0 and item.time == 0 and secs == 0:
                # attempting to get the schedule at t=0
                found_item = item
                break
            elif item.day > day:
                # if there isn't anything happening on the current day
                # then get the next schedule item
                found_item = item
                break

        # print "found item"
        # print found_item
        # if an event hasn't been found then we are past the last defined schedule
        # so repeat the last full day's schedule
        if found_item is None:
            # pull the next scheduled item from the last day's scheduled tasks
            last_day = None
            last_day_items = []
            # repeat the last day in the schedule
            # get the items from the last scheduled day
            for item in self.scheduled_items[::-1]:
                if last_day is None:
                    last_day = item.day
                if item.day != last_day:
                    break
                last_day_items.insert(0, item)

            if secs < last_day_items[0].time or secs >= last_day_items[-1].time:
                found_item = last_day_items[0]
            else:
                for item in last_day_items:
                    found_item = item
                    if item.time > secs:
                        break

        if not found_item is None:
            ttie = (day * SECS_IN_DAY) + found_item.time
            if ttie <= time_seconds and time_seconds > 0:
                ttie += SECS_IN_DAY
            return LpdmEvent(ttie, found_item.value, self.task_name)
        else:
            return None
