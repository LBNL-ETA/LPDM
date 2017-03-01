Device Base Class
=================

Configurable Parameters
_______________________

device_id
---------
The unique identifier of the device.

.. csv-table::
   :header: "Data Type", "Range", "Units", "Default Value"
   :widths: 40, 40, 40, 40

   string, n/a, n/a, n/a

device_name
-----------
The unique name of the device.

.. csv-table::
   :header: "Data Type", "Range", "Units", "Default Value"
   :widths: 40, 40, 40, 40

   string, n/a, n/a, n/a

device_type
-----------
The type of the device, should correspond to the name of the device folder,
e.g. grid_controller, diesel_generator, eud, ...

.. csv-table::
   :header: "Data Type", "Range", "Units", "Default Value"
   :widths: 40, 40, 40, 40

   string, n/a, n/a, n/a

price
-----
The initial price of the device.  This would only be relevant if the
static_price flag is set to True since the price is sent from the grid controller.

.. csv-table::
   :header: "Data Type", "Range", "Units", "Default Value"
   :widths: 40, 40, 40, 40

   float, n/a, $/kWh, 0.0

static_price
------------
Boolean indicator for using a static pricing scheme for the device.
A price value must be supplied, and the static_price flag must be set to True.

.. csv-table::
   :header: "Data Type", "Range", "Units", "Default Value"
   :widths: 40, 40, 40, 40

   boolean, "{true,false}", n/a, false

broadcast_new_price
-------------------
The callback function for the device for broadcasting a new price.

.. csv-table::
   :header: "Data Type", "Range", "Units", "Default Value"
   :widths: 40, 40, 40, 40

   function, n/a, n/a, n/a

broadcast_new_power
-------------------
The callback function for the device for broadcasting a new power value.

.. csv-table::
   :header: "Data Type", "Range", "Units", "Default Value"
   :widths: 40, 40, 40, 40

   function, n/a, n/a, n/a

broadcast_new_ttie
-------------------
The callback function for the device for broadcasting a new ttie.

.. csv-table::
   :header: "Data Type", "Range", "Units", "Default Value"
   :widths: 40, 40, 40, 40

   function, n/a, n/a, n/a

