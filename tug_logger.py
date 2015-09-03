import datetime

class TugLoggerTime:
    def __init__(self, time):
        self.time = time
        self.actions = []

    def addAction(self, device, action, is_initial_event, value, description):
        self.actions.append(TugLoggerAction(device, action, is_initial_event, value, description))

class TugLoggerAction:
    def __init__(self, device, action, is_initial_event, value, description):
        self.device = device
        self.action = action
        self.is_initial_event = is_initial_event
        self.value = value
        self.description = description

class TugLogger:
    def __init__(self):
        self.time_logs = []
        self._current = None

    def logAction(self, device, time, action, is_initial_event, value, description):
        if not self._current or self._current.time != time:
            self._current = TugLoggerTime(time)
            self.time_logs.append(self._current)

        self._current.addAction(device, action, is_initial_event, value, description)

        return

    def dump(self):
        for time_log in self.time_logs:
            # print(time_log.time / 60.0)
            time_string = "Day {0} {1} ({2})".format(1 + int(time_log.time / (60 * 60 * 24)), datetime.datetime.utcfromtimestamp(time_log.time).strftime('%H:%M:%S'), time_log.time)
            print(time_string)
            for action in time_log.actions:
                print("\t{0}{1}, {2}, {3}, {4}, {5}".format("\t" if not action.is_initial_event else "", action.device.deviceName(), action.action, "IE" if action.is_initial_event else "NIE", action.value, action.description))

    def json(self):
        json = []
        for time_log in self.time_logs:
            current_time = {
                "time": time_log.time,
                "time_string": "Day {0} {1}".format(1 + int(time_log.time / (60 * 60 * 24)), datetime.datetime.utcfromtimestamp(time_log.time).strftime('%H:%M:%S')),
                "actions": []
            }
            for item in time_log.actions:
                current_time["actions"].append({
                    "device_name": item.device.deviceName(), 
                    "action": item.action, 
                    "is_initial_event": item.is_initial_event, 
                    "values": item.value,
                    "description": item.description})
            json.append(current_time)
            
        return json

    def jsonTime(self, time):
        json = None
        for time_log in self.time_logs[::-1]:
            if time == time_log.time:
                current_time = {
                    "time": time_log.time,
                    "time_string": "Day {0} {1}".format(1 + int(time_log.time / (60 * 60 * 24)), datetime.datetime.utcfromtimestamp(time_log.time).strftime('%H:%M:%S')),
                    "actions": []
                }
                for item in time_log.actions:
                    current_time["actions"].append({
                        "device_name": item.device.deviceName(), 
                        "uuid": item.device.uuid(),
                        "action": item.action, 
                        "is_initial_event": item.is_initial_event, 
                        "values": item.value,
                        "description": item.description})
                json = current_time
                break
            
        return json

    def jsonByMessageType(self, max_time):
        json = []
        for time_log in self.time_logs:
            # current_time = {
            #     "time": time_log.time,
            #     "time_string": "Day {0} {1}".format(1 + int(time_log.time / (60 * 60 * 24)), datetime.datetime.utcfromtimestamp(time_log.time).strftime('%H:%M:%S')),
            #     "actions": []
            # }
            for item in time_log.actions:
                device_json = None
                for current_json in json:
                    if current_json["device"] == item.device.deviceName() and current_json["action"] == item.action:
                        device_json = current_json
                        break

                if not device_json:
                    device_json = {
                        "device": item.device.deviceName(),
                        "action": item.action,
                        "units": item.description,
                        "items": []
                    }
                    json.append(device_json)

                device_json["items"].append({
                    "time_seconds": time_log.time,
                    "time_string": "Day {0} {1}".format(1 + int(time_log.time / (60 * 60 * 24)), datetime.datetime.utcfromtimestamp(time_log.time).strftime('%H:%M:%S')),
                    "value": int(item.value) if type(item.value) == type(True) else item.value,
                    # "is_initial_event": item.is_initial_event,
                    "description": item.description
                })
            
        return {"max_time": max_time * 1000, "data": json}

    def dumpDevice(self, device):
        "Dump the activity for a specific device"
        for time_log in self.time_logs:
            actions = []
            for item in time_log.actions:
                if device == item.device:
                    actions.append(item)

            if len(actions):
                time_string = "Day {0} {1}".format(1 + int(time_log.time / (60 * 60 * 24)), datetime.datetime.utcfromtimestamp(time_log.time).strftime('%H:%M:%S'))
                print(time_string)
                for action in actions:
                    print("\t{0}{1}, {2}, {3}, {4}, {5}".format("\t" if not action.is_initial_event else "", action.device.deviceName(), action.action, "IE" if action.is_initial_event else "NIE", action.value, action.description))
