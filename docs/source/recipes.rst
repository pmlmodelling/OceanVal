Data Recipes
============

OceanVal provides built-in recipes for many popular observational datasets.
Downloading and storing data can be annoying and tedious, and recipes take
care of it for you.

Recipes are available for gridded data. Use the ``recipe`` argument with
:func:`oceanval.add_gridded_comparison` and provide the model variable that
should be compared with the observation.

We can illustrate how they work with an example.  
The following call asks OceanVal to compare the model's ``thetao`` variable with the COBE2 temperature dataset. The recipe dictionary
``{"temperature": "cobe2"}`` tells OceanVal to use the COBE2 recipe for the temperature variable.

.. code-block:: text

   oceanval.add_gridded_comparison(
       name="temperature",                 # <--- report name
       model_variable="thetao",           # <--- model NetCDF variable
       recipe={"temperature": "cobe2"},    # <--- observation recipe
       climatology=True,                # <--- climatological comparison
   )

The parts of the call mean:

- ``name`` is the short name OceanVal uses in reports.
- ``model_variable`` is the variable name in the model NetCDF output.
- ``recipe`` is a dictionary that must contain one variable and source
  identifier. For example, ``{"temperature": "woa23"}`` selects temperature
  from WOA23.
- ``climatology`` is a boolean that sets whether to compare climatological
  means or all available years. Set ``climatology=True`` for a climatological
  comparison, or ``climatology=False`` to compare all available years.

How are recipes processed?
--------------------------

OceanVal will automatically download the observational data when the
:func:`oceanval.matchup` function is called. In most cases this happens via
THREDDS servers, which makes things efficient: OceanVal only downloads what
is needed. Once the data is downloaded, the model and observations are
regridded to a common spatial grid, and model and observational data are
averaged per month and year, where appropriate.

What recipes are available?
---------------------------


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
