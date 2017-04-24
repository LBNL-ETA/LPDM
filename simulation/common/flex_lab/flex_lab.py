import paramiko

class FlexLab(object):
    def __init__(self, config={}):
        self._time = 0
        self._last_post_time = None
        self._host = config.get("host", None)
        self._flex_user = config.get("flex_user", None)
        self._key_file = config.get("key_file", None)
        # the minimum amount of time that needs to pass before a new set point can be posted
        self._actuation_lockout_time = config.get("actuation_lockout_time", 60.0 * 5.0)

        self._ssh = None

    def init(self):
        """Initialize the object"""
        # comment the connection out for testing
        # self.connect()
        pass

    def set_time(self, new_time):
        self._time = new_time

    def connect(self):
        self._ssh = paramiko.SSHClient()
        self._ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self._ssh.connect(self._host, username=self._flex_user, key_filename=self._key_file)

    def post_value(self, value):
        """Post a value to flex lab"""
        # only post a value if the minimum posting interval has been met or nothing has been posted yet
        if self._last_post_time is None or self._time - self._last_post_time > self._actuation_lockout_time:
            # self.run_cws_cmd(
                # user=self._flex_user,
                # passw=None,
                # system="the_system",
                # channel="the_channel",
                # value=value,
                # cmd="set"
            # )
            self._last_post_time = self._time

    def run_cws_cmd(self, user, passw, system, channel, value, cmd):
        if cmd == 'set':
            string = '{"cmd":"SETDAQ","sys":"{}","chn":"{}","val":"{}","user":"{}","pass":"{}"}'.format(
                system, channel, value, user, passw
            )
        else:
            string = '{"cmd":"GETDAQ","sys":"{}","chn":"{}",""user":"{}","pass":"{}"}'.format(
                system, channel, user, passw
            )
        stdin, stdout, stderr = ssh.exec_command(string)
        result = ""
        for line in stdout.readlines():
           result += line.strip()
        return result
