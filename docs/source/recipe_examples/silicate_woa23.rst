WOA23 silicate recipe
======================

.. code-block:: python

   import oceanval

   oceanval.add_gridded_comparison(
       name="silicate",
       model_variable="si",
       recipe={"silicate": "woa23"},
       climatology=True,
   )
