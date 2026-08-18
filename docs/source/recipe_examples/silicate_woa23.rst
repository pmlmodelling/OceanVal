WOA23 silicate recipe
======================

``model_variable`` is the variable name in the model NetCDF output.
Set ``climatology=True`` for a climatological comparison, or
``climatology=False`` to compare all available years. ``name`` is the short
name OceanVal uses in reports.

.. code-block:: python

   import oceanval

   oceanval.add_gridded_comparison(
       name="silicate",
       model_variable="si",
       recipe={"silicate": "woa23"},
       climatology=True,
   )
Dataset: `World Ocean Atlas 2023 <https://www.ncei.noaa.gov/products/world-ocean-atlas>`_.
