Data Recipes
============

OceanVal provides built-in recipes for common gridded observational datasets.
A recipe supplies the dataset metadata and remote file locations so you can
register a comparison without specifying every observation detail manually.

Recipes are available for gridded data. Use the ``recipe`` argument with
:func:`oceanval.add_gridded_comparison` and provide the model variable that
should be compared with the observation:

.. _recipe-example:

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

The recipe dictionary must contain one variable and source identifier. For
example, ``{"temperature": "woa23"}`` selects temperature from WOA23.

Available recipes
-----------------

Global datasets
~~~~~~~~~~~~~~~

.. list-table:: Global built-in recipes
   :header-rows: 1
   :widths: 12 16 16 32 24

   * - Region
     - Variable
     - Recipe
     - Dataset
     - Example
   * - Global
     - Temperature
     - ``cobe2``
     - COBE-SST 2
     - :ref:`Call <recipe-example>`
   * - Global
     - Nitrate
     - ``woa23``
     - World Ocean Atlas 2023
     - :ref:`Call <recipe-example>`
   * - Global
     - Phosphate
     - ``woa23``
     - World Ocean Atlas 2023
     - :ref:`Call <recipe-example>`
   * - Global
     - Oxygen
     - ``woa23``
     - World Ocean Atlas 2023
     - :ref:`Call <recipe-example>`
   * - Global
     - Silicate
     - ``woa23``
     - World Ocean Atlas 2023
     - :ref:`Call <recipe-example>`
   * - Global
     - Temperature
     - ``woa23``
     - World Ocean Atlas 2023
     - :ref:`Call <recipe-example>`
   * - Global
     - Salinity
     - ``woa23``
     - World Ocean Atlas 2023
     - :ref:`Call <recipe-example>`
   * - Global
     - Chlorophyll
     - ``occci``
     - Ocean Colour CCI
     - :ref:`Call <recipe-example>`
   * - Global
     - KD490
     - ``occci``
     - Ocean Colour CCI
     - :ref:`Call <recipe-example>`
   * - Global
     - pH
     - ``glodap``
     - GLODAPv2.2016b
     - :ref:`Call <recipe-example>`
   * - Global
     - Alkalinity
     - ``glodap``
     - GLODAPv2.2016b
     - :ref:`Call <recipe-example>`

Northwest European Shelf datasets
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``nsbc`` recipe provides North Sea Biogeochemical Climatology data for
chlorophyll, nitrate, phosphate, silicate, oxygen, temperature, and salinity.

.. code-block:: python

   oceanval.add_gridded_comparison(
       name="oxygen",
       model_variable="oxygen",
       recipe={"oxygen": "nsbc"},
       climatology=True,
   )

Dataset notes
-------------

COBE-SST 2
~~~~~~~~~~

The ``cobe2`` recipe provides global sea-surface temperature from NOAA's
Physical Sciences Laboratory. The data are surface-only and reported in
degrees Celsius.

See the `COBE2 dataset page <https://psl.noaa.gov/data/gridded/data.cobe2.html>`_.

World Ocean Atlas 2023
~~~~~~~~~~~~~~~~~~~~~~

The ``woa23`` recipe supports nitrate, phosphate, oxygen, silicate, temperature,
and salinity. Nutrient and temperature/salinity products are vertically
resolved, with data available to approximately 800 m depending on the product.

Temperature and salinity use decadal climatologies. Set ``start`` and ``end``
within one of the supported periods:

* 1955-1964
* 1965-1974
* 1975-1984
* 1985-1994
* 1995-2004
* 2005-2014
* 2015-2022

See the `World Ocean Atlas page <https://www.ncei.noaa.gov/products/world-ocean-atlas>`_.

Ocean Colour CCI
~~~~~~~~~~~~~~~~

The ``occci`` recipe provides surface chlorophyll and KD490. Chlorophyll is
reported in milligrams per cubic metre and KD490 in inverse metres.

See the `Ocean Colour CCI website <https://esa-oceancolour-cci.org/>`_.

GLODAPv2.2016b
~~~~~~~~~~~~~~

The ``glodap`` recipe provides annual climatologies of pH and alkalinity.
The products cover 1972-2013 and are surface-only. pH is reported on the total
scale and alkalinity in micromoles per kilogram.

See the `GLODAP website <https://www.glodap.info/>`_ and the
`GLODAPv2 reference <https://doi.org/10.5194/essd-8-325-2016>`_.

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
