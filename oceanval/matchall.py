import copy
import time
import nctoolkit as nc
import re
import importlib
import glob
import subprocess
import platform
if platform.system() == "Linux":
    import multiprocessing as mp
    from multiprocessing import Manager
else:
    import multiprocess as mp
    from multiprocess import Manager
import pathlib
import os
import pandas as pd
import string
import random
import warnings
import pickle
import xarray as xr
import oceanval.parsers as parsers
from oceanval.session import session_info
from oceanval.parsers import Validator, definitions
from tqdm import tqdm
from oceanval.utils import extension_of_directory
from oceanval.parsers import generate_mapping
from oceanval.gridded import gridded_matchup


def is_z_up(ff, variable=None):
    import netCDF4 as nc4

    try:
        ds1 = nc.open_data(ff, checks=False)
        if variable is None:
            var = ds1.variables[0]
        else:
            var = variable
        # select variable using nco
        ds1.nco_command(f"ncks -v {var}")
        ds1.run()
        ds = xr.open_dataset(ds1[0])
        ds = ds
        for x in ds[var].metpy.coordinates("longitude"):
            lon_name = x.name
        for x in ds[var].metpy.coordinates("latitude"):
            lat_name = x.name
        for x in ds[var].metpy.coordinates("time"):
            time_name = x.name
        coords = [
            x for x in list(ds.coords) if x not in [lon_name, lat_name, time_name]
        ]
        coords = [x for x in coords if "time" not in x.lower()]

        ds = nc4.Dataset(ff)
        if len(coords) == 1:

            z = ds.variables[coords[0]]
            if hasattr(z, "positive"):
                if z.positive == "down":
                    return False
                else:
                    return True
        raise ValueError(
            "Could not determine if z-axis is down from the provided file."
        )
    except:
        raise ValueError(
            "Could not determine if z-axis is down from the provided file."
        )


# a list of valid variables for validation
# add some additionals

session_warnings = Manager().list()

nc.options(progress=False)


def mm_match(ff, model_variable, df, df_times, ds_depths, variable, df_all, layer=None):
    """
    Parameters
    -------------
    ff: str
        Path to file
    model_variable: str
        Variable name in the simulation
    df: pd.DataFrame
        Dataframe of observational data
    df_times: pd.DataFrame
        Dataframe of observational data 
    ds_depths: list
        Depths to match

    """


    if session_info["cache"]:
        try:
            ff_read = (
                session_info["cache_mapping"]
                .query("path == @ff & layer == @layer & variable == @variable")
                .output
            )
            # read this pickle file in
            with open(ff_read.values[0], "rb") as f:
                df_ff = pickle.load(f)
                df_all.append(df_ff)
                return None
        except:
            pass

    df_ff = None

    if ds_depths is not None:
        nc.session.append_safe(ds_depths[0])
    try:
        with warnings.catch_warnings(record=True) as w:
            ds = nc.open_data(ff, checks=False)
            var_match = model_variable.split("+")

            valid_locs = ["lon", "lat", "year", "month", "day", "depth"]
            valid_locs = [x for x in valid_locs if x in df.columns]

            valid_times = (
                "year" in df.columns or "month" in df.columns or "day" in df.columns
            )

            if valid_times:
                df_locs = (
                    df_times.query("path == @ff")
                    .merge(df)
                    .loc[:, valid_locs]
                    .drop_duplicates()
                    .reset_index(drop=True)
                )
            else:
                df_locs = df.loc[:, valid_locs]

            ds.subset(variables=var_match)
            #
            ds1 = nc.open_data(ds[0], checks=False)
            ds_contents = ds1.contents
            the_var = model_variable.split("+")[0]

            if list(ds_contents.query("variable == @the_var").nlevels)[0] > 1:
                if layer == "surface":
                    ds.cdo_command("topvalue")
                else:
                    if session_info["invert"]:
                        ds.invert_levels()

            if (
                "year" in df_locs.columns
                or "month" in df_locs.columns
                or "day" in df_locs.columns
            ):
                ff_indices = df_times.query("path == @ff")

                ff_indices = ff_indices.reset_index(drop=True).reset_index()
                ff_indices = ff_indices
                ff_indices = ff_indices.merge(df_locs)
                ff_indices = ff_indices["index"].values
                ff_indices = [int(x) for x in ff_indices]
                ff_indices = list(set(ff_indices))

                if len(ff_indices) == 0:
                    return None
                ds.subset(time=ff_indices)
            if session_info["as_missing"] is not None:
                ds.as_missing(session_info["as_missing"])
            ds.run()


            if len(var_match) > 1:
                ds.sum_all()
            the_dict = {"model_variable": model_variable}
            session_info["adhoc"] = copy.deepcopy(the_dict)

            if len(df_locs) > 0:
                ds.run()
                if ds_depths is not None:
                    df_ff = ds.match_points(
                        df_locs, depths=ds_depths, quiet=True, max_extrap=0
                    )
                else:
                    df_ff = ds.match_points(
                        df_locs, quiet=True, max_extrap=0
                    )
                if df_ff is not None:
                    df_ff = df_ff.dropna().reset_index(drop=True)

                if df_ff is not None:
                    valid_vars = ["lon", "lat", "year", "month", "day", "depth"]
                    for vv in ds.variables:
                        valid_vars.append(vv)
                    valid_vars = [x for x in valid_vars if x in df_ff.columns]
                    df_ff = df_ff.loc[:, valid_vars]
                    # add this to the cache if necessary
                    if session_info["cache"]:
                        cache_dir = session_info["cache_dir"]
                        if cache_dir is not None:
                            # create a random string
                            random_string = "".join(
                                random.choices(
                                    string.ascii_lowercase + string.digits, k=10
                                )
                            )
                            cache_file = (
                                cache_dir
                                + "output/"
                                + "/matchup_"
                                + layer
                                + "_"
                                + variable
                                + "_"
                                + random_string
                                + ".pkl"
                            )
                            if not os.path.exists(cache_dir + "/output"):
                                os.makedirs(cache_dir + "/output")
                            with open(cache_file, "wb") as f:
                                pickle.dump(df_ff, f)
                            # add a mapping to session_info["cache_files"]
                            # add to session_info["cache_dir"] + "/mappings"
                            mapping_file = (
                                cache_dir
                                + "/mappings/mapping_"
                                + layer
                                + "_"
                                + variable
                                + "_"
                                + random_string
                                + ".pkl"
                            )
                            if not os.path.exists(cache_dir + "/mappings"):
                                os.makedirs(cache_dir + "/mappings")
                            # dump ff
                            with open(mapping_file, "wb") as f:
                                output_dir = {ff: cache_file}
                                pickle.dump(output_dir, f)

                    df_all.append(df_ff)
            else:
                return None
        if df_ff is not None:
            for ww in w:
                if str(ww.message) not in session_warnings:
                    session_warnings.append(str(ww.message))

    except Exception as e:
        print(e)

