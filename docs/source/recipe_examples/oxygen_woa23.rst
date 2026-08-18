WOA23 oxygen recipe
====================

.. code-block:: python

   import oceanval

   oceanval.add_gridded_comparison(
       name="oxygen",
       model_variable="o2",
       recipe={"oxygen": "woa23"},
       climatology=True,
   )
