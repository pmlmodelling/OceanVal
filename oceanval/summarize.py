import copy
import os
import webbrowser   
import xarray as xr
import importlib
import glob
import pathlib
import warnings
import pickle
import nctoolkit as nc
import random
import pandas as pd
import re
import dill

from shutil import copyfile
from oceanval.session import session_info
from oceanval.parsers import summaries, generate_mapping_summary
from oceanval.utils import extension_of_directory
from oceanval.matchall import get_time_res, is_z_up
from tqdm import tqdm
example_files = dict()
random_files = []




def extract_variable_mapping(folder, exclude=[], n_check=None):
    """
    Find paths to netCDF files
    Parameters
    -------------
    folder : str
        The folder containing the netCDF files
    exclude : list
        List of strings to exclude

    Returns
    -------------
    all_df : pd.DataFrame
        A DataFrame containing the paths to the netCDF files
    """

    # add restart to exclude
    exclude.append("restart")

    n = 0
    while True:

        levels = session_info["levels_down"]

        new_directory = folder + "/"
        if levels > 0:
            for i in range(levels + 1):
                dir_glob = glob.glob(new_directory + "/**")
                # randomize dir_glob

                random.shuffle(dir_glob)
                for x in dir_glob:
                    # figure out if the the base directory is an integer
                    try:
                        if levels != 0:
                            y = int(os.path.basename(x))
                        new_directory = x + "/"
                    except:
                        pass
        options = glob.glob(new_directory + "/**.nc")
        # if n_check is not None and an integer, limit options to n_check
        if n_check is not None and isinstance(n_check, int):
            options = random.sample(options, min(n_check, len(options)))
        if True:
            options = [x for x in options if "restart" not in os.path.basename(x)]

        if len([x for x in options if ".nc" in x]) > 0:
            break

        n += 1

        if n > 10* 10000:
            raise ValueError("Unable to find any netCDF files in the provided directory. Check n_dirs_down arg and simulation directory structure.")

    all_df = []
    print("********************************")
    print("Parsing model information from netCDF files")

    # remove any files from options if parts of exclude are in them
    for exc in exclude:
        options = [x for x in options if f"{exc}" not in os.path.basename(x)]
    
    # handle required
    if session_info["require"] is not None:
        for req in session_info["require"]:
            options = [x for x in options if f"{req}" in os.path.basename(x)]

    print("Searching through files in a random directory to identify variable mappings")
    # randomize options
    for ff in tqdm(options):
        random_files.append(ff)
        ds = nc.open_data(ff, checks=False)
        stop = True
        ds_dict = generate_mapping_summary(ds)
        try:
            ds_dict = generate_mapping_summary(ds)
            stop = False
        # output error and ff
        except:
            pass
        if stop:
            continue

        ds_vars = ds.variables

        if len([x for x in ds_dict.values() if x is not None]) > 0:
            new_name = ""
            for x in os.path.basename(ff).split("_"):
                try:
                    y = int(x)
                    if len(new_name) > 0:
                        new_name = new_name + "_**"
                    else:
                        new_name = new_name + "**"
                except:
                    if len(new_name) > 0:
                        new_name = new_name + "_" + x
                    else:
                        new_name = x
            # replace integers in new_name with **

            new_dict = dict()
            for key in ds_dict:
                if ds_dict[key] is not None:
                    #new_dict[ds_dict[key]] = [key]
                    new_dict[key] = [ds_dict[key]]
            # new_name. Replace numbers between _ with **

            # replace integers with 4 or more digits with **
            new_name = re.sub(r"\d{4,}", "**", new_name)
            # replace strings of the form _12. with _**.
            new_name = re.sub(r"\d{2,}", "**", new_name)
            example_files[new_name] = ff

            all_df.append(
                pd.DataFrame.from_dict(new_dict).melt().assign(pattern=new_name)
            )
    
    try: 
        all_df = pd.concat(all_df).reset_index(drop=True)
    except:
        raise ValueError("No netCDF files found with any of the model variables.")
    #  rename variable-value, and value-variable
    all_df = all_df.rename(columns={"variable": "value", "value": "variable"}) 


    patterns = set(all_df.pattern)
    resolution_dict = dict()
    for folder in patterns:
        resolution_dict[folder] = get_time_res(folder, new_directory)
    all_df["resolution"] = [resolution_dict[x] for x in all_df.pattern]

    all_df = (
        all_df.sort_values("resolution").groupby("value").head(1).reset_index(drop=True)
    )
    all_df = all_df.rename(columns={"variable": "model_variable"})
    all_df = all_df.rename(columns={"value": "variable"})
    all_df = all_df.drop(columns="resolution")
    all_df = all_df.loc[:, ["variable", "model_variable", "pattern"]]

    # add example file column
    all_df["example_file"] = [
        example_files[x] for x in all_df.pattern
    ]

    return all_df