example_files = dict()

def get_time_res(x, folder=None):
    """
    Get the time resolution of the netCDF files

    Parameters
    -------------
    x : str
        The extension of the file
    folder : str
        The folder containing the netCDF files

    Returns
    -------------
    res : str
        The time resolution of the netCDF files

    """

    final_extension = extension_of_directory(folder)

    if final_extension[0] == "/":
        final_extension = final_extension[1:]

    wild_card = final_extension + x
    wild_card = wild_card.replace("**", "*")
    # replace double stars with 1
    wild_card = wild_card.replace("**", "*")

    wild_card = os.path.basename(wild_card)
    for y in pathlib.Path(folder).glob(wild_card):
        path = y
        # convert to string
        path = str(path)
        break

    ds = nc.open_data(path, checks=False)
    ds_times = ds.times
    try:
        months = [x.month for x in ds_times]
        days = [x.day for x in ds_times]
        years = [x.year for x in ds_times]
    except:
        years = [int(str(x).split("T")[0].split("-")[0]) for x in ds.times]
        months = [int(str(x).split("T")[0].split("-")[1]) for x in ds.times]
        days = [int(str(x).split("T")[0].split("-")[2]) for x in ds.times]
    df_times = pd.DataFrame({"month": months, "day": days, "year": years})

    n1 = len(
        df_times.loc[:, ["month", "year"]].drop_duplicates().reset_index(drop=True)
    )
    n2 = len(df_times)
    if n1 == n2:
        return "m"
    else:
        return "d"


random_files = []
raw_options = []


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

    for x in options:
        raw_options.append(x)
    # randomize raw_options
    random.shuffle(raw_options)
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
        ds_dict = generate_mapping(ds)
        try:
            ds_dict = generate_mapping(ds)
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


