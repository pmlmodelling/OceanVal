Data Recipes
=============

To make life easier, oceanVal provides a number of built in recipes, which will allow you to easily validate common oceanic variables from data that is downloadable.

**Note**: recipes are only available for gridded data at present.


Overview
--------

This is carried out using the ``recipe`` parameter in the ``add_gridded_comparison`` function, as follows:


.. code-block:: python
    import oceanval

    oceanval.add_gridded_comparison(
        model_variable="foobar",
        recipe={"temperature": "cobe2"}
    )

This is a minimalist example, where you have said you want to matchup temperature from the (COBE2)[https://psl.noaa.gov/thredds/dodsC/Datasets/COBE2/sst.mon.mean.nc] sea surface temperature dataset with the model temperature, with variable name "foobar".

The recipe dictionary must contain exactly one key-value pair, where:

* **Key**: Variable name (e.g., "temperature", "nitrate")
* **Value**: Data source identifier (e.g., "cobe2", "woa23", "nsbc")

The table below summarizes the available recipes.

+-------------------+--------------+--------------------------+---------------------------------------+
| **Region**        | **Variable** | **Recipe**               | **Data source**                       |
+===================+==============+==========================+=======================================+
| Global            | Temperature  | {"temperature": "cobe2"} | COBE2 Sea Surface Temperature         |
+-------------------+--------------+--------------------------+---------------------------------------+
| Global            | Nitrate      | {"nitrate": "woa23"}     | World Ocean Atlas 2023                |
+-------------------+--------------+--------------------------+---------------------------------------+
| Global            | Phosphate    | {"phosphate": "woa23"}   | World Ocean Atlas 2023                |
+-------------------+--------------+--------------------------+---------------------------------------+
| Global            | Oxygen       | {"oxygen": "woa23"}      | World Ocean Atlas 2023                |
+-------------------+--------------+--------------------------+---------------------------------------+
| Global            | Silicate     | {"silicate": "woa23"}    | World Ocean Atlas 2023                |
+-------------------+--------------+--------------------------+---------------------------------------+
| Global            | Temperature  | {"temperature": "woa23"} | World Ocean Atlas 2023                |
+-------------------+--------------+--------------------------+---------------------------------------+
| Global            | Salinity     | {"salinity": "woa23"}    | World Ocean Atlas 2023                |
+-------------------+--------------+--------------------------+---------------------------------------+
| Global            | Chlorophyll  | {"chlorophyll": "occci"} | Ocean Colour CCI                      |
+-------------------+--------------+--------------------------+---------------------------------------+
| Global            | KD490        | {"kd490": "occci"}       | Ocean Colour CCI                      |
+-------------------+--------------+--------------------------+---------------------------------------+
| Global            | pH           | {"pH": "glodap"}         | Global Ocean Data Analysis Project v2 |
+-------------------+--------------+--------------------------+---------------------------------------+
| Global            | Alkalinity   | {"alkalinity": "glodap"} | Global Ocean Data Analysis Project v2 |
+-------------------+--------------+--------------------------+---------------------------------------+
| NW European Shelf | Chlorophyll  | {"chlorophyll": "nsbc"}  | North Sea Biogeochemical Climatology  |
+-------------------+--------------+--------------------------+---------------------------------------+
| NW European Shelf | Nitrate      | {"nitrate": "nsbc"}      | North Sea Biogeochemical Climatology  |
+-------------------+--------------+--------------------------+---------------------------------------+
| NW European Shelf | Phosphate    | {"phosphate": "nsbc"}    | North Sea Biogeochemical Climatology  |
+-------------------+--------------+--------------------------+---------------------------------------+
| NW European Shelf | Silicate     | {"silicate": "nsbc"}     | North Sea Biogeochemical Climatology  |
+-------------------+--------------+--------------------------+---------------------------------------+
| NW European Shelf | Oxygen       | {"oxygen": "nsbc"}       | North Sea Biogeochemical Climatology  |
+-------------------+--------------+--------------------------+---------------------------------------+
| NW European Shelf | Temperature  | {"temperature": "nsbc"}  | North Sea Biogeochemical Climatology  |
+-------------------+--------------+--------------------------+---------------------------------------+
| NW European Shelf | Salinity     | {"salinity": "nsbc"}     | North Sea Biogeochemical Climatology  |
+-------------------+--------------+--------------------------+---------------------------------------+






Available recipes for global gridded data
-----------------

COBE2 - Sea Surface Temperature
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Recipe**: {"temperature": "cobe2"} 

**Source**: COBE-SST 2 (NOAA Physical Sciences Laboratory)

**Vertical information**: Surface only

**URL**: https://psl.noaa.gov/thredds/dodsC/Datasets/COBE2/sst.mon.mean.nc

**Usage Example**:

.. code-block:: python

   oceanval.add_gridded_comparison(
       model_varianble ="foobar",
       recipe={"temperature": "cobe2"}
   )

COBE2 data is stored in the following units:

    temperature: degrees Celsius (°C)


WOA23 - World Ocean Atlas 2023
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Source**: NOAA World Ocean Atlas 2023

**Variables**: nitrate, phosphate, oxygen, silicate, temperature, salinity

**Vertical information**: Vertically resolved to 800m depth

**Recipes**: {"nitrate": "woa23"}, {"phosphate": "woa23"}, {"oxygen": "woa23"}, {"silicate": "woa23"}, {"temperature": "woa23"}, {"salinity": "woa23"}

Data is stored in the following units:

    **Nitrate**: micromoles per kg (µmol/kg)

    **Phosphate**: micromoles per kg (µmol/kg)

    **Oxygen**: micromoles per kilogram (µmol/kg)

    **Silicate**: micromoles per kg (µmol/kg)

    **Temperature**: degrees Celsius (°C)

    **Salinity**: practical salinity units (PSU)

**URL**: https://www.ncei.noaa.gov/products/world-ocean-atlas 


**Usage Example**:

.. code-block:: python

   oceanval.add_gridded_comparison(
       model_variable="foobar",
       recipe={"nitrate": "woa23"}
   )

**Note**: temperature and salinity are available for different decadal climatologies. You must therefore specify start and end years when using these recipes to ensure the correct data is downloaded. 

The climatological periods available are:

* 1955-1964

* 1965-1974

* 1975-1984

* 1985-1994

* 1995-2004

* 2005-2014

* 2015-2022

The start and end provided must fall within one of these periods. 
For example, if you want to validate against the 1995-2004 climatology, you would set start = 1995 and end = 2004 when calling the ``add_gridded_comparison`` function, as follows:

.. code-block:: python

   oceanval.add_gridded_comparison(
       model_variable="foobar",
       recipe={"temperature": "woa23"},
       start = 1995,
       end = 2004
   )

This data is vertically resolved, so if you want vertically resolved validation you will need to modify things as follows:

.. code-block:: python

   oceanval.add_gridded_comparison(
       model_variable="foobar" ,
       recipe={"nitrate": "woa23"},
       vertical = True
   )

Ocean Colour CCI - Chlorophyll and KD490
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


**Source**: ESA Ocean Colour Climate Change Initiative (OC-CCI) v6.0

**Variables**: chlorophyll, KD490

**Vertical information**: Surface only

**Recipe**: {"chlorophyll": "occci"}, {"kd490": "occci"}

**URL**: https://esa-oceancolour-cci.org/

**Usage Example**:
.. code-block:: python

   oceanval.add_gridded_comparison(
       model_variable="foobar",
       recipe={"chlorophyll": "occci"   }
   )
    oceanval.add_gridded_comparison(
         model_variable="foobar",
         recipe={"kd490": "occci"}

**Years available": monthly averages for 1998-2024

This data is stored in the following units:

    **Chlorophyll**: milligrams per cubic meter (mg/m³)

    **KD490**: inverse meters (m⁻¹)

GLODAPv2.2016b
-----------------
**Source**: Global Ocean Data Analysis Project version 2 (GLODAPv2.2016b)

**Variables**: pH, alkalinity

**Vertical information**: Surface only

**Recipes**: {"pH": "glodap"}, {"alkalinity": "glodap"}

**URL**: https://www.glodap.info/

**Usage Example**:

.. code-block:: python

   oceanval.add_gridded_comparison(
       model_variable="foobar",
       recipe={"pH": "glodap"}
   )
    oceanval.add_gridded_comparison(
         model_variable="foobar",
         recipe={"alkalinity": "glodap"}
    )
This data is stored in the following units:

    **pH**: total scale

    **Alkalinity**: micromoles per kilogram (µmol/kg)

**Note**: These are annual climatologies covering the years 1972-2013. Please read this reference before deciding a suitable simulation to use for comparison: https://essd.copernicus.org/articles/8/325/2016/.




Available recipes for the northwest European shelf
-----------------

NSBC - North Sea Biogeochemical Climatology
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Source**: North Sea Biogeochemical Climatology (University of Hamburg)

**Variables**: ammonium, nitrate, phosphate, silicate, chlorophyll, oxygen, temperature, salinity

**Vertical information**: Vertically resolved climatologies 

**URL**: https://www.hereon.de/en/institute/coastal-research/projects/north-sea-biogeochemical-climatology-nsbc.php


**Usage Examples**:

.. code-block:: python

   oceanval.add_gridded_comparison(
       model_variable="foobar",
       recipe={"chlorophyll": "nsbc"}
   )
   
   oceanval.add_gridded_comparison(
        model_variable="foobar",
       recipe={"nitrate": "nsbc"}
   )

   oceanval.add_gridded_comparison(
        model_variable="foobar",
       recipe={"phosphate": "nsbc"}
   )

   oceanval.add_gridded_comparison(
        model_variable="foobar",
       recipe={"silicate": "nsbc"}
   )
    oceanval.add_gridded_comparison(
          model_variable="foobar",
         recipe={"oxygen": "nsbc"}
    )
    oceanval.add_gridded_comparison(
          model_variable="foobar",
         recipe={"temperature": "nsbc"}
    )
    oceanval.add_gridded_comparison(
            model_variable="foobar",
         recipe={"salinity": "nsbc"}
    )


This data is vertically resolved, so if you want vertically resolved validation you will need to modify things as follows:

.. code-block:: python

   oceanval.add_gridded_comparison(
            model_variable="foobar",
       recipe={"nitrate": "nsbc"},
       vertical = True
   )


NSBC data is stored in the following units:

    **Phosphate**: millimoles per liter (mmol/L)

    **Nitrate**: millimoles per liter (mmol/L)

    **Ammonium**: millimoles per liter (mmol/L)

    **Silicate**: millimoles per liter (mmol/L)

    **Chlorophyll**: milligrams per cubic meter (mg/m³)

    **Oxygen**: milliliters per liter (ml/L)

    **Temperature**: degrees Celsius (°C)

    **Salinity**: practical salinity units (PSU)