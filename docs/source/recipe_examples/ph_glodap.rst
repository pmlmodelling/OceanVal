GLODAP pH recipe
=================

.. code-block:: python

   import oceanval

   oceanval.add_gridded_comparison(
       name="ph",
       model_variable="ph",
       recipe={"ph": "glodap"},
       climatology=True,
   )
