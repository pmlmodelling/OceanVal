GLODAP pH recipe
=================

Dataset: `GLODAPv2.2016b <https://www.glodap.info/>`_.

.. code-block:: python

   import oceanval

   oceanval.add_gridded_comparison(
       name="ph",
       model_variable="ph",
       recipe={"ph": "glodap"},
       climatology=True,
   )

``model_variable`` is the variable name in the model NetCDF output.
Set ``climatology=True`` for a climatological comparison, or
``climatology=False`` to compare all available years. ``name`` is the short
name OceanVal uses in reports.

The ``glodap`` recipe provides annual climatologies of pH and alkalinity.
The products cover 1972-2013 and are surface-only. pH is reported on the total
scale and alkalinity in micromoles per kilogram.

See the `GLODAP website <https://www.glodap.info/>`_ and the
`GLODAPv2 reference <https://doi.org/10.5194/essd-8-325-2016>`_.
