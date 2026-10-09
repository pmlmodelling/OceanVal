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

The OceanVal App
----------------

The quickest way needs no Python at all. In a terminal, in the directory to
work in, run:

.. code-block:: console

   oceanval

A page opens in your web browser that takes you from a folder of model
output to a validation report:

1. **Choose** what to do: match up and validate, match up only, or validate
   matchups made earlier.
   Or register recipes of your own for observations you use again, which are
   saved in a ``.oceanvalrc`` file (see :doc:`recipes`).
2. **Simulation**: where the model output is, and which files to use.
3. **Own data**: add observations of your own, if you have any, for this
   matchup only or saved as a recipe for later ones too.
4. **Recipes**: check the model variables found, and choose the
   observations to validate against.
5. **Units**: check and confirm the units, with conversions suggested where
   they differ.
6. **Files** and **Report**: check the matchups, then choose the report's
   options.
7. **Run**: the matchup and the report, with the output shown as it comes.

**Back**, on every step after the first, keeps what you have entered, so you
can go back to fix a mistake without starting again.

Closing the browser window quits ``oceanval`` in the terminal, within about
15 seconds, stopping anything it is running, whichever browser you use. So
do **Quit** (which is instant) and Ctrl+C.

To see how it works first, choose **Try a demo**, below the four choices. It
downloads a CMIP6 climate model's sea surface temperature, sea surface
salinity and surface nitrate (50 MB) and takes you through the same steps with
the options filled in: temperature is matched up with COBE-SST 2, and salinity
and nitrate with the World Ocean Atlas 2023. The units step suggests
converting the observed nitrate, which you check as you would for your own
model. It shows how OceanVal works, not how to validate a climate model, which needs many years
of output rather than one. It creates a directory called ``oceanval_demo``,
with the data, matchups and report in it: remove it when you have finished.

The script it runs is written first, to ``matchup.py``, so you can read it
and run it again later. Every step is described on the website, in
`Validating from your browser
<https://pmlmodelling.github.io/OceanVal/browser.html>`_, including how to
use it on a remote machine.

The sections below do the same in Python.

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
