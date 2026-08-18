OCCCI chlorophyll recipe
=========================

Dataset: `Ocean Colour CCI <https://esa-oceancolour-cci.org/>`_.

.. code-block:: python

   import oceanval

   oceanval.add_gridded_comparison(
       name="chlorophyll",
       model_variable="chl",
       recipe={"chlorophyll": "occci"},
       climatology=False,
   )

``model_variable`` is the variable name in the model NetCDF output.
Set ``climatology=True`` for a climatological comparison, or
``climatology=False`` to compare all available years. ``name`` is the short
name OceanVal uses in reports.
