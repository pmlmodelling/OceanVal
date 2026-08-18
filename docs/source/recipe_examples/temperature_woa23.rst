WOA23 temperature recipe
=========================

.. code-block:: python

   import oceanval

   oceanval.add_gridded_comparison(
       name="temperature",
       model_variable="thetao",
       recipe={"temperature": "woa23"},
       start=2005,
       end=2014,
       climatology=True,
   )
