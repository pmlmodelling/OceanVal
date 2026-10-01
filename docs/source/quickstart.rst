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

The OceanVal window
-------------------

The quickest way needs no Python at all. In a terminal, in the directory to
work in, run:

.. code-block:: console

   oceanval

``OceanVal`` works too. A page opens in your web browser that takes you
through these steps:

1. **Choose** to match up new data and validate it, to match up only, or to
   validate matchups made earlier.
2. **Simulation**: where the model output is, how many directories down its
   files are, which files to skip or keep (the file filters), and the domain.
   Type the directory, with folders suggested as you go, or pick
   it with **Browse…**, which looks through the folders on the machine
   OceanVal runs on, so it works on a remote machine too. As you type, the
   page counts the files that pass the filters. The next page starts with
   years inferred from their names, which you can change there. It also asks
   where to save the matchups and the report: the
   directory you started ``oceanval`` in, unless you choose another. To
   validate matchups made earlier, you choose the report's options instead.
3. **Own data**: whether you have observations of your own, as well as
   OceanVal's built-in datasets. If you do, a page for point data (csv
   files) and one for gridded data (netCDF) let you add them one at a time,
   with every argument of ``add_point_comparison`` or
   ``add_gridded_comparison``; the ones that have to be given are marked in
   red. Skip a page if you have none of that kind. The calls are written
   into the matchup script.
4. **Recipes**: the ``create_recipes`` window, to check the model variables
   found and choose the observations to validate against. A dataset
   validated through the water column (Vertical) needs a thickness before
   you can carry on.
5. **Units**: a table of the units of every gridded and point matchup, read
   from the model's netCDF files and, for the observations, from the recipes
   (the Units column on the recipes page) or from your own netCDF file. Where
   OceanVal thinks they differ, it suggests a multiplier and an adder for the
   observations, in red and bold, and says what it assumed, such as a seawater
   density of 1025 kg/m³ between per kilogram and per volume. It can get this
   wrong, so check every row, and fill in any it could not work out. Your own
   point data is csv files, which have no units, so it is up to you to make
   sure they match the model's. The units always have to be confirmed, with a
   box under the tables, before the button starts the matchup. The
   conversions are written into the matchup script as ``obs_multiplier`` and
   ``obs_adder``.
6. **Files**: the page says it is identifying the files that meet your
   criteria, then shows what it found as a table: each variable, its model
   variable, the observations it is compared with and the files it is in,
   with **List all files** for each (OceanVal applies temporal subsetting to
   them). Carry on if the matchups are right; No stops the run.
7. **Report** (to match up and validate): "One last thing... How would you
   like your validation report?" The report's options, asked for before
   anything is matched up: a subregion to validate, regional summaries,
   fixed colour scales, PDF and Word versions, a zipped copy, and a concise
   or detailed report. The report is built beside the matchups, in the
   directory chosen in step 2. **Back** shows the matchups again. The options
   are written into the matchup script's ``validate()`` call.
8. **Run**: matchup, then, to validate as well, ``validate()`` with the
   report's options. The output appears as it comes, in the page and in the
   terminal, and anything else OceanVal asks, such as whether to try again
   for observations a server could not supply, is asked in the page.

The script it runs is written first, to ``matchup.py`` unless you choose
another name, so you can read it, and run it again later with
``python matchup.py``.

If ``oceanval`` cannot open a browser for you, it prints the link to open.
VS Code forwards its port for you; over plain SSH, choose the port with
``--port`` and forward it first: ``oceanval --port 8765``, with
``ssh -L 8765:127.0.0.1:8765 you@server``.

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
