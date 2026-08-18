Data Recipes
============

OceanVal provides built-in recipes for common gridded observational datasets.
A recipe supplies the dataset metadata and remote file locations so you can
register a comparison without specifying every observation detail manually.

Recipes are available for gridded data. Use the ``recipe`` argument with
:func:`oceanval.add_gridded_comparison` and provide the model variable that
should be compared with the observation.

Available recipes

Global datasets
~~~~~~~~~~~~~~~
.. csv-table:: Global built-in recipes
   :header: "Region", "Variable", "Recipe", "Dataset", "Example"
   :widths: 12, 16, 16, 32, 24

   "Global", "Temperature", "``cobe2``", "`COBE-SST 2 <https://psl.noaa.gov/data/gridded/data.cobe2.html>`_", ":doc:`Full details <recipe_examples/temperature_cobe2>`"
   "Global", "Nitrate", "``woa23``", "`World Ocean Atlas 2023 <https://www.ncei.noaa.gov/products/world-ocean-atlas>`_", ":doc:`Full details <recipe_examples/nitrate_woa23>`"
   "Global", "Phosphate", "``woa23``", "`World Ocean Atlas 2023 <https://www.ncei.noaa.gov/products/world-ocean-atlas>`_", ":doc:`Full details <recipe_examples/phosphate_woa23>`"
   "Global", "Oxygen", "``woa23``", "`World Ocean Atlas 2023 <https://www.ncei.noaa.gov/products/world-ocean-atlas>`_", ":doc:`Full details <recipe_examples/oxygen_woa23>`"
   "Global", "Silicate", "``woa23``", "`World Ocean Atlas 2023 <https://www.ncei.noaa.gov/products/world-ocean-atlas>`_", ":doc:`Full details <recipe_examples/silicate_woa23>`"
   "Global", "Temperature", "``woa23``", "`World Ocean Atlas 2023 <https://www.ncei.noaa.gov/products/world-ocean-atlas>`_", ":doc:`Full details <recipe_examples/temperature_woa23>`"
   "Global", "Salinity", "``woa23``", "`World Ocean Atlas 2023 <https://www.ncei.noaa.gov/products/world-ocean-atlas>`_", ":doc:`Full details <recipe_examples/salinity_woa23>`"
   "Global", "Chlorophyll", "``occci``", "`Ocean Colour CCI <https://esa-oceancolour-cci.org/>`_", ":doc:`Full details <recipe_examples/chlorophyll_occci>`"
   "Global", "KD490", "``occci``", "`Ocean Colour CCI <https://esa-oceancolour-cci.org/>`_", ":doc:`Full details <recipe_examples/kd490_occci>`"
   "Global", "pH", "``glodap``", "`GLODAPv2.2016b <https://www.glodap.info/>`_", ":doc:`Full details <recipe_examples/ph_glodap>`"
   "Global", "Alkalinity", "``glodap``", "`GLODAPv2.2016b <https://www.glodap.info/>`_", ":doc:`Full details <recipe_examples/alkalinity_glodap>`"

Each Example link opens a separate page containing the corresponding call.

In each example:

* ``model_variable`` is the variable name in the model NetCDF output.
* Set ``climatology=True`` for a climatological comparison, or
   ``climatology=False`` to compare all available years.
* ``name`` is the short name OceanVal uses in reports.

.. toctree::
   :hidden:

   recipe_examples/temperature_cobe2
   recipe_examples/nitrate_woa23
   recipe_examples/phosphate_woa23
   recipe_examples/oxygen_woa23
   recipe_examples/silicate_woa23
   recipe_examples/temperature_woa23
   recipe_examples/salinity_woa23
   recipe_examples/chlorophyll_occci
   recipe_examples/kd490_occci
   recipe_examples/ph_glodap
   recipe_examples/alkalinity_glodap
   recipe_examples/oxygen_nsbc

The recipe dictionary must contain one variable and source identifier. For
example, ``{"temperature": "woa23"}`` selects temperature from WOA23.



Northwest European Shelf datasets
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``nsbc`` recipe provides North Sea Biogeochemical Climatology data for
chlorophyll, nitrate, phosphate, silicate, oxygen, temperature, and salinity.

See the :doc:`Full details <recipe_examples/oxygen_nsbc>` example for the NSBC recipe.

Dataset notes
-------------

COBE-SST 2
~~~~~~~~~~

The ``cobe2`` recipe provides global sea-surface temperature from NOAA's
Physical Sciences Laboratory. The data are surface-only and reported in
degrees Celsius.

See the `COBE2 dataset page <https://psl.noaa.gov/data/gridded/data.cobe2.html>`_.

Inspect a recipe directly
-------------------------

The recipe helper can be used to inspect the metadata selected for a variable:

.. code-block:: python

   from oceanval.parsers import find_recipe

   recipe = find_recipe({"temperature": "woa23"}, start=2005, end=2014)
   print(recipe["source"], recipe["obs_variable"])

Always check the dataset units and climatology period before comparing the
result with model output. See :doc:`how_to_use` for matching and time-resolution
guidance.
