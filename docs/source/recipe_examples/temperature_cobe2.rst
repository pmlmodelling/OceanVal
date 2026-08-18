COBE2 temperature recipe
=========================

Dataset: `COBE-SST 2 <https://psl.noaa.gov/data/gridded/data.cobe2.html>`_.

.. code-block:: python

   import oceanval

   oceanval.add_gridded_comparison(
       name="temperature",
       model_variable="thetao",
       recipe={"temperature": "cobe2"},
       climatology=False,
   )

``model_variable`` is the variable name in the model NetCDF output.
Set ``climatology=True`` for a climatological comparison, or
``climatology=False`` to compare all available years. ``name`` is the short
name OceanVal uses in reports.
