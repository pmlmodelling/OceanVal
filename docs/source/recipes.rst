Data Recipes
============

OceanVal provides built-in recipes for common gridded observational datasets.
A recipe supplies the dataset metadata and remote file locations so you can
register a comparison without specifying every observation detail manually.

Recipes are available for gridded data. Use the ``recipe`` argument with
:func:`oceanval.add_gridded_comparison` and provide the model variable that
should be compared with the observation.

How do recipes work?
--------------------

A recipe is a compact name for a complete gridded observation definition. It
does not download data when you call ``add_gridded_comparison``. Instead, the
recipe is resolved immediately into metadata and remote file locations, and
those details are stored in OceanVal's comparison definitions. When you later
run :func:`oceanval.matchup`, OceanVal accesses the recipe's observation files,
downloads or caches the required data as needed, and matches it with the model
output.

The process has four stages:

1. **Choose a recipe**: select one variable and one data source, such as
   ``{"nitrate": "woa23"}``.
2. **Resolve metadata**: OceanVal identifies the observation source, remote
   files, observation variable, units information, climatology setting, and
   report labels.
3. **Register the comparison**: ``add_gridded_comparison`` combines the
   recipe metadata with your model variable and stores the definition.
4. **Match the data**: ``matchup`` retrieves the observations, reads the
   model NetCDF files, and creates the model-observation matchup files.

Worked example: WOA23 nitrate
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following call asks OceanVal to compare the model's ``no3`` variable with
the WOA23 nitrate product:

.. code-block:: text

   oceanval.add_gridded_comparison(
       name="nitrate",                 # <--- report name
       model_variable="no3",           # <--- model NetCDF variable
       recipe={"nitrate": "woa23"},    # <--- observation recipe
       climatology=True,                # <--- climatological comparison
   )

The parts of the call mean:

``name="nitrate"``
   ``name`` is the short internal name used by OceanVal to identify the
   comparison and label report outputs.

``model_variable="no3"``
   This must match the variable name in the model NetCDF files. The recipe
   describes the observation; it does not guess or rename the model variable.

``recipe={"nitrate": "woa23"}``
   The key selects the observation variable and the value selects the source.
   OceanVal uses this pair to find the WOA23 metadata and remote observation
   files.

``climatology=True``
   This tells OceanVal to make a like-for-like climatological comparison. Use
   ``False`` when the comparison should retain all available years instead.

The resolution step can be pictured as follows:

.. code-block:: text

   {"nitrate": "woa23"}
          |
          |  variable + source identifier
          v
   find_recipe(...)
          |
          +--> observation source: WOA23
          +--> remote files: monthly nitrate NetCDF files
          +--> observation variable: n_an
          +--> climatology: True
          +--> report labels: nitrate concentration / Nitrate
          |
          v
   add_gridded_comparison(...)
          |
          +--> joins recipe metadata to model_variable="no3"
          +--> stores the comparison definition
          |
          v
   matchup(...)
          |
          +--> accesses or downloads the observation files
          +--> reads the model NetCDF output
          +--> regrids and matches model with observations
          +--> writes the matchup data for validation

For WOA23 temperature and salinity, ``start`` and ``end`` are also required
because those products are supplied as decadal climatologies. The selected
years determine which WOA23 period and remote files OceanVal uses.

Available recipes

