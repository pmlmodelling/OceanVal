Examples
========

The examples below use the public OceanVal API. For a complete first run,
start with :doc:`quickstart`.

Select variables and model files
--------------------------------

``matchup`` discovers model files below ``sim_dir``. Use ``n_dirs_down`` when
files are nested in a numeric year/month directory structure, and use
``exclude`` or ``require`` when several simulations share a directory.

.. code-block:: python

   import oceanval

   oceanval.matchup(
       sim_dir="/path/to/model/output",
       start=2000,
       end=2010,
       n_dirs_down=2,
       cores=4,
       exclude=["initial_conditions"],
       require=["experiment_1"],
   )

Control time and spatial matching
---------------------------------

For monthly model output, ignore the day of year when matching point
observations. Longitude and latitude limits can reduce the area processed.

.. code-block:: python

   oceanval.matchup(
       sim_dir="/path/to/model/output",
       start=2000,
       end=2010,
       point_time_res=["year", "month"],
       lon_lim=[-10, 10],
       lat_lim=[40, 60],
   )

If the model does not contain cell thickness metadata, pass a thickness
variable name or a path to a thickness file with ``thickness``.

Compare validation reports
--------------------------

After producing reports for multiple simulations, compare them with
``oceanval.compare``. The mapping keys become the model names in the report.

.. code-block:: python

   import oceanval

   oceanval.compare(
       model_dict={
           "control": "/path/to/control/output",
           "experiment": "/path/to/experiment/output",
       },
       view=True,
       ask=True,
   )

Customize and rebuild a report
------------------------------

Generated reports contain notebooks under ``oceanval_report/notebooks``.
After editing a notebook, rebuild the report from its parent directory:

.. code-block:: python

   oceanval.rebuild(data_dir="/path/to/validation/output")

The rebuild operation uses the edited notebooks and regenerates the HTML
report. Keep a copy of the original notebooks if you need to compare changes.
