########################################################################################################################
# *** Copyright Notice ***
#
# "Price Based Local Power Distribution Management System (Local Power Distribution Manager) v2.0"
# Copyright (c) 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory
# (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All rights reserved.
#
# If you have questions about your rights to use or distribute this software, please contact
# Berkeley Lab's Innovation & Partnerships Office at  IPO@lbl.gov.
########################################################################################################################

"""Runs the simulation."""

from Build import Supervisor

supervisor = Supervisor()

# Read in the simulation file. For each device,
# add it to connected devices, and then add its name and TTIE to process_queue.

while supervisor.has_next_event():
    supervisor.occur_next_event()

print("Simulation has finished.")

