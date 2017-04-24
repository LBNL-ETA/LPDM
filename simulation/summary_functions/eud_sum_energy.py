import os
import sys
import re
from summary_function_base import SummaryFunction

class SumEnergyEud(SummaryFunction):
    def __init__(self):
        SummaryFunction.__init__(self)
        self.sum_kwh = 0
        self.values = []
        self.last_value = None

    def __repr__(self):
        return "Total Energy Used: {} kWh".format(self.sum_kwh)

    def file_match(self, file_name):
        """only run this function for files that match a specific pattern"""
        if re.match("device.*_eud.log", file_name):
            return True
        else:
            return False

    def process_line(self, line):
        """process a single line of input"""
        match = re.findall(r"\d\d:\d\d:\d\d \((\d+)\).*message: Broadcast new power ([\d.]+)", line)
        if match and len(match) == 1:
            time = match[0][0]
            value = match[0][1]
            if self.last_value and self.last_values["time"] == time:
                # there could be multiple energy values reported for a single time, so only take the last value
                self.values.pop()
            self.values.append({"time": time, "value": value})
            self.last_match = self.values[-1]

    def end(self):
        """calculate the total energy used once all of the changes in energy have been captured"""
        for item in self.values:
            self.sum_kwh += float(item["value"]) * float(item["time"]) / 60.0 / 1000.0

def run(path, log_file_name):
    summary = SumEnergyEud()
    if summary.file_match(log_file_name):
        for line in open(os.path.join(path, log_file_name)):
            summary.process_line(line)
        summary.end()
        print summary

if __name__ == "__main__":
    summary_function = SumEnergyEud()

    for line in sys.stdin:
        summary_function.process_line(line)

    summary_function.end()
    print summary_function
