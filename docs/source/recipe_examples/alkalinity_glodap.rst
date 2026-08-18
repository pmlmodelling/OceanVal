GLODAP alkalinity recipe
=========================

.. code-block:: python

   import oceanval

   oceanval.add_gridded_comparison(
       name="alkalinity",
       model_variable="talk",
       recipe={"alkalinity": "glodap"},
       climatology=True,
   )
