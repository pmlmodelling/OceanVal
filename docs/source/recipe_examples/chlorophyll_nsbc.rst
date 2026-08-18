NSBC chlorophyll recipe
========================

Dataset: North Sea Biogeochemical Climatology (NSBC).

.. code-block:: python

   import oceanval

   oceanval.add_gridded_comparison(
       name="chlorophyll",
       model_variable="chlorophyll",
       recipe={"chlorophyll": "nsbc"},
       climatology=True,
   )

``model_variable`` is the variable name in the model NetCDF output.
Set ``climatology=True`` for a climatological comparison, or
``climatology=False`` to compare all available years. ``name`` is the short
name OceanVal uses in reports.
