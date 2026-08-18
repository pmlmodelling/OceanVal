NSBC oxygen recipe
===================

.. code-block:: python

   import oceanval

   oceanval.add_gridded_comparison(
       name="oxygen",
       model_variable="oxygen",
       recipe={"oxygen": "nsbc"},
       climatology=True,
   )
