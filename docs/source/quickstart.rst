Quickstart
==========

This guide shows the shortest path from a model output directory to an HTML
validation report: three function calls. It assumes your model files are
CF-compliant NetCDF files stored either in one directory or in numeric
``YYYY/MM`` subdirectories.

Install
-------

Install the released package from conda-forge:

.. code-block:: console

   conda install -c conda-forge oceanval

For full installation options, see :doc:`installing`.

Match model output with observations
------------------------------------

Work from a fresh, empty directory: OceanVal writes its matchup files and
report there. Register the observations you need, then run ``matchup``:

.. code-block:: python

   import oceanval

   # 1. Register: compare the model variable "thetao" with WOA23 temperature
   oceanval.add_gridded_comparison(
       name="temperature",
       model_variable="thetao",
       recipe={"temperature": "woa23"},
       start=2005,
       end=2014,
       climatology=True,
   )

   # 2. Match: pair model output with the observations
   oceanval.matchup(
       sim_dir="/path/to/model/output",
       start=2005,
       end=2014,
       cores=4,
   )

Replace ``thetao`` with the temperature variable name used in your model's
NetCDF files. OceanVal will scan ``sim_dir``, report the file pattern it has
identified, and ask you to confirm before matching. The matched data is
written to an ``oceanval_matchups`` directory.

To use other variables or your own observation files, see :doc:`recipes` and
:doc:`how_to_use`.

Build the report
----------------

Run validation from the same directory:

.. code-block:: python

   # 3. Report: compute statistics and build the HTML report
   oceanval.validate()

The report is written below ``oceanval_report`` and opens in your browser
when the build completes. It includes climatology maps, bias maps,
seasonality analysis, spatial correlation tables, and full documentation of
the methods used.

Next steps
----------

* Add more variables: each :doc:`recipe <recipes>` is one extra
  ``add_gridded_comparison`` call.
* Validate against your own gridded or in-situ data: see :doc:`how_to_use`.
* Compare several simulations side by side with :func:`oceanval.compare`.

Troubleshooting
---------------

If no matchups are produced, check the model directory structure, variable
names, time resolution, units, and climatology setting. The most common issue
with monthly model output and in-situ observations is using daily matching
precision; see the time resolution guidance in :doc:`how_to_use`, or browse
the :doc:`Q&A <q_a>`.
