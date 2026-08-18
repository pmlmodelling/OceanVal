OCCCI KD490 recipe
===================

.. code-block:: python

   import oceanval

   oceanval.add_gridded_comparison(
       name="kd490",
       model_variable="kd490",
       recipe={"kd490": "occci"},
       climatology=False,
   )
