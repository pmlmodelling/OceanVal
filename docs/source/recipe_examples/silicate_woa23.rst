WOA23 silicate recipe
======================

Dataset: `World Ocean Atlas 2023 <https://www.ncei.noaa.gov/products/world-ocean-atlas>`_.

.. code-block:: python

   import oceanval

   oceanval.add_gridded_comparison(
       name="silicate",
       model_variable="si",
       recipe={"silicate": "woa23"},
       climatology=True,
   )

``model_variable`` is the variable name in the model NetCDF output.
Set ``climatology=True`` for a climatological comparison, or
``climatology=False`` to compare all available years. ``name`` is the short
name OceanVal uses in reports.

The ``woa23`` recipe supports nitrate, phosphate, oxygen, silicate, temperature,
and salinity. Nutrient and temperature/salinity products are vertically
resolved, with data available to approximately 800 m depending on the product.

Temperature and salinity use decadal climatologies. Set ``start`` and ``end``
within one of the supported periods:

* 1955-1964
* 1965-1974
* 1975-1984
* 1985-1994
* 1995-2004
* 2005-2014
* 2015-2022

See the `World Ocean Atlas page <https://www.ncei.noaa.gov/products/world-ocean-atlas>`_.
