How to use oceanVal
=====================

Validating simulations using oceanVal involves three steps:

    **1**. Register the observational datasets you want to use for validation
    **2**. Matchup the model simulation output with the observational datasets
    **3**. Calculate validation statistics, generate plots and create an html summary of the performance of the simulation

**You should always create a new directory prior to running oceanVal for a new simulation, and then run all oceanVal commands from within that directory.**

Step 1: Register observational datasets
------------------------------------

You first need to register the observational datasets you want to use for validation. 
This involves specifying the location of the data files and any necessary metadata.
You can register both gridded and in-situ observational datasets using the `oceanval.add_point_comprison` and `oceanval.add_gridded_comparison` functions. 

**Setting up point (in-situ) observational data**

To register an in-situ observational dataset, you will need to specify the following:

- `name`: A name for the dataset, e.g. "temperature". This is so that oceanVal can keep track of things. You can call this what you want, but it can only contain numbers and letters.
- `source`: The source of the observational data (e.g. "NOAA"). 
- `model_variable`: A string specifying the name of the model variable to compare against the observations. 
- `obs_path`: The path to a file or directory containing the observational data files.

Note: when specifying a directory as `obs_path` ensure that the directory only contains files relevant to the observational variable being registered, as oceanVal will recursively identify and use all netCDF files in the directory.

The following optional parameters can also be specified:

- `source_info`: Additional information about the source of the data (e.g. publication details)
- `short_name`: A short name for the observational variable (e.g. "temp" for temperature)
- `short_title`: A short title for plots (e.g. "Nitrate Concentration")
- `long_name`: A long name for the observational variable (e.g. "sea surface temperature")
- `vertical`: A boolean indicating whether vertical validation should be carried out. This defaults to False, so only surface validation will occur.
- `start`: The first year of observations to use. If not specified, all years in the data will be used. 
- `end`: The last year of observations to use. If not specified, all years in the data will be used.
- `obs_multiplier`: A multiplier to apply to the observational data (e.g. to convert units). This defaults to 1.0 (no change). 
- `obs_adder`: An adder to apply to the observational data (e.g. to convert units). This defaults to 0.0 (no change). For example, set to 273.15 to convert from Kelvin to Celsius.
- `binning`: Specify if you want data to be spatially binned to a specific lon/lat resolution. This is of the format [lon_bin_size, lat_bin_size] in degrees. If not specified, no binning will be applied.

An example is shown below:

.. code:: ipython3

    oceanval.add_point_comparison(
        name="nitrate",
        source = "ICES",
        source_info = "In-situ observations from the International Council for the Exploration of the Sea"
        short_name = "nitrate concentration"
        model_variable="temp",
        obs_path="/path/to/obs_data/",
    )

.. admonition:: How does oceanVal handle variable names?

    You can use whatever you want for the `name` parameter when registering observational datasets. This is only used internally by oceanVal to keep track of things, to name files etc.
    Reports and plots will use the `short_name`, `long_name` and `short_title` parameters for labelling. If you want a better looking report, you should set these parameters.

    You can only validate variables using a single gridded and a single point (in-situ) dataset each time you run a validation.



**Setting up gridded observational data**

To register a gridded observational dataset, you will need to specify the following:

- `name`: A name for the dataset, e.g. "temperature". This is so that oceanVal can keep track of things.
- `source`: The source of the observational data (e.g. "CMEMS"). 
- `model_variable`: A string specifying the name of the model variable to compare against the observations.
- `obs_path`: The path to the directory containing the observational data files.
- `obs_variable`: A string specifying the name of the variable in the observational data files.
- `climatology`: A boolean indicating whether the observational data is a climatology. 

Note: if you do not provide `obs_variable`, oceanVal will assume there is only one variable in the observational data files, and will use that variable for validation. 

The following optional parameters can also be specified:

- `source_info`: Additional information about the source of the data (e.g. publication details)
- `short_name`: A short name for the observational variable (e.g. "oxygen concentration")
- `long_name`: A long name for the observational variable (e.g. "dissolved oxygen concentration")
- `short_title`: A short title for plots (e.g. "Oxygen Concentration")
- `vertical`: A boolean indicating whether vertical validation should be carried out. This defaults to False, so only surface validation will occur.
- `start`: The first year of observations to use for validation.
- `end`: The last year of observations to use for validation.
- `obs_multiplier`: A multiplier to apply to the observational data (e.g. to convert units). This defaults to 1.0 (no change).
- `obs_adder`: An adder to apply to the observational data (e.g. to convert units). This defaults to 0.0 (no change). For example, set to 273.15 to convert from Kelvin to Celsius.

An example is shown below:

.. code:: ipython3

    oceanval.add_gridded_comparison(
        name="oxygen",
        source = "CMEMS",
        source_info = "Gridded observations from the Copernicus Marine Environment Monitoring Service"
        short_name = "oxygen concentration"
        model_variable="oxygen",
        obs_variable="O2_concentration",
        obs_path="/path/to/obs_data/",
        climatology=False,
    )


**Be consistent**

If you are registering the same variable separate for point and gridded data, make sure you are giving the same `short_name`, `long_name` and `short_title` for both datasets. This will ensure that plots and statistics are labelled consistently.
You will get an error if you are inconsistent.


