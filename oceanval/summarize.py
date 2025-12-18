import copy
import os
import glob
import pathlib
import warnings
import pickle
import nctoolkit as nc
import random
import pandas as pd
import re

from oceanval.session import session_info
from oceanval.parsers import summaries, generate_mapping_summary
from oceanval.utils import extension_of_directory
from oceanval.matchall import get_time_res
from tqdm import tqdm
example_files = dict()

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
    as_missing=None
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
    
    # Validate n_dirs_down
    if not isinstance(n_dirs_down, int):
        raise TypeError("n_dirs_down must be an integer")
    if n_dirs_down < 0:
        raise ValueError("n_dirs_down must be a positive integer")
    
    # Validate overwrite
    if not isinstance(overwrite, bool):
        raise TypeError("overwrite must be a boolean")
    
    # Validate out_dir
    if not isinstance(out_dir, str):
        raise TypeError("out_dir must be a string")
    out_dir = os.path.expanduser(out_dir)
    out_dir = os.path.abspath(out_dir)
    
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
    x = input("Are you happy with the variable mappings shown above? Y/N: ")
    if x.lower() != "y":
        print("Exiting summarization. Please redefine your summary variables as needed.")
        return

    # Find model files

    
    # Process each summary variable
    for var_name in summaries.keys:
        var = summaries[var_name]
        model_var = var.model_variable
        
        print(f"\nProcessing {var_name} (model variable: {model_var})")
        
        # Find files containing this variable
        pattern = all_df.query(f"variable == '{var_name}'")["pattern"].values[0]     
        final_extension = extension_of_directory(sim_dir, n_dirs_down)
        ensemble = glob.glob(sim_dir + final_extension + pattern, recursive = True)
        all_files = list(set(ensemble))

        
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
        try:
            ds = nc.open_data(all_files, checks=False)
            ds.subset(years=range(start, end + 1))
            
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
            ds.run()

            # now do the climatology
            clim_years = summaries[var_name].climatology_years
            ds_clim = ds.copy()
            ds_clim.subset(years=clim_years)
            ds_clim.top()
            ds_clim.tmean()
            
            # Prepare output filename
            out_file = f"{summary_dir}/data/{var_name}/{var_name}_surface_climatology.nc"
            os.makedirs(os.path.dirname(out_file), exist_ok=True)
            
            # Check if we should overwrite
            if os.path.exists(out_file) and not overwrite:
                print(f"  File exists and overwrite=False, skipping: {out_file}")
                continue
            
            # Save the result
            ds_clim.to_nc(out_file, overwrite=True, zip=True)
            print(f"  Saved: {out_file}")

            ds_trends = ds.copy()
            ds_trends.spatial_mean()
            # save it
            out_file = f"{summary_dir}/data/{var_name}/{var_name}_spatialmean_timeseries.nc"
            os.makedirs(os.path.dirname(out_file), exist_ok=True)
            ds_trends.to_nc(out_file, overwrite=True, zip=True)

            
        except Exception as e:
            print(f"  Error processing {var_name}: {str(e)}")
            warnings.warn(f"Failed to process {var_name}: {str(e)}")
            continue
    
        # Save summaries configuration
        config_file = os.path.join(f"{summary_dir}/{var_name}", "summaries_config.pkl")
        with open(config_file, "wb") as f:
            import dill
            dill.dump(summaries, f)
    
    print(f"\nSummarization complete. Output saved to: {summary_dir}")
