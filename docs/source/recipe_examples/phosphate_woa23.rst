WOA23 phosphate recipe
=======================

.. code-block:: python

   import oceanval

   oceanval.add_gridded_comparison(
       name="phosphate",
       model_variable="po4",
       recipe={"phosphate": "woa23"},
       climatology=True,
   )
