GLODAP pH recipe
=================

``model_variable`` is the variable name in the model NetCDF output.
Set ``climatology=True`` for a climatological comparison, or
``climatology=False`` to compare all available years. ``name`` is the short
name OceanVal uses in reports.

.. code-block:: python

   import oceanval

   oceanval.add_gridded_comparison(
       name="ph",
       model_variable="ph",
       recipe={"ph": "glodap"},
       climatology=True,
   )
Dataset: `GLODAPv2.2016b <https://www.glodap.info/>`_.
