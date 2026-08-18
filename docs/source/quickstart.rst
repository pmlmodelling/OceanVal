Quickstart
==========

This guide shows the shortest path from a model output directory to an HTML
validation report. It assumes the model files are NetCDF files stored either
in one directory or in numeric ``YYYY/MM`` subdirectories.

Install
-------

Install the released package from conda-forge:

.. code-block:: console

   conda install -c conda-forge oceanval

For development installation, see :doc:`installing`.

Match model output with observations
------------------------------------

Register the observation datasets you need, then run ``matchup`` from a
working directory where OceanVal can write ``oceanval_matchups``:

.. code-block:: python

   import oceanval

   oceanval.add_gridded_comparison(
       name="temperature",
       source="WOA23",
       model_variable="thetao",
       recipe={"temperature": "woa23"},
       start=2005,
       end=2014,
       climatology=True,
   )

   oceanval.matchup(
       sim_dir="/path/to/model/output",
       start=2005,
       end=2014,
       surface={"gridded": ["temperature"]},
       cores=4,
   )

The exact model variable and recipe depend on your model and observations.
See :doc:`obs_data` and :doc:`how_to_use` before adapting this example.

Build the report
----------------

Run validation from the directory containing ``oceanval_matchups``:

.. code-block:: python

   oceanval.validate()

The generated report is written below ``oceanval_report`` and opened in a
browser when the build completes. Use ``oceanval.validate("pdf")`` when a PDF
is required.

Troubleshooting
---------------

If no matchups are produced, check the model directory structure, variable
names, time resolution, units, and climatology setting. The most common issue
with monthly model output is using daily matching precision; see the time
resolution guidance in :doc:`how_to_use`.
