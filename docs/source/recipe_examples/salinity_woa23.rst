WOA23 salinity recipe
======================

.. code-block:: python

   import oceanval

   oceanval.add_gridded_comparison(
       name="salinity",
       model_variable="so",
       recipe={"salinity": "woa23"},
       start=2005,
       end=2014,
       climatology=True,
   )