.. admonition:: How does oceanVal handle gridded data?

    oceanVal works on the basis that gridded data can be converted to one of the following:

    1. A time series of multi-year monthly averages for each grid cell
    2. A climatological monthly average for each grid cell 
    3. A climatological annual average for each grid cell

    If you provide multi-year observational data, oceanVal will calculate a mult-year observational average, which is compared with the model in a like-for-like manner.    

    If you provide single-year observational data with monthly resolution, oceanVal will generate a comparable climatological monthly average from the model simulation output for comparison.
    This will be based on the year range you have specified.

    If you have provided a single-year observational dataset with only one time step, oceanVal will assume this is a climatological annual average.
    A model climatological annual average will be generated from the simulation output for comparison.

    **The simulation output will always be regridded to the observational grid.**



Step 2: Matchup model output with observations
--------------------------------------
Once you have registered your observational datasets, you can matchup the model simulation output with the observations using the `oceanval.matchup` function.

You will need to specify the following:

- `sim_dir`: The path to the directory containing the model simulation output files.
- `start`: The first year of the simulation to use for validation. 
- `end`: The last year of the simulation to use for validation.
- `cores`: The number of CPU cores to use for parallel processing.
- `lon_lim`: The longitude limits for the validation region (e.g. [-180, 180]).
- `lat_lim`: The latitude limits for the validation region (e.g. [-90, 90]).

The following variable is required if you are carrying out vertical validation: 

- `thickness`: Either "z_level" or a string specifying the name of the variable in the model output files that contains the cell thickness information.

The following optional parameters can also be specified:

- `n_dirs_down`: The number of directory levels to search down for model output files. This defaults to 2, assuming files are stored in for example a YYYY/MM/ structure.
- `overwrite`: A boolean indicating whether to overwrite existing matchup files. This defaults to False.
- `ask`: A boolean indicating whether to ask for confirmation before overwriting existing matchup files. This defaults to True.
- `cache`: A boolean indicating whether to cache intermediate results. This defaults to False.
- `exclude`: A list of strings that should not appear in any simulation files paths. 
- `out_dir`: The path to the directory where matchup files should be saved. If not specified, matchup files will be saved in the execution directory.
- `point_time_res`: The time resolution for the point (in-situ) observation matchup. This defaults ["year", "month", "day"] for totally precise matchups. Set to ["month", "day"], if you want to compare climatological simulation output with observations.
- `n_check`: The number of files to check when identifying the file naming convention. oceanVal checks all files in a random subdirectory. Set n_check for a random subset in cases where all simulation files are in a single directory. 
- `as_missing`: A float or list of floats providing a range , i.e [min, max], specifying values to be treated as missing in the model output.

An example is shown below:

.. code:: ipython3

    oceanval.matchup(
        sim_dir="/path/to/simulation/output/",
        start=2000,
        end=2010,
        cores=4,
        lon_lim=[-80, 0],
        lat_lim=[20, 60],
        thickness="cell_thickness",
    )

**Note**: If you are validating a simulation with only monthly resolution, then you probably want to set the `point_time_res` parameter to `["year", "month"]` when matching up in-situ observations.
This will result in day of year being ignored when matching up observations with the simulation output. If you use the default for `point_time_res`, then very few matchups will be found, as the day of year in the observations will almost never match that in the simulation output. 

**Summing up simulation output**

Sometimes observational data needs to be compared with the sum of multiple model variable.
You can do this by setting something like "var1+var2+var3" as the `model_variable` when registering the observational dataset.

.. admonition:: How does oceanVal handle in-situ data?

    oceanVal will handle in-situ data observational data depending on which of the following are provided:

    - year 
    - month
    - day
    - depth

    If depth is not provided, oceanVal will assume this represents a surface observational dataset. 
    If you do provide depth, oceanVal will interpolate to all available depth-resolved data if you have specified `vertical=True` in `add_point_comparison`, otherwise it will only use the top 5m of data.
    By default it only looks at the surface. 

    If you provide year, month and day, oceanVal will look for model output at the exact date of the observation.

    If you provide year and month, but not day, oceanVal will look for model output for the whole month of the observation, and use the monthly average from the simulation.

    If you only provide year, oceanVal will look for model output for the whole year of the observation, and use the annual average from the simulation.

    If no time information is provided, oceanVal will use the multi-year average from the simulation output for comparison with the observation.

    In some cases, you may want to ignore the year information in the observational data.
    For example, you may have only a 1-year simulation and you want to validate based on all available years of observations, only using month and day information in the observational data.
    In this case, you can set the `point_time_res` parameter in the `oceanval.matchup` function to specify which time information to use when matching up in-situ observations with the simulation output.
    Set this to `["month", "day"]` to ignore year information when matching up observations with the simulation output.


.. admonition:: Where does oceanVal save matchup files?

    By default, oceanVal will save matchup files in the directory where you run the `oceanval.matchup` function.
    You can find the files in oceanval_matchups/gridded or oceanval_matchups/point subdirectories.

    Gridded matchups will end with ".nc", while point matchups will end with ".csv".
    In each case, the model output will be named "model", while the observations will be named "observation".

Step 3: Calculate validation statistics and generate html summary
--------------------------------------

Once you have matched up the model simulation output with the observations, you can calculate validation statistics and generate plots using the `oceanval.validate` function.

You can do this as follows:

.. code:: ipython3

    oceanval.validate()
This must be run in the same directory where the matchup files were created.

The following options are available:

- `variables`: A list of variable names to validate. This must match those supplied as `name`. If not specified, all registered variables will be validated. 
- `lon_lim`: The longitude limits for the validation region (e.g. [-180, 180]).
- `lat_lim`: The latitude limits for the validation region (e.g. [-90, 90]).
- `region`: A string specifying the region being validated. Only "global" and "nwes" (northwest European Shelf are currently available).
- `concise`: A boolean indicating whether to generate a concise html summary page. This defaults to True.

This will then generate and open an html page that can be viewed in a web browser.