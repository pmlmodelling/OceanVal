WOA23 nitrate recipe
=====================

.. code-block:: python

   import oceanval

   oceanval.add_gridded_comparison(
       name="nitrate",
       model_variable="no3",
       recipe={"nitrate": "woa23"},
       climatology=True,
   )
