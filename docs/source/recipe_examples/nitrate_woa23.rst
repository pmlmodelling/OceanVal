WOA23 nitrate recipe
=====================

``model_variable`` is the variable name in the model NetCDF output.
Set ``climatology=True`` for a climatological comparison, or
``climatology=False`` to compare all available years. ``name`` is the short
name OceanVal uses in reports.

.. code-block:: python

   import oceanval

   oceanval.add_gridded_comparison(
       name="nitrate",
       model_variable="no3",
       recipe={"nitrate": "woa23"},
       climatology=True,
   )
Dataset: `World Ocean Atlas 2023 <https://www.ncei.noaa.gov/products/world-ocean-atlas>`_.
