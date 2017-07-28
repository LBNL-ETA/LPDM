import unittest
from mock import MagicMock, patch
from device.scheduler import Scheduler

class TestScheduler(unittest.TestCase):
    def setUp(self):
        # hours are default time unit so should automatically recognize
        self.schedule_list_hour = [
            [8, 1, 'hour'],
            [17, 0, 'hour'],
            [20, 1],
            [23, 0],
            [3, 1],
            [15, 0]
        ]
        # hours are default time unit so should automatically recognize
        self.schedule_dict_hour = [
            {"time_unit": "hour", "time": 8, "value": 1},
            {"time_unit": "hour", "time": 17, "value": 0},
            {"time": 20, "value": 1},
            {"time": 23, "value": 0},
            {"time": 3, "value": 1},
            {"time": 15, "value": 0}
        ]
        self.schedule_dict_minute = [
            {"time_unit": "minute", "time": 8 * 60, "value": 1},
            {"time_unit": "minute", "time": 17 * 60, "value": 0},
            {"time_unit": "minute", "time": 20 * 60, "value": 1},
            {"time_unit": "minute", "time": 23 * 60, "value": 0},
            {"time_unit": "minute", "time": 3 * 60, "value": 1},
            {"time_unit": "minute", "time": 15 * 60, "value": 0}
        ]
        self.schedule_dict_second = [
            {"time_unit": "second", "time": 8 * 60, "value": 1},
            {"time_unit": "second", "time": 17 * 60, "value": 0},
            {"time_unit": "second", "time": 20 * 60, "value": 1},
            {"time_unit": "second", "time": 23 * 60, "value": 0},
            {"time_unit": "second", "time": 3 * 60, "value": 1},
            {"time_unit": "second", "time": 15 * 60, "value": 0}
        ]
        self.schedule_dict_day = [
            {"time_unit": "day", "time": 0, "value": 1},
            {"time_unit": "day", "time": 3, "value": 0},
            {"time_unit": "day", "time": 4, "value": 1},
            {"time_unit": "day", "time": 10, "value": 0},
            {"time_unit": "day", "time": 11, "value": 1},
            {"time_unit": "day", "time": 15, "value": 0}
        ]
        self.schedule_always_on = [
            [0, "on"]
        ]
        self.schedule_off_day4 = [
            [0, "on"],
            [0, "on"],
            [0, "on"], [12, "off"],
            [0, "off"]
        ]

    def test_parse_schedule_list_hour(self):
        """test parsing the schedule with lists and time is in hours"""
        # build the scheduler using the schedule_list
        scheduler = Scheduler(self.schedule_list_hour)
        scheduler.parse_schedule()

        # should have 6 items all in hours
        self.assertEqual(len(scheduler.scheduled_items), 6)
        # all times should be converted to seconds
        self.assertEqual(scheduler.scheduled_items[0].time, self.schedule_list_hour[0][0] * 60 * 60)
        self.assertEqual(scheduler.scheduled_items[1].time, self.schedule_list_hour[1][0] * 60 * 60)
        self.assertEqual(scheduler.scheduled_items[2].time, self.schedule_list_hour[2][0] * 60 * 60)
        self.assertEqual(scheduler.scheduled_items[3].time, self.schedule_list_hour[3][0] * 60 * 60)
        self.assertEqual(scheduler.scheduled_items[4].time, self.schedule_list_hour[4][0] * 60 * 60)
        self.assertEqual(scheduler.scheduled_items[5].time, self.schedule_list_hour[5][0] * 60 * 60)

        # the last two events should be happening on the next day
        self.assertEqual(scheduler.scheduled_items[4].day, 1)
        self.assertEqual(scheduler.scheduled_items[5].day, 1)

    def test_parse_schedule_dict_hour(self):
        """test parsing the schedule dict and time is in hours"""
        # build the scheduler using the schedule_dict
        scheduler = Scheduler(self.schedule_dict_hour)
        scheduler.parse_schedule()

        # should have 6 items all in hours
        self.assertEqual(len(scheduler.scheduled_items), 6)
        # all times should be converted to seconds
        self.assertEqual(scheduler.scheduled_items[0].time, self.schedule_dict_hour[0]["time"] * 60 * 60)
        self.assertEqual(scheduler.scheduled_items[1].time, self.schedule_dict_hour[1]["time"] * 60 * 60)
        self.assertEqual(scheduler.scheduled_items[2].time, self.schedule_dict_hour[2]["time"] * 60 * 60)
        self.assertEqual(scheduler.scheduled_items[3].time, self.schedule_dict_hour[3]["time"] * 60 * 60)
        self.assertEqual(scheduler.scheduled_items[4].time, self.schedule_dict_hour[4]["time"] * 60 * 60)
        self.assertEqual(scheduler.scheduled_items[5].time, self.schedule_dict_hour[5]["time"] * 60 * 60)

    def test_parse_schedule_dict_minute(self):
        """test parsing the schedule with dict and time is minute"""
        # build the scheduler using the schedule_list
        scheduler = Scheduler(self.schedule_dict_minute)
        scheduler.parse_schedule()

        # should have 6 items all in minutes
        self.assertEqual(len(scheduler.scheduled_items), 6)
        # all times should be converted to seconds
        self.assertEqual(scheduler.scheduled_items[0].time, self.schedule_dict_minute[0]["time"] * 60)
        self.assertEqual(scheduler.scheduled_items[1].time, self.schedule_dict_minute[1]["time"] * 60)
        self.assertEqual(scheduler.scheduled_items[2].time, self.schedule_dict_minute[2]["time"] * 60)
        self.assertEqual(scheduler.scheduled_items[3].time, self.schedule_dict_minute[3]["time"] * 60)
        self.assertEqual(scheduler.scheduled_items[4].time, self.schedule_dict_minute[4]["time"] * 60)
        self.assertEqual(scheduler.scheduled_items[5].time, self.schedule_dict_minute[5]["time"] * 60)

    def test_parse_schedule_dict_second(self):
        """test parsing the schedule with dicts and time is seconds"""
        # build the scheduler using the schedule_list
        scheduler = Scheduler(self.schedule_dict_second)
        scheduler.parse_schedule()

        # should have 6 items all in seconds
        self.assertEqual(len(scheduler.scheduled_items), 6)
        # all times should be converted to seconds
        self.assertEqual(scheduler.scheduled_items[0].time, self.schedule_dict_second[0]["time"])
        self.assertEqual(scheduler.scheduled_items[1].time, self.schedule_dict_second[1]["time"])
        self.assertEqual(scheduler.scheduled_items[2].time, self.schedule_dict_second[2]["time"])
        self.assertEqual(scheduler.scheduled_items[3].time, self.schedule_dict_second[3]["time"])
        self.assertEqual(scheduler.scheduled_items[4].time, self.schedule_dict_second[4]["time"])
        self.assertEqual(scheduler.scheduled_items[5].time, self.schedule_dict_second[5]["time"])

    def test_parse_schedule_dict_day(self):
        """Test parsing schedule with dicts and time unit is days"""
        scheduler = Scheduler(self.schedule_dict_day)
        scheduler.parse_schedule()

        # should have 6 items all seconds should be 0, only days should be set
        self.assertEqual(len(scheduler.scheduled_items), 6)

    def test_get_next_scheduled_task(self):
        """Test retrieving tasks"""
        # build the scheduler using the schedule_dict
        scheduler = Scheduler(self.schedule_dict_hour)
        scheduler.parse_schedule()

        task = scheduler.get_next_scheduled_task(0)
        # should be something coming up at 8:00
        self.assertEqual(task.ttie, 8 * 3600)

        # try and grab the next scheduled task at 18:00
        # should be the event at 20:00
        task = scheduler.get_next_scheduled_task(18 * 3600)
        self.assertEqual(task.ttie, 20 * 3600)

        # get the first task of the next day (day #1, 3:00)
        task = scheduler.get_next_scheduled_task(24 * 3600)
        self.assertEqual(task.ttie, 3600 * 24 + 3 * 3600)

        # get a task at a time period after the last explicitly scheduled task
        # this would be 1 minute after the last task
        # should be repeating the last day's schedule
        task = scheduler.get_next_scheduled_task(24 * 3600 + 15 * 3600 + 60)
        self.assertEqual(task.ttie, 24 * 3600 * 2 + 3 * 3600)
        # and this would be 15 days after the last scheduled task
        task = scheduler.get_next_scheduled_task(15 * 24 * 3600)
        self.assertEqual(task.ttie, 24 * 3600 * 15 + 3 * 3600)

    def test_schedule_always_on(self):
        """Make sure the first event starts at time 0"""
        scheduler = Scheduler(self.schedule_always_on)
        scheduler.parse_schedule()

        task = scheduler.get_next_scheduled_task(0)
        # should be something coming up at 8:00
        self.assertEqual(task.ttie, 0)

    def test_off_on_day_4(self):
        """Test as schedule that turns something off on day #4"""
        scheduler = Scheduler(self.schedule_off_day4)
        scheduler.parse_schedule()

            # [0, "on"],
            # [0, "on"],
            # [0, "on"], [12, "off"],
            # [0, "off"]
        # day #1
        task = scheduler.get_next_scheduled_task(0)
        self.assertEqual(task.ttie, 0)
        # day #2
        task = scheduler.get_next_scheduled_task(60 * 60 * 23)
        self.assertEqual(task.ttie, 60 * 60 * 24)
        # day #3
        task = scheduler.get_next_scheduled_task(60 * 60 * 47)
        self.assertEqual(task.ttie, 60 * 60 * 24 * 2)
        # day #4
        task = scheduler.get_next_scheduled_task(60 * 60 * 71)
        self.assertEqual(task.ttie, 60 * 60 * 24 * 3)
        # should be something coming up at 8:00
        # self.assertEqual(task.ttie, 0)

    def test_on_off(self):
        """Test a simple on/off schedule. On at 15:00 and off at 23:00.  Should repeat every day."""
        # setup the schedule
        the_schedule = [[15, "on"], [23, "off"]]
        # setup the scheduler and parse the schedule
        scheduler = Scheduler(the_schedule)
        scheduler.parse_schedule()

        # get the first task at time 0, should be on at 15
        task = scheduler.get_next_scheduled_task(0)
        self.assertEqual(task.ttie, 60 * 60 * 15)
        # the task at 16:00 should return off at 23:00
        task = scheduler.get_next_scheduled_task(60 * 60 * 16)
        self.assertEqual(task.ttie, 60 * 60 * 23)

if __name__ == "__main__":
    unittest.main()


