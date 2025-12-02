OceanVal Q&A
=====================

How do I validate multiple simulations?
------------------------------------

If you want to validate multiple simulations with a single script, 
you should make use of the `out_dir` option in the 
`oceanval.matchup` and `data_dir` and `output_dir` options in the  `oceanVal.validate` functions.
These will enable oceanVal to store output in separate folders.

When your code has finished validating one simulation, you should reset things as follows:

.. code:: ipython3

    oceanval.reset()

This will clear any of the observational matchups you have previous added using 
`oceanval.add_point_comparison` and `oceanval.add_gridded_comparison` functions and will give
you a clean slate to validate the next simulation.



How do I speed up validations? 
------------------------------------

By default, oceanVal will use 6 CPU cores to carry out matchups. 
If you want to speed things up, change this number in the `oceanval.matchup` function using the `cores` argument.

For example, to use 12 cores:

.. code:: ipython3

    oceanval.matchup(..., cores=12, .... )


How do I view the data matchups?
------------------------------------

Data matchups are stored in the oceanval_matchups directory inside the output directory you specified.
Gridded data will be in the "gridded" directory and point data in the "point" directory.
The folder structure should be self-explanatory, with the gridded data stored as .nc files
and the point data stored as .csv files.

I get a "TypeError: clean_all() takes 0 positional arguments but 2 were given". What do I do?
------------------------------------

This message should be ignored. It is a quirk in the behaviour of a dependency of the jupyter book package, and it does not mean anything is going wrong.

Can I validate using gridded observational data from openDAP?
------------------------------------

Yes. oceanVal can access gridded observational data from openDAP servers.
The file path will just need to end with ".nc".

You can use the `oceanval.add_gridded_comparison` function to add the observational data as usual,
but you just need to set `thredds=True`.

For example, to validate model temperature against the COBE SST data hosted by NOAA PSL:

.. code:: ipython3

    oceanval.add_gridded_comparison(
        name="temperature",
        obs_path = "https://psl.noaa.gov/thredds/dodsC/Datasets/COBE2/sst.mon.mean.nc"
        obs_variable="sst",
        model_variable="temperature",
        thredds=True
    )



