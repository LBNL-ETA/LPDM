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

"""
Main run portal for the simulation. Calls run simulation in simulation.py.
"""

import Build.simulation as sim
import sys

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        sim.run_simulation(sys.argv[1], sys.argv[2:])
    elif len(sys.argv) == 2:
        sim.run_simulation(sys.argv[1], [])
    else:
        raise FileNotFoundError("Must enter a configuration filename")

    # TODO: Create a graphing function here.
