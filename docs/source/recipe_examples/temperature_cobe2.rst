COBE2 temperature recipe
=========================

.. code-block:: python

   import oceanval

   oceanval.add_gridded_comparison(
       name="temperature",
       model_variable="thetao",
       recipe={"temperature": "cobe2"},
       climatology=False,
   )
