OCCCI chlorophyll recipe
=========================

.. code-block:: python

   import oceanval

   oceanval.add_gridded_comparison(
       name="chlorophyll",
       model_variable="chl",
       recipe={"chlorophyll": "occci"},
       climatology=False,
   )
