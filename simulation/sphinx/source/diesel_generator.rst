Diesel Generator
================

Configurable Parameters
_______________________

fuel_tank_capacity
------------------
Fuel tank capacity in gallons.

.. csv-table::
   :header: "Data Type", "Range", "Units", "Default Value"
   :widths: 40, 40, 40, 40

   float, n/a, gallons, 100.0 gallons

fuel_level
----------
The percentage of fuel in the tank at the start of the simulation.

.. csv-table::
   :header: "Data Type", "Range", "Units", "Default Value"
   :widths: 40, 40, 40, 40

   float, 0.0 - 100.0, Percent, null (Setting to null will default to 100% full.)


fuel_reserve
------------
The target percentage of fuel left in the tank for refueling.
The percentage is expressed in values from 0.0 - 100.0.

.. csv-table::
   :header: "Data Type", "Range", "Units", "Default Value"
   :widths: 40, 40, 40, 40

   float, 0.0 - 100.0, Percent, 20.0


days_to_refuel
--------------
The number of days until the next refuel.

When the diesel generator is initialized it will use days_to_refuel to create a TTIE event to send to the supervisor.
The next TTIE event for refueling is scheduled after the generator has be refuelled.

.. csv-table::
   :header: "Data Type", "Range", "Units", "Default Value"
   :widths: 40, 40, 40, 40

   int, n/a, Days, 7 days

kwh_per_gallon
--------------
The power output of the generator.

.. csv-table::
   :header: "Data Type", "Range", "Units", "Default Value"
   :widths: 40, 40, 40, 40

   float, n/a, kWh/gallon, 36.36 kWh/gallon

time_to_reassess_fuel
---------------------
The time interval in seconds for calculating the trajectory of fuel consumption.

.. csv-table::
   :header: "Data Type", "Range", "Units", "Default Value"
   :widths: 40, 40, 40, 40

   int, n/a, seconds, 21600 seconds (6 hours)


fuel_price_change_rate
----------------------
The maximum amount the fuel price can change.

.. csv-table::
   :header: "Data Type", "Range", "Units", "Default Value"
   :widths: 40, 40, 40, 40

   float, 0.0 - 100.0, Percent, 5.0%


capacity
--------
The generation capacity (W).

.. csv-table::
   :header: "Data Type", "Range", "Units", "Default Value"
   :widths: 40, 40, 40, 40

   float, n/a, Watts, 2000.0 W

gen_eff_zero
------------
The generation at zero output.
Efficiency at some percentage is linear between _gen_eff_zero and _gen_eff_100

.. csv-table::
   :header: "Data Type", "Range", "Units", "Default Value"
   :widths: 40, 40, 40, 40

   float, 0.0 - 100.0, Percent, 0.0%

gen_eff_100
-----------
The generation efficiency at 100% output.
Efficiency at some percentage is linear between _gen_eff_zero and _gen_eff_100

.. csv-table::
   :header: "Data Type", "Range", "Units", "Default Value"
   :widths: 40, 40, 40, 40

   float, 0.0 - 100.0, Percent, 100.0%

price_reassess_time
-------------------
Interval for reassessing fuel price.

.. csv-table::
   :header: "Data Type", "Range", "Units", "Default Value"
   :widths: 40, 40, 40, 40

   int, n/a, Seconds, 3600 seconds (1 hour)


fuel_base_cost
--------------
Base cost of fuel ($/gallon).

.. csv-table::
   :header: "Data Type", "Range", "Units", "Default Value"
   :widths: 40, 40, 40, 40

   float, n/a, $/gallon, 5.0 $/gallon

static_price
------------
Boolean indicator on whether to use a dynamic fuel price scheme, using the preceeding parameters,
or a static fuel price scheme, using the current_fuel_price parameter.

.. csv-table::
   :header: "Data Type", "Range", "Units", "Default Value"
   :widths: 40, 40, 40, 40

   boolean, "{true, false}", n/a, false

.. note::
    The static_price flag needs to be set to true and a non-null value needs to be set for current_fuel_price
    in order for the static pricing to take effect.

current_fuel_price
------------------
The cost of fuel for static fuel pricing.

.. csv-table::
   :header: "Data Type", "Range", "Units", "Default Value"
   :widths: 40, 40, 40, 40

   float, n/a, $/gallon, null

.. note::
    The static_price flag needs to be set to true and a non-null value needs to be set for current_fuel_price
    in order for the static pricing to take effect.

