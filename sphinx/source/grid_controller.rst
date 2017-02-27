Grid Controller
================

Configurable Parameters
_______________________

check_battery_soc_rate
----------------------
The rate at which the battery state of charge is calculated.

.. csv-table::
   :header: "Data Type", "Range", "Units", "Default Value"
   :widths: 40, 40, 40, 40

   int, n/a, seconds, 300 seconds (5 minutes)

pv_power_update_rate
--------------------
The rate at which to update the PV power output.

.. csv-table::
   :header: "Data Type", "Range", "Units", "Default Value"
   :widths: 40, 40, 40, 40

   int, n/a, seconds, 900 seconds (15 minutes)