Global datasets
~~~~~~~~~~~~~~~
.. csv-table:: Global built-in recipes
   :header: "Region", "Variable", "Recipe", "Dataset", "Water-column", "Example"
   :widths: 12, 16, 16, 32, 14, 24

   "Global", "Alkalinity", "``glodap``", "`GLODAPv2.2016b <https://www.glodap.info/>`_", "No", ":doc:`Full details <recipe_examples/alkalinity_glodap>`"
   "Global", "Chlorophyll", "``occci``", "`Ocean Colour CCI <https://esa-oceancolour-cci.org/>`_", "No", ":doc:`Full details <recipe_examples/chlorophyll_occci>`"
   "Global", "KD490", "``occci``", "`Ocean Colour CCI <https://esa-oceancolour-cci.org/>`_", "No", ":doc:`Full details <recipe_examples/kd490_occci>`"
   "Global", "Nitrate", "``woa23``", "`World Ocean Atlas 2023 <https://www.ncei.noaa.gov/products/world-ocean-atlas>`_", "Yes", ":doc:`Full details <recipe_examples/nitrate_woa23>`"
   "Global", "Oxygen", "``woa23``", "`World Ocean Atlas 2023 <https://www.ncei.noaa.gov/products/world-ocean-atlas>`_", "Yes", ":doc:`Full details <recipe_examples/oxygen_woa23>`"
   "Global", "pH", "``glodap``", "`GLODAPv2.2016b <https://www.glodap.info/>`_", "No", ":doc:`Full details <recipe_examples/ph_glodap>`"
   "Global", "Phosphate", "``woa23``", "`World Ocean Atlas 2023 <https://www.ncei.noaa.gov/products/world-ocean-atlas>`_", "Yes", ":doc:`Full details <recipe_examples/phosphate_woa23>`"
   "Global", "Salinity", "``woa23``", "`World Ocean Atlas 2023 <https://www.ncei.noaa.gov/products/world-ocean-atlas>`_", "Yes", ":doc:`Full details <recipe_examples/salinity_woa23>`"
   "Global", "Silicate", "``woa23``", "`World Ocean Atlas 2023 <https://www.ncei.noaa.gov/products/world-ocean-atlas>`_", "Yes", ":doc:`Full details <recipe_examples/silicate_woa23>`"
   "Global", "Temperature", "``cobe2``", "`COBE-SST 2 <https://psl.noaa.gov/data/gridded/data.cobe2.html>`_", "No", ":doc:`Full details <recipe_examples/temperature_cobe2>`"
   "Global", "Temperature", "``woa23``", "`World Ocean Atlas 2023 <https://www.ncei.noaa.gov/products/world-ocean-atlas>`_", "Yes", ":doc:`Full details <recipe_examples/temperature_woa23>`"


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
   recipe_examples/ammonium_nsbc
   recipe_examples/chlorophyll_nsbc
   recipe_examples/nitrate_nsbc
   recipe_examples/phosphate_nsbc
   recipe_examples/salinity_nsbc
   recipe_examples/silicate_nsbc
   recipe_examples/temperature_nsbc

The recipe dictionary must contain one variable and source identifier. For
example, ``{"temperature": "woa23"}`` selects temperature from WOA23.



Northwest European Shelf datasets
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``nsbc`` recipe provides North Sea Biogeochemical Climatology data for
chlorophyll, nitrate, phosphate, silicate, oxygen, temperature, and salinity.

.. csv-table:: Northwest European Shelf built-in recipes
   :header: "Region", "Variable", "Recipe", "Dataset", "Water-column", "Example"
   :widths: 22, 16, 16, 32, 14, 24

   "Northwest European Shelf", "Ammonium", "``nsbc``", "North Sea Biogeochemical Climatology", "Yes", ":doc:`Full details <recipe_examples/ammonium_nsbc>`"
   "Northwest European Shelf", "Chlorophyll", "``nsbc``", "North Sea Biogeochemical Climatology", "Yes", ":doc:`Full details <recipe_examples/chlorophyll_nsbc>`"
   "Northwest European Shelf", "Nitrate", "``nsbc``", "North Sea Biogeochemical Climatology", "Yes", ":doc:`Full details <recipe_examples/nitrate_nsbc>`"
   "Northwest European Shelf", "Oxygen", "``nsbc``", "North Sea Biogeochemical Climatology", "Yes", ":doc:`Full details <recipe_examples/oxygen_nsbc>`"
   "Northwest European Shelf", "Phosphate", "``nsbc``", "North Sea Biogeochemical Climatology", "Yes", ":doc:`Full details <recipe_examples/phosphate_nsbc>`"
   "Northwest European Shelf", "Salinity", "``nsbc``", "North Sea Biogeochemical Climatology", "Yes", ":doc:`Full details <recipe_examples/salinity_nsbc>`"
   "Northwest European Shelf", "Silicate", "``nsbc``", "North Sea Biogeochemical Climatology", "Yes", ":doc:`Full details <recipe_examples/silicate_nsbc>`"
   "Northwest European Shelf", "Temperature", "``nsbc``", "North Sea Biogeochemical Climatology", "Yes", ":doc:`Full details <recipe_examples/temperature_nsbc>`"

Each Example link opens a separate page containing the corresponding call.

Dataset notes
-------------


Always check the dataset units and climatology period before comparing the
result with model output. See :doc:`how_to_use` for matching and time-resolution
guidance.
