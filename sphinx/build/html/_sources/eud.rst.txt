End-Use Device
================

Configurable Parameters
_______________________

max_power_output
----------------
The maximum power output of the device.

.. csv-table::
   :header: "Data Type", "Range", "Units", "Default Value"
   :widths: 40, 40, 40, 40

   float, n/a, W, 100.0 W

price_dim_start
---------------
The price at which the device should start dimming its power.

.. csv-table::
   :header: "Data Type", "Range", "Units", "Default Value"
   :widths: 40, 40, 40, 40

   float, n/a, $/kWh, 0.3 $/kWh

price_dim_end
-------------
The price at which the device should stop dimming its power.

When price > price_dim_end and price < price_off, set to power_level_low.

.. csv-table::
   :header: "Data Type", "Range", "Units", "Default Value"
   :widths: 40, 40, 40, 40

   float, n/a, $/kWh, 0.7 $/kWh

price_off
---------
The price at which the device should shut off.

.. csv-table::
   :header: "Data Type", "Range", "Units", "Default Value"
   :widths: 40, 40, 40, 40

   float, n/a, $/kWh, 0.9 $/kWh

power_level_low
---------------
The low power output percentage.

.. csv-table::
   :header: "Data Type", "Range", "Units", "Default Value"
   :widths: 40, 40, 40, 40

   float, 0.0 - 100.0, Percent, 20.0%