def summarize(
    sim_dir=None,
    start=None,
    end=None,
    lon_lim=None,
    lat_lim=None,
    cores=6,
    thickness=None,
    n_dirs_down=2,
    overwrite=True,
    out_dir="",
    exclude=[],
    require=None,
    cache=False,
    n_check=None,
    as_missing=None,
    strict_names=True,
    ask = True,
):
    """
    Generate summaries of model output based on defined summary variables.

    Parameters
    -------------
    sim_dir : str
        Folder containing model output
    start : int
        Start year. First year of the simulations to summarize.
        This must be supplied
    end : int
        End year. Final year of the simulations to summarize.
        This must be supplied
    lon_lim : list
        List of two floats, which must be provided. The first is the minimum longitude, 
        the second is the maximum longitude. Default is None.
    lat_lim : list
        List of two float. Default is None, so no spatial subsetting will occur. 
        The first is the minimum latitude, the second is the maximum latitude. Default is None.
    cores : int
        Number of cores to use for parallel processing.
        Default is 6, or the system cores if less than 6.
    thickness : str
        Path to a thickness file, i.e. cell vertical thickness or the name of the thickness variable. 
        This only needs to be supplied if the variable is missing from the raw data.
    n_dirs_down : int
        Number of levels down to look for netCDF files. Default is 2, ie. the files are of 
        the format */*/*.nc.
    overwrite : bool
        If True, existing summarized data will be overwritten. Default is True.
    out_dir : str
        Path to output directory. Default is "", so the output will be saved in the current directory.
    exclude : list
        List of strings to exclude. This is useful if you have files in the directory that 
        you do not want to include in the summary.
    require : list
        List of strings to require. This is useful if you want to only include files that 
        have certain strings in their names. Defaults to None, so there are no requirements.
    cache : bool
        If True, caching will be used to speed up future processing. Default is False.
    n_check : int
        Number of files to check when extracting variable mappings. Default is None, 
        so all files will be checked.
    as_missing : float or list
        Value(s) to treat as missing in the model data. Default is None.

    Returns
    -------------
    None
    Summarized data will be stored in the oceanval_summaries directory.

    Examples
    -------------
    >>> import oceanval as ov
    >>> ov.add_summary(name="temp", model_variable="temperature", vertical_average=True, depth_range=[0, 100])
    >>> ov.summarize(sim_dir="/path/to/model/output", start=2000, end=2010)
    """

    session_info["levels_down"] = n_dirs_down
    session_info["require"] = require
    session_info["as_missing"] = as_missing
    
    # Validate sim_dir
    if sim_dir is None:
        raise ValueError("Please provide a sim_dir directory")
    if not os.path.exists(sim_dir):
        raise ValueError(f"{sim_dir} does not exist")
    sim_dir = os.path.abspath(sim_dir)
    
    # Validate start year
    if start is None:
        raise ValueError("Please provide a start year")
    if isinstance(start, int) is False:
        raise TypeError("Start must be an integer")
    
    # Validate end year
    if end is None:
        raise ValueError("Please provide an end year")
    if isinstance(end, int) is False:
        raise TypeError("End must be an integer")
    
    # Validate lon_lim and lat_lim
    if (lon_lim is None and lat_lim is None) is False:
        if lon_lim is None or lat_lim is None:
            raise TypeError("lon_lim and lat_lim must both be provided or both be None")
    
    if lon_lim is not None:
        if not isinstance(lon_lim, list) or len(lon_lim) != 2:
            raise ValueError("lon_lim must be a list of two floats")
    
    if lat_lim is not None:
        if not isinstance(lat_lim, list) or len(lat_lim) != 2:
            raise ValueError("lat_lim must be a list of two floats")
    
    # Validate cores
    if cores == 6:
        if cores > os.cpu_count():
            cores = os.cpu_count()
            print(f"Setting cores to {cores} as this is the number of cores available on your system")
    if cores < 1:
        raise ValueError("cores must be a positive integer")
    nc.options(cores=cores)

    
    # Validate thickness parameter
    if thickness is not None:
        if isinstance(thickness, str):
            if thickness.endswith(".nc"):
                if not os.path.exists(thickness):
                    raise FileNotFoundError(f"{thickness} does not exist")
    if thickness == "z-level":
        thickness = "z_level"
    if thickness == "z level":
        thickness = "z_level"
    if thickness == "z_level":
        session_info["z_level"] = True
    else:
        session_info["z_level"] = False
    # Validate out_dir
    if not isinstance(out_dir, str):
        raise TypeError("out_dir must be a string")
    out_dir = os.path.expanduser(out_dir)
    out_dir = os.path.abspath(out_dir)
    session_info["out_dir"] = out_dir

    invert_thickness = False
    thick_check = False
    # loop through summaries to see if any require thickness
    for var_name in summaries.keys:
        var = summaries[var_name]
        if var.vertical:
            thick_check = True
    ds_depths = None
    if session_info["z_level"]:
        thick_check = False
    if thick_check:
        print("Sorting out thickness")
        ds_depths = False
        with warnings.catch_warnings(record=True) as w:
            # extract the thickness dataset
            cell_thickness_found = False
            if thickness is not None and os.path.exists(thickness):
                ds_thickness = nc.open_data(thickness, checks=False)
                invert_thickness = is_z_up(ds_thickness[0])
                if len(ds_thickness.variables) != 1:
                    if (
                        len(
                            [x for x in ds_thickness.variables if "cell_thickness" in x]
                        )
                        == 0
                    ):
                        raise ValueError(
                            "The thickness file has more than one variable and none include cell_thickness. Please provide a single variable!"
                        )
                ds_thickness.rename({ds_thickness.variables[0]: "cell_thickness"})
                cell_thickness_found = True
                thickness = "cell_thickness"
            else:
                print(
                    "Vertical thickness is required for your matchups, but they are not supplied"
                )
                print("Searching through simulation output to find it")
                if thickness is None:
                    raise ValueError(
                        "Please provide the name of the thickness variable"
                    )
                for ff in raw_options:
                    print("Checking file for thickness: " + ff)
                    # do this quietly
                    with warnings.catch_warnings(record=True) as w:
                        ds_thickness = nc.open_data(ff, checks=False)
                        if thickness in ds_thickness.variables:
                            cell_thickness_found = True
                            invert_thickness = is_z_up(ff, thickness)
                            break
                        else:
                            if (
                                len(
                                    [
                                        x
                                        for x in ds_thickness.variables
                                        if thickness in x
                                    ]
                                )
                                > 0
                            ):
                                cell_thickness_found = True
                                invert_thickness = is_z_up(ff, thickness)
                                break

            if not cell_thickness_found:
                raise ValueError("Unable to find cell_thickness")

            if os.path.exists(thickness) == False:
                if len(ds_thickness.times) > 0:
                    ds_thickness.subset(time=0, variables=f"{thickness}*")
                else:
                    ds_thickness.subset(variables=f"{thickness}*")
            ds_thickness.run()
            var_sel = (
                ds_thickness.contents.query(f"variable.str.contains('{thickness}')")
                .query("nlevels > 1")
                .variable
            )
            ds_thickness.subset(variables=var_sel)
            if session_info["as_missing"] is not None:
                ds_thickness.as_missing(session_info["as_missing"])
            if len(ds_thickness.variables) > 1:
                if "cell_thickness" in ds_thickness.variables:
                    ds_thickness.subset(variables=f"{thickness}*")
                else:
                    ds_thickness.subset(variables=ds_thickness.variables[0])
            ds_thickness.run()
          #  print(f"Thickness variable is {ds_thickness.variables[0]} from {ff}")
            #####
            # now output the bathymetry if it does not exists


            if invert_thickness:
                if ask:
                    # user check
                    x = input(
                        "The thickness data appears to have the sea surface at the bottom (i.e. increasing depth values down. DO NOT PROCEED IF THIS IS A NEMO SIMULATION. Is this correct? (y/n) "
                    )
                    if x.lower() == "n":
                        return None
                else:
                    print("###### Inverting thickness automatically")
                    print(
                        "The thickness data appears to have the sea surface at the bottom (i.e. increasing depth values down. This has been inverted automatically."
                    )
                    print("##########################################################################")

            ds_thickness.run()
            if invert_thickness:
                ds_thickness.invert_levels()
                ds_thickness.run()
            ds_thickness_sim = ds_thickness.copy()

            ds_depths = ds_thickness.copy()

            ds_depths.vertical_cumsum()
            ds_cell_thickness = ds_thickness.copy()
            ds_thickness / 2
            ds_depths - ds_thickness
            ds_depths.run()
            ds_depths.rename({ds_depths.variables[0]: "depth"})
            ds_depths.run()

        for ww in w:
            if str(ww.message) not in session_warnings:
                session_warnings.append(str(ww.message))
        if ds_depths is False:
            raise ValueError(
                "You have asked for variables that require the specification of thickness"
            )
        print("Thickness is sorted out")

        ds_depths.run()
    if ds_depths is not None:
        session_info["ds_depths"] = ds_depths[0]
        session_info["ds_thickness"] = ds_thickness_sim[0]
    else:
        session_info["ds_depths"] = thickness
        session_info["ds_thickness"] = None 

    session_info["invert"] = invert_thickness    
    # Validate n_dirs_down
    if not isinstance(n_dirs_down, int):
        raise TypeError("n_dirs_down must be an integer")
    if n_dirs_down < 0:
        raise ValueError("n_dirs_down must be a positive integer")
    
    # Validate overwrite
    if not isinstance(overwrite, bool):
        raise TypeError("overwrite must be a boolean")
    
    
    # Validate exclude
    if not isinstance(exclude, list):
        if isinstance(exclude, str):
            exclude = [exclude]
        else:
            raise TypeError("exclude must be a list or a string")
    for ex in exclude:
        if not isinstance(ex, str):
            raise TypeError("each item in exclude must be a string")
    
    # Validate require
    if require is not None:
        if isinstance(require, str):
            require = [require]
        if not isinstance(require, list):
            raise TypeError("require must be a list or a string")
        for rq in require:
            if not isinstance(rq, str):
                raise TypeError("each item in require must be a string")
    
    # Validate cache
    if not isinstance(cache, bool):
        raise TypeError("cache must be a boolean")
    
    # Validate n_check
    if n_check is not None:
        if not isinstance(n_check, int):
            raise TypeError("n_check must be an integer")
        if n_check < 1:
            raise ValueError("n_check must be a positive integer")
    
    # Validate as_missing
    if as_missing is not None:
        if not isinstance(as_missing, list):
            if not isinstance(as_missing, (int, float)):
                raise TypeError("as_missing must be a float, int, list or None")
        if isinstance(as_missing, list):
            for am in as_missing:
                if not isinstance(am, (int, float)):
                    raise TypeError("as_missing list elements must be float or int")
    
    # Check if any summaries have been defined
    if len(summaries.keys) == 0:
        raise ValueError("You do not appear to have defined any summary variables! Use add_summary() to define them.")
    
    # Create output directory
    summary_dir = os.path.join(out_dir, "oceanval_summaries")
    os.makedirs(summary_dir, exist_ok=True)
    
    print(f"Processing {len(summaries.keys)} summary variables from {start} to {end}")

    all_df = extract_variable_mapping(
        folder=sim_dir,
        exclude=exclude,
        n_check=n_check
    )
    print("Variable mapping extraction complete.")
    print(all_df)
    if ask:
        x = input("Are you happy with the variable mappings shown above? Y/N: ")
        if x.lower() != "y":
            print("Exiting summarization. Please redefine your summary variables as needed.")
            return

    patterns = list(set(all_df.pattern))
    times_dict = dict()

    # Find model files
    print("*************************************")
    for pattern in patterns:
        print(f"Indexing file time information for {pattern} files")
        final_extension = extension_of_directory(sim_dir)
        ensemble = glob.glob(sim_dir + final_extension + pattern)
        # handle required
        if session_info["require"] is not None:
            for req in session_info["require"]:
                ensemble = [x for x in ensemble if f"{req}" in os.path.basename(x)]
        for exc in exclude:
            ensemble = [x for x in ensemble if f"{exc}" not in os.path.basename(x)]
        # find length of example file
        if strict_names:
            len_example = len(os.path.basename(example_files[pattern]))
            ensemble = [x for x in ensemble if len(os.path.basename(x)) == len_example]

        try:
            ds = xr.open_dataset(ensemble[0])
            time_name = [x for x in list(ds.dims) if "time" in x][0]
        except:
            ds = xr.open_dataset(ensemble[0], decode_times=False)
            time_name = [x for x in list(ds.dims) if "time" in x][0]

        for ff in tqdm(ensemble):
            if ff in times_dict:
                continue
            if "restart" in ff:
                continue

            try:
                ds = xr.open_dataset(ff)
                ff_month = [int(x.dt.month) for x in ds[time_name]]
                ff_year = [int(x.dt.year) for x in ds[time_name]]
                days = [int(x.dt.day) for x in ds[time_name]]
            except:
                ds = nc.open_data(ff, checks=False)
                ds_times = ds.times
                ff_month = [int(x.month) for x in ds_times]
                ff_year = [int(x.year) for x in ds_times]
                days = [int(x.day) for x in ds_times]

            df_ff = pd.DataFrame(
                {
                    "year": ff_year,
                    "month": ff_month,
                    "day": days,
                }
            )
            times_dict[ff] = df_ff

    
    # Process each summary variable
    for var_name in summaries.keys:
        var = summaries[var_name]
        model_var = var.model_variable
        
        print(f"\nProcessing {var_name} (model variable: {model_var})")
        
        # Find files containing this variable
        pattern = all_df.query(f"variable == '{var_name}'")["pattern"].values[0]     
        final_extension = extension_of_directory(sim_dir, n_dirs_down)
        ensemble = glob.glob(sim_dir + final_extension + pattern)
        start = summaries[var_name].start
        end = summaries[var_name].end
        all_files = []
        for ff in ensemble:
            if times_dict[ff].year.min() <= end and times_dict[ff].year.max() >= start:
                all_files.append(ff)
        
        # Apply exclude filters
        for exc in exclude:
            all_files = [f for f in all_files if exc not in str(f)]
        
        # Apply require filters
        if require is not None:
            for req in require:
                all_files = [f for f in all_files if req in str(f)]
        
        if len(all_files) == 0:
            print(f"  Warning: No files found for {var_name}")
            continue
        
        # Open and process the data
        ds = nc.open_data(all_files, checks=False)
            
        # Check if variable exists
        if model_var not in ds.variables:
            print(f"  Warning: Variable {model_var} not found in files")
            continue
            
        # Subset to variable of interest
        ds.subset(variables=model_var)
            
        # Apply time range
            
        # Apply spatial subsetting
        if lon_lim is not None and lat_lim is not None:
            ds.subset(lon=lon_lim, lat=lat_lim)
            
        # Handle missing values
        if as_missing is not None:
            ds.as_missing(as_missing)
            
        # Apply depth range if specified
        ds.merge("time")
        ds.tmean("year")
        short_title = summaries[var_name].short_title
        ds.set_longnames({model_var: short_title})
        ds.run()


        # now do the climatology
        clim_years = summaries[var_name].climatology_years
        # do this quietly
        with warnings.catch_warnings(record=True) as w:
            ds_clim = ds.copy()
            ds_clim.subset(years=range(clim_years[0], clim_years[1] + 1))
            ds_clim.top()
            ds_clim.tmean()
            ds_clim.run()
            
        # Prepare output filename
        out_file = f"{summary_dir}/data/{var_name}/{var_name}_surface_climatology.nc"
        os.makedirs(os.path.dirname(out_file), exist_ok=True)
            
        # Check if we should overwrite
        if os.path.exists(out_file) and not overwrite:
            print(f"  File exists and overwrite=False, skipping: {out_file}")
            continue
            
        # Save the result
        # delete if it iexists
        if os.path.exists(out_file):
            os.remove(out_file)
        ds_clim.to_nc(out_file, overwrite=True, zip=True)
        print(f"  Saved: {out_file}")
        trend_info = summaries[var_name].trends
        trends = trend_info is not None
        # now figure out if vertical mean is neeed
        if summaries[var_name].vertical_mean:
            # quietly
            with warnings.catch_warnings(record=True) as w:
                ds_vertmean = ds.copy()
                ds_vertmean.subset(years=clim_years)
                ds_vertmean.tmean()
                thickness = session_info["ds_thickness"]
                if thickness is None:
                    ds_vertmean.vertical_mean(fixed = True)
                else:
                    ds_vertmean.vertical_mean(thickness = ds_cell_thickness)
                # climatological years
                out_file = f"{summary_dir}/data/{var_name}/{var_name}_verticalmean_climatology.nc"
                os.makedirs(os.path.dirname(out_file), exist_ok=True)
                if os.path.exists(out_file):
                    os.remove(out_file)
                ds_vertmean.to_nc(out_file, overwrite=True, zip=True)
                print(f"  Saved: {out_file}")
            
                # do trends if needed
            if trends:
                with warnings.catch_warnings(record=True) as w:
                    ds_trends = ds.copy()
                    period = trend_info["period"]
                    ds_trends.subset(years = range(period[0], period[1] + 1))
                    window = trend_info["window"]
                    if window != 1:
                        ds_trends.rolling_mean(window)
                    if thickness is None:
                        ds_trends.vertical_mean(fixed = True)
                    else:
                        ds_trends.vertical_mean(thickness = ds_cell_thickness)
                    ds_trends.spatial_mean()
                    out_file = f"{summary_dir}/data/{var_name}/{var_name}_verticalmean_spatialmeantimeseries.nc"
                    os.makedirs(os.path.dirname(out_file), exist_ok = True)
                    if os.path.exists(out_file):
                        os.remove(out_file)

                    ds_trends.to_nc(out_file, overwrite=True, zip=True)
            
        # now do vertical integration if needed
        if summaries[var_name].vertical_integration:
            with warnings.catch_warnings(record=True) as w:
                ds_vertint = ds.copy()
                ds_vertint.subset(years=clim_years)
                ds_vertint.tmean()
                thickness = session_info["ds_thickness"]
                if thickness is None:
                    ds_vertint.vertical_integration(fixed = True)
                else:
                    ds_vertint.vertical_integration(thickness = ds_cell_thickness)
                # climatological years
                out_file = f"{summary_dir}/data/{var_name}/{var_name}_verticalintegrated_climatology.nc"
                os.makedirs(os.path.dirname(out_file), exist_ok=True)
                if os.path.exists(out_file):
                    os.remove(out_file)
                ds_vertint.to_nc(out_file, overwrite=True, zip=True)
                print(f"  Saved: {out_file}")

            # now do the spatial mean timeseries
            if trends:
                with warnings.catch_warnings(record=True) as w:
                    ds_trends = ds.copy()
                    period = trend_info["period"]
                    ds_trends.subset(years = range(period[0], period[1] + 1))
                    window = trend_info["window"]
                    if window != 1:
                        ds_trends.rolling_mean(window)
                    if thickness is None:
                        ds_trends.vertical_integration(fixed = True)
                    else:
                        ds_trends.vertical_integration(thickness = ds_cell_thickness)
                    ds_trends.spatial_sum(by_area = True)
                    out_file = f"{summary_dir}/data/{var_name}/{var_name}_verticalintegrated_spatialsumtimeseries.nc"
                    os.makedirs(os.path.dirname(out_file), exist_ok = True)
                    if os.path.exists(out_file):
                        os.remove(out_file)

                    ds_trends.to_nc(out_file, overwrite=True, zip=True)

        if trends:
            with warnings.catch_warnings(record=True) as w:
                ds_trends = ds.copy()
                ds_trends.top()
                ds_trends.spatial_mean()
                # find out the window
                trend_info = summaries[var_name].trends
                period = trend_info["period"]
                ds_trends.subset(years = range(period[0], period[1] + 1))
                window = trend_info["window"]
                if window != 1:
                    ds_trends.rolling_mean(window)
                # save it
                out_file = f"{summary_dir}/data/{var_name}/{var_name}_surface_spatialmeantimeseries.nc"
                os.makedirs(os.path.dirname(out_file), exist_ok=True)
                if os.path.exists(out_file):
                    os.remove(out_file)

                ds_trends.to_nc(out_file, overwrite=True, zip=True)

            
    
        # Save summaries configuration
        config_file = os.path.join(f"{summary_dir}/data/{var_name}", "summaries_config.pkl")
        with open(config_file, "wb") as f:
            import dill
            dill.dump(summaries, f)
    
    print(f"\nSummarization complete. Output saved to: {summary_dir}")

    # now create the book

    book_dir = f"{out_dir}/oceanval_summaries/book"
    os.makedirs(book_dir, exist_ok=True)

    data_path = importlib.resources.files(__name__).joinpath("data/_toc.yml")

    out = f"{book_dir}/" + os.path.basename(data_path)
    copyfile(data_path, out)
    print(out)

    data_path = importlib.resources.files(__name__).joinpath(
        "data/requirements.txt"
    )
    out = f"{book_dir}/" + os.path.basename(data_path)
    copyfile(data_path, out)

    data_path = importlib.resources.files(__name__).joinpath("data/intro_summarize.md")
    out = f"{book_dir}/" + os.path.basename(data_path).replace("intro_summarize", "intro")
    copyfile(data_path, out)

    # copy config

    data_path = importlib.resources.files(__name__).joinpath("data/_config.yml")
    out = f"{book_dir}/" + os.path.basename(data_path)
    copyfile(data_path, out)

    # open config and replace oceanval_report with oceanval_summaries
    with open(out, "r") as file:
        filedata = file.read()
    # Replace the target string
    filedata = filedata.replace("oceanval_report", "book")
    # write
    with open(out, "w") as file:
        file.write(filedata)
                            

    copyfile(
        importlib.resources.files(__name__).joinpath("data/pml_logo.jpg"),
        f"{book_dir}/pml_logo.jpg",
    )

    # identify variables to be summarized
    #f"{out_dir}/data"
    # directories in this
    summary_variables = os.listdir(f"{summary_dir}/data")
    # variables are the basename
    variables = [os.path.basename(x) for x in summary_variables]

    for vv in variables:
        vv_out = f"{book_dir}/notebooks/{vv}_summary.ipynb"
        file1 = importlib.resources.files(__name__).joinpath(
                        "data/variable_summary_template.ipynb"
                    )
        # create directory
        os.makedirs(os.path.dirname(vv_out), exist_ok=True)
         # copy file
        copyfile(file1, vv_out)

        ff = f"{summary_dir}/data/{vv}/summaries_config.pkl"
        with open(ff, "rb") as f:
            ff_dict = dill.load(f)
        short_title = ff_dict[vv].short_title
        # read this in
        # read vv_out in and do some replacing
        with open(vv_out, "r") as file:
            filedata = file.read()
        # Replace the target string
        filedata = filedata.replace("VARIABLE_NAME", vv)
        filedata = filedata.replace("SHORT_TITLE", short_title)
        
        
        # write
        with open(vv_out, "w") as file:
            file.write(filedata)
    

    os.system(f"jupyter-book build  {book_dir}/")
    webbrowser.open(
            "file://" + os.path.abspath(f"{book_dir}/_build/html/index.html")
        )



