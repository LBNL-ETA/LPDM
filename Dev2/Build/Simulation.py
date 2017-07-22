"""Runs the simulation."""

from Build import Supervisor

supervisor = Supervisor()

# Read in the simulation file. For each device,
# add it to connected devices, and then add its name and TTIE to process_queue.

while supervisor.has_next_event():
    supervisor.occur_next_event()

print("Simulation has finished.")