def matchup(
    sim_dir=None,
    start=None,
    end=None,
    lon_lim=None,
    lat_lim=None,
    cores=6,
    thickness=None,
    n_dirs_down=2,
    point_time_res=["year", "month", "day"],
    overwrite=True,
    ask=True,
    out_dir="",
    exclude=[],
    require = None,
    cache=False,
    n_check=None,
    as_missing=None,
    strict_names = True
):
    """
    Match up model with observational data

    Parameters
    -------------

    sim_dir : str
        Folder containing model output
    start : int
        Start year. First year of the simulations to matchup.
        This must be supplied
    end : int
        End year. Final year of the simulations to matchup.
        This must be supplied
    lon_lim : list
        List of two floats, which must be provided. The first is the minimum longitude, the second is the maximum longitude. Default is None.
    lat_lim : list
        List of two float. Default is None, so no spatial subsetting will occur. The first is the minimum latitude, the second is the maximum latitude. Default is None.
    cores : int
        Number of cores to use for parallel extraction and matchups of data.
        Default is 6, or the system cores if less than 6.
        If you use a large number of cores you may run into RAM issues, so keep an eye on things.
    thickness : str
        Path to a thickness file, i.e. cell vertical thickness or the name of the thickness variable. This only needs to be supplied if the variable is missing from the raw data.
        If the cell_thickness variable is in the raw data, it will be used, and thickness does not need to be supplied.
    n_dirs_down : int
        Number of levels down to look for netCDF files. Default is 2, ie. the files are of the format */*/*.nc.
    point_time_res : list or dict
        List of strings or a dict. Default is ['year', 'month', 'day']. This is the time resolution of the point data matchup.
        If you want fine-grained control, provide a dictionary where the key is the variable and the value is a list of strings.
        If you provide this list make sure all variables have keys, or else provide a key called "default" with a value to use when the variable is not stated explicitly.
    overwrite : bool
        If True, existing matched data will be overwritten. Default is True.
    ask : bool
        If True, the user will be asked if they are happy with the matchups. Default is True.
    out_dir : str
        Path to output directory. Default is "", so the output will be saved in the current directory.
    exclude : list
        List of strings to exclude. This is useful if you have files in the directory that you do not want to include in the matchup.
    require : list
        List of strings to require. This is useful if you want to only include files that have certain strings in their names. Defaults to None, so there are no requirements.
    cache : bool
        If True, caching will be used to speed up future matchups. Default is False.
    n_check : int
        Number of files to check when extracting variable mappings. Default is None, so all files will be checked.
    as_missing : float or list
        Value(s) to treat as missing in the model data. Default is None.
    strict_names : bool
        If True, variable names must match exactly those in the definitions. Default is True.

    Returns
    -------------
    None
    Data will be stored in the matched directory.

  """
  # check if the sim_dir exists
    if sim_dir is None:
        raise ValueError("Please provide a sim_dir directory")
    if not os.path.exists(sim_dir):
        raise ValueError(f"{sim_dir} does not exist")
    # convert sim_dir to hard path
    if sim_dir is not None:
        sim_dir = os.path.abspath(sim_dir)

    if start is None:
        raise ValueError("Please provide a start year")
    if isinstance(start, int) is False:
        raise TypeError("Start must be an integer")

    if end is None:
        raise ValueError("Please provide an end year")
    if isinstance(end, int) is False:
        raise TypeError("End must be an integer")

    # check lon_lim and lat_lim are lists
    if (lon_lim is None and lat_lim is None) is False:
        if lon_lim is None or lat_lim is None:
            raise TypeError("lon_lim and lat_lim must be lists")

    # add this info to session_info
    session_info["lon_lim"] = lon_lim
    session_info["lat_lim"] = lat_lim

    if cores == 6:
        if cores > os.cpu_count():
            cores = os.cpu_count()
            print(
                f"Setting cores to {cores} as this is the number of cores available on your system"
            )
    # error for cores < 1
    if cores < 1:
        raise ValueError("cores must be a positive integer")
    nc.options(cores=cores)
    session_info["cores"] = cores

    if thickness is not None:
        if isinstance(thickness, str):
            # if it ends with .nc check it exists
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

    # check n_dirs_down is an integer
    if not isinstance(n_dirs_down, int):
        raise TypeError("n_dirs_down must be an integer")
    if n_dirs_down < 0:
        raise ValueError("n_dirs_down must be a positive integer")
    session_info["levels_down"] = n_dirs_down

    if isinstance(point_time_res, str):
        point_time_res = [point_time_res]
    if isinstance(point_time_res, list) is False:
        raise TypeError("point_time_res must be a list or a string")
    session_info["point_time_res"] = copy.deepcopy(point_time_res)

    if not isinstance(overwrite, bool):
        raise TypeError("overwrite must be a boolean")
    session_info["overwrite"] = overwrite

    if not isinstance(ask, bool):
        raise TypeError("ask must be a boolean")

    # ensure out_dir is a string

    if not isinstance(out_dir, str):
        raise TypeError("out_dir must be a string")
    out_dir = os.path.expanduser(out_dir)
    # full path
    out_dir = os.path.abspath(out_dir)
    # add out_dir to session_info
    session_info["out_dir"] = out_dir + "/"

    # check if exclude is a list or str
    if not isinstance(exclude, list):
        if isinstance(exclude, str):
            exclude = [exclude]
        else:
            raise TypeError("exclude must be a list or a string")
    # need to check each item in exclude is a string
    for ex in exclude:
        if not isinstance(ex, str):
            raise TypeError("each item in exclude must be a string")

    if require is not None:
        if isinstance(require, str):
            require = [require]
        if not isinstance(require, list):
            raise TypeError("require must be a list or a string")
        # need to check each item in require is a string
        for rq in require:
            if not isinstance(rq, str):
                raise TypeError("each item in require must be a string")

    session_info["require"] = require


    # check cache is a boolean
    if not isinstance(cache, bool):
        raise TypeError("cache must be a boolean")

    # check n_check is None or an integer
    if n_check is not None:
        if not isinstance(n_check, int):
            raise TypeError("n_check must be an integer")
    # ensure n_check is positive
        if n_check < 1:
            raise ValueError("n_check must be a positive integer")

    # check as_missing is None, float or list
    if as_missing is not None:
        if not isinstance(as_missing, list):
            if not isinstance(as_missing, (int, float)):
                raise TypeError("as_missing must be a float, int, list or None")
        # check list elements can be float
        if isinstance(as_missing, list):
            for am in as_missing:
                if not isinstance(am, (int, float)):
                    raise TypeError("as_missing list elements must be float or int")
    session_info["as_missing"] = as_missing

    # check strict_names is a boolean
    if not isinstance(strict_names, bool):
        raise TypeError("strict_names must be a boolean")
    session_info["strict_names"] = strict_names

    gridded = []

    point = dict()
    point["all"] = []
    point["surface"] = []

    if len(definitions.keys) == 0:
        raise ValueError("You do not appear to have asked for any variables to be validated!")
    for key in definitions.keys:
        if definitions[key].vertical_point is False:
            if key not in point["surface"]:
                point["surface"].append(key)
        if definitions[key].vertical_point is True:
            if key not in point["all"]:
                point["all"].append(key)
        # do the same for gridded
        if definitions[key].gridded:
            if key not in gridded:
                    gridded.append(key)

    # if cache is True, create a cache directory in out_dir
    if cache:
        cache_dir = out_dir + "/.cache_oceanval/"
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        session_info["cache_dir"] = cache_dir
        session_info["cache"] = True
        # create a mappings directory in cache_dir
        mappings_dir = cache_dir + "/mappings/"
        if not os.path.exists(mappings_dir):
            os.makedirs(mappings_dir)
        # list files in mappings_dir
        paths = glob.glob(mappings_dir + "/*.pkl")
        mapping_df = []
        for ff in paths:
            with open(ff, "rb") as f:
                output_dir = pickle.load(f)
            ff_path = list(output_dir.keys())[0]
            ff_output = list(output_dir.values())[0]
            ff_layer = os.path.basename(ff).split("_")[1]
            ff_variable = os.path.basename(ff).split("_")[2]
            mapping_df.append(
                pd.DataFrame(
                    {
                        "variable": [ff_variable],
                        "layer": [ff_layer],
                        "path": [ff_path],
                        "output": [ff_output],
                    }
                )
            )
        if len(mapping_df) > 0:
            mapping_df = pd.concat(mapping_df).reset_index(drop=True)
        session_info["cache_mapping"] = mapping_df

    else:
        session_info["cache_dir"] = None
        session_info["cache"] = False

    ds_depths = None


    ff = session_info["out_dir"] + "oceanval_matchups/short_titles.pkl"
    if os.path.exists(ff):
        with open(ff, "rb") as f:
            short_titles = pickle.load(f)
    else:
        short_titles = dict()
    session_info["short_title"] = short_titles | session_info["short_title"]

    sim_start = -1000
    sim_end = 10000

    if end is not None:
        sim_end = end

    if start is not None:
        sim_start = start

    # check validity of variables chosen

    all_vars = definitions.keys

    all_df = extract_variable_mapping(sim_dir, exclude=exclude, n_check=n_check)
    # check if any model_variable is None
    var_found = list(all_df.variable.unique())
    missing = ",".join([x for x in all_vars if x not in var_found])
    # 
    if len(missing) > 0:
        error = f"The model variables specified do not appear to be in the simulation output for the following: {missing}. Please check the model_variable names and try again."
        raise ValueError(error)

    # add in anything that is missing

    missing_df = pd.DataFrame({"variable": all_vars}).assign(
        model_variable=None, pattern=None
    )

    all_df = (
        pd.concat([all_df, missing_df])
        .groupby("variable")
        .head(1)
        .reset_index(drop=True)
        )
    # check if the variables are in all_df

    pattern = all_df.reset_index(drop=True).iloc[0, :].pattern

    final_extension = extension_of_directory(sim_dir)

    if final_extension[0] == "/":
        final_extension = final_extension[1:]

    wild_card = final_extension + pattern
    wild_card = wild_card.replace("**", "*")
    for x in pathlib.Path(sim_dir).glob(wild_card):
        path = x
        # convert to string
        path = str(path)
        break

    try:
        ds = nc.open_data(path, checks=False)
    except:
        raise ValueError("Problems finding files. Check n_dirs_down arg")

    # check length of lon_lim and lat_lim
    if session_info["lon_lim"] is not None:
        if len(session_info["lon_lim"]) != 2 or len(session_info["lat_lim"]) != 2:
            raise ValueError(
                "lon_lim and lat_lim must be lists of two floats, e.g. [-18, 9] and [42, 63]"
            )


    vars_available = list(
        all_df
        # drop rows where pattern is None
        .dropna()
        # get all variables
        .variable
    )
    # check variables chosen are valid

    remove = []

    gridded = [x for x in gridded if x in vars_available]
    for key in point.keys():
        point[key] = [x for x in point[key] if x in vars_available]

    for vv in point["all"]:
        if definitions[vv].vertical_point is False:
            point["all"].remove(vv)
            point["surface"].append(vv)

    var_chosen = gridded + point["all"] + point["surface"]
    var_chosen = list(set(var_chosen))

    # create oceanval_matchups directory
    if not os.path.exists("oceanval_matchups"):
        os.makedirs(session_info["out_dir"] + "/oceanval_matchups", exist_ok=True)

    invert_thickness = False
    point_all = point["all"] + point["surface"]

    # go through variables in definitions
    thick_check = False
    for vv in var_chosen:
        # identifical if vertical_gridded is True
        try:
            if definitions[vv].vertical_gridded:
                thick_check = True
        except:
            pass
    if len(point["all"]) > 0:
        thick_check = True

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
            print(f"Thickness variable is {ds_thickness.variables[0]} from {ff}")
            #####
            # now output the bathymetry if it does not exists

            ff_bath = session_info["out_dir"] + "oceanval_matchups/model_bathymetry.nc"
            if not os.path.exists(ff_bath):
                ds_bath = ds_thickness.copy()
                ds_bath.vertical_sum()
                ds_bath.to_nc(ff_bath, zip=True)

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

    # add the global checker here
    # sort all_df alphabetically by variable
    all_df = all_df.sort_values("variable").reset_index(drop=True)
    gridded.sort()
    print("Variables that will be matched up")
    print("******************************")
    if len(gridded) > 0:
        print(
            f"The following variables will be matched up with gridded surface data: {','.join(gridded)}"
        )

    print("******************************")
    print(f"** Inferred mapping of model variable names from {sim_dir}")

    all_df_print = copy.deepcopy(all_df).reset_index(drop=True)

    # new tidied variable
    new_variable = []
    for i in range(len(all_df_print)):
        if all_df.variable[i] in var_chosen:
            if all_df.pattern[i] is not None:
                new_variable.append(all_df.variable[i] + "**")
            else:
                new_variable.append(all_df.variable[i])
        else:
            new_variable.append(all_df.variable[i])
    all_df_print["variable"] = new_variable
    all_df_print = all_df_print.sort_values("variable")
    # move variable with ** in it to the top of the data frame
    all_df_print = all_df_print.sort_values(
        by="variable", key=lambda x: x.str.replace(r".*\*\*", "", regex=True)
    )
    all_df_print = all_df_print.reset_index(drop=True)
    # add a new row with --- in it after variables with ** in them
    new_row = pd.DataFrame(
        {"variable": ["---"], "model_variable": ["---"], "pattern": ["---"]}
    )
    all_df_print = pd.concat([all_df_print, new_row], ignore_index=True)
    all_df_print = all_df_print.sort_values(
        by="variable", key=lambda x: x.str.replace(r".*\*\*", "", regex=True)
    )
    all_df_print = all_df_print.reset_index(drop=True)

    print(all_df_print.to_string(index=False))

    print("Are you happy with these matchups? Y/N")

    if ask:
        x = input()
    else:
        x = "y"

    if x.lower() not in ["y", "n"]:
        print("Provide Y or N")
        x = input()

    if x.lower() == "n":
        print("Please adjust your variable names and try again")
        return None

    out = session_info["out_dir"] + "/oceanval_matchups/mapping.csv"
    # check directory exists for out
    out_folder = os.path.dirname(out)
    if not os.path.exists(out_folder):
        os.makedirs(out_folder)

    df_out = all_df.dropna().reset_index(drop=True)
    final_extension = extension_of_directory(sim_dir)
    df_out["pattern"] = [sim_dir + final_extension + x for x in df_out.pattern]
    df_out.to_csv(out, index=False)
    # restrict all_df to only variables chosen
    all_df = all_df.query("variable in @var_chosen").reset_index(drop=True)

    final_extension = extension_of_directory(sim_dir)

    # combine all variables into a list
    all_vars = gridded + point["all"] + point["surface"]
    all_vars = list(set(all_vars))

    df_variables = all_df.query("variable in @all_vars").reset_index(drop=True)
    # remove rows where model_variable is None
    df_variables = df_variables.dropna().reset_index(drop=True)

    patterns = list(set(df_variables.pattern))

    times_dict = dict()


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

    # figure out the lon/lat extent in the model
    with warnings.catch_warnings(record=True) as w:
        lons = session_info["lon_lim"]
        lats = session_info["lat_lim"]

    all_df = all_df.dropna().reset_index(drop=True)
    df_mapping = all_df
    good_model_vars = [x for x in all_df.model_variable if x is not None]

    df_mapping = all_df

    point_all = point["all"] + point["surface"]
    if len(point_all) > 0:
        print("********************************")
        print("Matching up with observational point data")
        print("********************************")

        # if model_variable is None remove from all_df

        for key, value in point.items():
            point_vars = value
            depths = copy.deepcopy(key)
            layer = depths

            # sort the list
            point_vars.sort()

            for vv in point_vars:


                # try finding source in definitions
                variable = vv
                source = definitions[variable].point_source

                out = f"{session_info['out_dir']}/oceanval_matchups/point/{layer}/{variable}/{source}/{source}_{layer}_{variable}.csv"

                if os.path.exists(out) and not overwrite:
                    continue

                all_df = df_mapping
                all_df = all_df.query("model_variable in @good_model_vars").reset_index(
                    drop=True
                )

                all_df = all_df.dropna()
                all_df = all_df.query("variable == @vv").reset_index(drop=True)
                patterns = list(set(all_df.pattern))

                for pattern in patterns:
                    final_extension = extension_of_directory(sim_dir)
                    ensemble = glob.glob(sim_dir + final_extension + pattern)
                    for exc in exclude:
                        ensemble = [
                            x for x in ensemble if f"{exc}" not in os.path.basename(x)
                        ]
                    # find length of example file
                    if strict_names:
                        len_example = len(os.path.basename(example_files[pattern]))
                        ensemble = [
                            x
                            for x in ensemble
                            if len(os.path.basename(x)) == len_example
                        ]

                    df_times = []
                    days = []
                    for ff in ensemble:
                        df_ff = times_dict[ff]
                        df_times.append(
                            pd.DataFrame(
                                {
                                    "month": df_ff.month,
                                    "year": df_ff.year,
                                    "day": df_ff.day,
                                }
                            ).assign(path=ff)
                        )
                    df_times = pd.concat(df_times)

                    # Idea: figure out if it is monthly or daily data
                    # This might help speed things up

                    sim_paths = list(set(df_times.path))
                    sim_paths.sort()
                    # write to the report

                    min_year = df_times.year.min()
                    max_year = df_times.year.max()
                    session_info["min_year"] = min_year
                    # factor in start
                    session_info["min_year"] = max(session_info["min_year"], sim_start)
                    session_info["max_year"] = max_year
                    # factor in end
                    session_info["max_year"] = min(session_info["max_year"], sim_end)

                    def point_match(
                        variable, layer="all", ds_depths=None, df_times=None
                    ):
                        with warnings.catch_warnings(record=True) as w:
                            point_variable = variable
                            model_variable = list(
                                all_df.query(
                                    "variable == @point_variable"
                                ).model_variable
                            )[0]

                            paths = glob.glob(
                                f"{definitions[variable].point_dir}/**.csv"
                            )

                            # try finding source in definitions
                            source = definitions[variable].point_source

                            out = f"{session_info['out_dir']}/oceanval_matchups/point/{layer}/{variable}/{source}/{source}_{layer}_{variable}.csv"

                            for exc in exclude:
                                paths = [
                                    x
                                    for x in paths
                                    if f"{exc}" not in os.path.basename(x)
                                ]
                            
                            def read_csv_simyears(ff, layer = None):
                                df = pd.read_csv(ff)
                                min_year = session_info["min_year"]
                                max_year = session_info["max_year"]
                                if "year" in df.columns:
                                    df = df.query(
                                        "year >= @min_year and year <= @max_year"
                                    ).reset_index(drop=True)
                                if layer == "surface":
                                    if "depth" in df.columns:
                                        df = df.query("depth <= 5").reset_index(
                                            drop=True
                                        )
                                        # drop depth
                                return df

                            df = pd.concat([read_csv_simyears(x, layer) for x in paths])
                            if "year" in df.columns:
                                # find point_start
                                point_start = definitions[variable].point_start
                                point_end = definitions[variable].point_end
                                df = df.query(
                                    "year >= @point_start and year <= @point_end"
                                ).reset_index(drop=True)

                            # remove source if it's in df
                            if "source" in df.columns:
                                df = df.query("source == @source").reset_index(
                                    drop=True
                                )
                            # if it exists, coerce year to int
                            if "year" in df.columns:
                                df = df.assign(year=lambda x: x.year.astype(int))
                                # subset to
                            if "month" in df.columns:
                                df = df.assign(month=lambda x: x.month.astype(int))
                            if "day" in df.columns:
                                df = df.assign(day=lambda x: x.day.astype(int))
                            if layer == "surface":
                                if "depth" in df.columns:
                                    df = df.query("depth <= 5").reset_index(drop=True)
                                    # drop depth
                                    df = df.drop(columns=["depth"])

                            # extract point_time_res from dictionary
                            point_time_res = copy.deepcopy(
                                session_info["point_time_res"]
                            )
                            for x in [
                                x
                                for x in ["year", "month", "day"]
                                if x not in point_time_res
                            ]:
                                if x in df.columns:
                                    df = df.drop(columns=x)

                            sel_these = point_time_res
                            sel_these = [x for x in df.columns if x in sel_these]
                            if "year" in df.columns:
                                paths = list(
                                    set(
                                        df.loc[:, sel_these]
                                        .drop_duplicates()
                                        .merge(df_times)
                                        .path
                                    )
                                )
                            else:
                                paths = list(set(df_times.path))

                            if len(paths) == 0:
                                print(f"No matching times for {variable}")

                            manager = Manager()

                            df_times_new = copy.deepcopy(df_times)


                            valid_cols = [
                                "lon",
                                "lat",
                                "day",
                                "month",
                                "year",
                                "depth",
                                "observation",
                            ]
                            select_these = [x for x in df.columns if x in valid_cols]

                            if len(df) == 0:
                                print("No data for this variable")
                                return None

                            if "year" not in df.columns:
                                try:
                                    point_time_res.remove("year")
                                except:
                                    pass
                            if "month" not in df.columns:
                                try:
                                    point_time_res.remove("month")
                                except:
                                    pass
                            if "day" not in df.columns:
                                try:
                                    point_time_res.remove("day")
                                except:
                                    pass

                            if cores > 1:
                                nc.options(parallel = True)
                            df_all = manager.list()

                            grid_setup = False
                            pool = mp.Pool(cores)

                            pbar = tqdm(total=len(paths), position=0, leave=True)
                            results = dict()

                            if cores > 1:
                                for ff in paths:

                                    temp = pool.apply_async(
                                        mm_match,
                                        [
                                            ff,
                                            model_variable,
                                            df,
                                            df_times_new,
                                            ds_depths,
                                            point_variable,
                                            df_all,
                                            layer,
                                        ],
                                    )

                                    results[ff] = temp

                                for k, v in results.items():
                                    value = v.get()
                                    pbar.update(1)
                            else:
                                for ff in paths:
                                    value = mm_match(
                                        ff,
                                        model_variable,
                                        df,
                                        df_times_new,
                                        ds_depths,
                                        point_variable,
                                        df_all,
                                        layer,
                                    )
                                    pbar.update(1)

                            df_all = list(df_all)
                            df_all = [x for x in df_all if x is not None]
                            # do nothing when there is no data
                            if len(df_all) == 0:
                                print(f"No data for {variable}")
                                time.sleep(1)
                                return False

                            df_all = pd.concat(df_all)
                            nc.options(parallel = False)

                            change_this = [
                                x
                                for x in df_all.columns
                                if x
                                not in [
                                    "lon",
                                    "lat",
                                    "year",
                                    "month",
                                    "day",
                                    "depth",
                                    "observation",
                                ]
                            ][0]
                            #
                            df_all = df_all.rename(
                                columns={change_this: "model"}
                            ).merge(df)
                            # add model to name column names with frac in them
                            df_all = df_all.dropna().reset_index(drop=True)
                            # fix the observations based on obs_unit_multiplier
                            multiplier = definitions[variable].obs_multiplier_point
                            if multiplier != 1:
                                df_all = df_all.assign(
                                    observation=lambda x: x.observation * multiplier
                                )
                            adder = definitions[variable].obs_adder_point
                            if adder != 0:
                                df_all = df_all.assign(
                                    observation=lambda x: x.observation + adder
                                )

                            grouping = copy.deepcopy(point_time_res)
                            grouping.append("lon")
                            grouping.append("lat")
                            grouping.append("depth")
                            grouping = [x for x in grouping if x in df_all.columns]
                            grouping = list(set(grouping))
                            df_all = df_all.dropna().reset_index(drop=True)
                            df_all = df_all.groupby(grouping).mean().reset_index()


                            # create directory for out if it does not exists
                            if not os.path.exists(os.path.dirname(out)):
                                os.makedirs(os.path.dirname(out))
                            if lon_lim is not None:
                                df_all = df_all.query(
                                    f"lon > {lon_lim[0]} and lon < {lon_lim[1]}"
                                )
                            if lat_lim is not None:
                                df_all = df_all.query(
                                    f"lat > {lat_lim[0]} and lat < {lat_lim[1]}"
                                )

                            if len(df_all) > 0:

                                if "year" not in point_time_res:
                                    try:
                                        df_all = df_all.drop(columns="year")
                                    except:
                                        pass
                                if "day" not in point_time_res:
                                    try:
                                        df_all = df_all.drop(columns="day")
                                    except:
                                        pass
                                if "month" not in point_time_res:
                                    try:
                                        df_all = df_all.drop(columns="month")
                                    except:
                                        pass
                                # special handling of temperature
                                if variable == "temperature":
                                    max_model = df_all.model.max()
                                    max_obs = df_all.observation.max()
                                    if max_model > 100 and max_obs < 100:
                                        df_all = df_all.assign(
                                            observation=lambda x: x.observation + 273.15
                                        )   
                                    if max_obs > 100 and max_model < 100:
                                        df_all = df_all.assign(
                                            observation=lambda x: x.observation - 273.15
                                        )

                                df_all.to_csv(out, index=False)
                                # save the definitions
                                out_definitions = out.replace(
                                    ".csv", "_definitions.pkl"
                                )
                                import dill
                                # get the model unit
                                ds = nc.open_data(paths[0], checks=False)
                                the_variable = model_variable.split("+")[0]
                                model_unit = list(
                                    ds.contents.query(
                                        "variable == @the_variable"
                                    ).unit
                                )[0]
                                definitions[variable].model_unit = model_unit
                                dill.dump( definitions, file=open(out_definitions, "wb"))

                                out1 = out.replace(
                                    os.path.basename(out), "matchup_dict.pkl"
                                )
                                # read in the adhoc dict in mm_match

                                point_start = -5000
                                point_end = 10000
                                try:
                                    point_start = definitions[variable].point_start
                                    point_end = definitions[variable].point_end
                                except:
                                    pass

                                min_year = session_info["min_year"]
                                max_year = session_info["max_year"]

                                if point_start > min_year:
                                    min_year = point_start
                                if point_end < max_year:
                                    max_year = point_end

                                the_dict = {
                                    "start": min_year,
                                    "end": max_year,
                                    "point_time_res": point_time_res,
                                    "model_variable": model_variable,
                                }
                                # remove the adhoc dict
                                # write to pickle
                                with open(out1, "wb") as f:
                                    pickle.dump(the_dict, f)

                                return None
                            else:
                                print(f"No data for {variable}")
                                time.sleep(1)
                                return False

                    vv_variable = definitions[vv].long_name

                    out = glob.glob(
                        session_info["out_dir"]
                        + "/"
                        + f"oceanval_matchups/point/all/{vv}/**_all_{vv}.csv"
                    )

                    if len(out) > 0:
                        if session_info["overwrite"] is False:
                            continue

                    print(
                        f"Matching up model output of {key} {vv_variable} with in-situ observational data"
                    )

                    # try:
                    if True:
                        point_match(
                            vv, ds_depths=ds_depths, df_times=df_times, layer=key
                        )
                    # except:
                    #     pass

                    output_warnings = []
                    for ww in session_warnings:
                        if ww is not None:
                            if ww in output_warnings:
                                continue
                            if "CDO found more than one time variable" in ww:
                                continue
                            if "coordinates variable time" in ww:
                                continue
                            output_warnings.append(str(ww))

                    if len(output_warnings) > 0:
                        output_warnings = list(set(output_warnings))
                        print(f"Warnings for {vv_variable}")
                        for ww in output_warnings:
                            warnings.warn(message=ww)
                    # empty session warnings
        while len(session_warnings) > 0:
            session_warnings.pop()

    gridded_matchup(
        df_mapping=df_mapping,
        folder=sim_dir,
        var_choice=gridded,
        exclude=exclude,
        sim_start=sim_start,
        sim_end=sim_end,
        lon_lim=lon_lim,
        lat_lim=lat_lim,
        times_dict=times_dict,
        example_files=example_files,
    )

    if len(session_info["end_messages"]) > 0:
        print("########################################")
        print("########################################")
        print("Important messages about matchups:")
        print("*" * 30)
        # write this info to a md report

        for x in session_info["end_messages"]:
            print(x)
        print("########################################")
        print("########################################")

    # store definitions as a pickle
    ff = session_info["out_dir"] + "oceanval_matchups/definitions.pkl"
    if os.path.exists(ff):
        os.remove(ff)
    import dill

    dill.dump(definitions, file=open(ff, "wb"))

    # output short titles
    ff = session_info["out_dir"] + "oceanval_matchups/short_titles.pkl"
    short_titles = session_info["short_title"]
    with open(ff, "wb") as f:
        pickle.dump(short_titles, f)
    
    # now add to the list of variables matched up
    ff = session_info["out_dir"] + "oceanval_matchups/variables_matched.pkl"
    if os.path.exists(ff):
        with open(ff, "rb") as f:
            variables_matched = pickle.load(f)
    else:
        variables_matched = []
    for vv in list(df_mapping.variable):
        if vv not in variables_matched:
            variables_matched.append(vv)
    with open(ff, "wb") as f:
        pickle.dump(variables_matched, f)


