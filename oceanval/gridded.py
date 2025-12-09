import glob
import copy
import os
import warnings
import pickle
import pandas as pd
import time
import numpy as np
import nctoolkit as nc
import xarray as xr

from oceanval.fixers import tidy_warnings
from oceanval.utils import extension_of_directory
from oceanval.session import session_info
from oceanval.parsers import Validator, definitions


def gridded_matchup(
    df_mapping=None,
    folder=None,
    var_choice=None,
    exclude=None,
    sim_start=None,
    sim_end=None,
    lon_lim=None,
    lat_lim=None,
    times_dict=None,
    example_files = {}
):
    """
    Function to create gridded matchups for a given set of variables

    Parameters
    ----------
    df_mapping : pandas.DataFrame
        DataFrame containing the mapping between model variables and gridded observations
    folder : str
        Path to folder containing model data
    var_choice : list
        List of variables to create matchups for
    exclude : list
        List of strings to exclude from the file search
    sim_start : int
        Start year for model simulations
    sim_end : int
        End year for model simulations
    lon_lim : list
        Longitude limits for subsetting
    lat_lim : list
        Latitude limits for subsetting
    times_dict : dict
        Dictionary with file paths as keys and corresponding time DataFrames as values
    Returns
    -------
    None

    """

    start_cores = session_info["cores"]


    all_df = df_mapping
    # if model_variable is None remove from all_df
    good_model_vars = [x for x in all_df.model_variable if x is not None]

    all_df = all_df.query("model_variable in @good_model_vars").reset_index(drop=True)

    all_df = all_df.dropna()

    vars = []
    for x in definitions.keys:
        if definitions[x].gridded:
            vars.append(x)

    vars = [x for x in vars if x in var_choice]
    vars.sort()

    if len(vars) > 0:
        # first up, do the top

        mapping = dict()

        for vv in vars:
            vertical_gridded = definitions[vv].vertical_gridded
            climatology = definitions[vv].climatology
                # if global is not selected, stop
            # a dictionary for summarizing things
            var_dict = {}
            out_dir = session_info["out_dir"]
            out = glob.glob(
                out_dir + f"oceanval_matchups/gridded/{vv}/*_{vv}_surface.nc"
            )
            if len(out) > 0:
                if session_info["overwrite"] is False:
                    continue
            # figure out the data source
            #
            # check if this directory is empty
            dir_var = definitions[vv].gridded_dir 

            vv_source = definitions[vv].gridded_source

            #
            vv_name = definitions[vv].long_name

            print(
                f"Matching up surface {vv_name} with {vv_source.upper()} gridded data"
            )
            print("**********************")
            df = df_mapping.query("variable == @vv").reset_index(drop=True)

            mapping[vv] = list(df.query("variable == @vv").model_variable)[0]

            selection = mapping[vv].split("+")

            patterns = set(df.pattern)
            pattern = list(patterns)[0]

            final_extension = extension_of_directory(folder)
            paths = glob.glob(folder + final_extension + pattern)
            if session_info["strict_names"]:
                len_example = len(os.path.basename(example_files[pattern]))
                paths = [x for x in paths if len(os.path.basename(x)) == len_example]

            for exc in exclude:
                paths = [
                    x for x in paths if f"{exc}" not in os.path.basename(x)
                ]
            
            # handle required
            if session_info["require"] is not None:
                for req in session_info["require"]:
                    paths = [x for x in paths if f"{req}" in os.path.basename(x)]


            all_years = []
            for ff in paths:
                all_years += list(times_dict[ff].year)

            all_years = list(set(all_years))
            n_years = len(all_years)

            sim_years = range(sim_start, sim_end + 1)
            sim_years = [x for x in all_years if x in sim_years]
            min_year = min(sim_years)
            max_year = max(sim_years)

            start = definitions[vv].gridded_start
            end = definitions[vv].gridded_end
            if start is not None:
                sim_years = [x for x in sim_years if x >= start]
            if end is not None:
                sim_years = [x for x in sim_years if x <= end]

            if len(sim_years) == 0:
                # specific error for glodap
                session_info["end_messages"] += [f"No simulation years found for {vv}. Please check start and end args!"]
                warnings.warn(f"No simulation years found for {vv}. Please check start and end args!")
                return None
            # now simplify paths, so that only the relevant years are used
            new_paths = []
            year_options = list(
                set(
                    pd.concat([x for x in times_dict.values()])
                    .loc[:, ["year", "month"]]
                    .drop_duplicates()
                    .groupby("year")
                    .size()
                    # must be at least 12
                    .pipe(lambda x: x[x >= 12])
                    .reset_index()
                    .year
                )
            )
            old_years = sim_years
            n_years = len(sim_years)
            sim_years = [x for x in sim_years if x in year_options]
            month_sel = range(1, 13)
            if len(sim_years) == 0:
                sim_years = old_years
                month_sel = list(
                    set(
                        pd.concat([x for x in times_dict.values()])
                        .loc[:, ["year", "month"]]
                        .drop_duplicates()
                        .month
                    )
                )

            for ff in paths:
                if len([x for x in times_dict[ff].year if x in sim_years]) > 0:
                    new_paths.append(ff)

            paths = list(set(new_paths))
            paths.sort()

            # handle 

            var_dict["clim_years"] = [min(sim_years), max(sim_years)]

            # get the number of paths

            with warnings.catch_warnings(record=True) as w:

                new_paths = copy.deepcopy(paths)

                ds_model = nc.open_data(paths, checks=False)
                ds_model.subset(years=sim_years)
                ds_model.subset(variables=selection)
                if vertical_gridded is False:
                    ds_zz = nc.open_data(ds_model[0], checks = False)
                    ds_zz.subset(variables=selection)
                    ds_zz.run()
                    if ds_zz.contents.nlevels.values[0] > 1:
                        ds_model.cdo_command("topvalue")
                if session_info["as_missing"] is not None:
                    ds_model.as_missing(session_info["as_missing"])
                ds_model.merge("time")
                ds_model.tmean(
                    ["year", "month"], align="left"
                )

                # the code below needs to be simplifed
                # essentially anything with a + in the mapping should be split out
                # and then the command should be run for each variable

                var_unit = None
                for vv in list(df.variable):
                    if "+" in mapping[vv]:
                        command = f"-aexpr,{vv}=" + mapping[vv]
                        ds_model.cdo_command(command)
                        drop_these = mapping[vv].split("+")
                        ds_contents = ds_model.contents
                        ds_contents = ds_contents.query(
                            "variable in @drop_these"
                        )
                        var_unit = ds_contents.unit[0]
                        ds_model.drop(variables=drop_these)

                        ds_model.run()
                        if var_unit is not None:
                            ds_model.set_units(
                                {vv: var_unit}
                            )

                        ds_model.run()

            tidy_warnings(w)

            # figure out the start and end year
            with warnings.catch_warnings(record=True) as w:
                start_year = min(ds_model.years)
                end_year = max(ds_model.years)

                # Read in the monthly observational data
                thredds = definitions[vv].thredds
                if thredds == False:
                    if dir_var.endswith(".nc"):
                        vv_file = dir_var
                    else:
                        vv_file = nc.create_ensemble(dir_var)
                else:
                    vv_file = dir_var  # thredds URL
                recipe = definitions[vv].recipe
                
                # some special handling for occci files
                occci = False
                if recipe:
                    if vv_source.lower() == "occci":
                        new_files = []
                        for yy in sim_years:
                            for ff in vv_file:
                                if f"/{yy}/" in ff:
                                    new_files.append(ff)
                        vv_file = new_files
                        occci = True
                extracted = False
                if recipe:
                    if vv_source == "GLODAPv2.2016b":
                        print("Downloading GLODAPv2.2016b data")
                        ds_obs = nc.open_url(vv_file)
                        print("Download complete")
                        variable = definitions[vv].obs_variable
                        ds_obs.subset(variables=variable)
                        ds_obs.run()
                        # we need to set the time, because it does not exists
                        ds_obs.cdo_command(f"setreftime,1800-01-01,00:00:00,days -settaxis,2000-01-01,00:00:00,1month")
                        ds_obs.run()
                        thredds = False
                        extracted = True

                if not extracted:
                    if thredds:
                        ds_obs = nc.open_thredds(vv_file, checks=False)
                    else:
                        ds_obs = nc.open_data(
                            vv_file,
                            checks=False,
                        )
                bad_clim = False

                # use ncks to spatially subset to lon_lim and lat_lim
                if occci:
                    variable = definitions[vv].obs_variable
                    ds_obs.subset(variables=variable)
                    if lon_lim is not None:
                        ds_obs.crop(lon=lon_lim, lat=lat_lim)

                if vertical_gridded is False:
                    if thredds:
                        ds_zz = nc.open_thredds(ds_obs[0], checks = False)
                    else:
                        ds_zz = nc.open_data(vv_file, checks =False)
                    variable = definitions[vv].obs_variable
                    if variable == "auto":
                        variable = ds_zz.variables[0]
                    if ds_zz.contents.query("variable == @variable").nlevels.values[0] > 1:
                        if recipe:
                            ds_obs.top()
                        else:
                            ds_obs.cdo_command("topvalue")


                try:
                    min_obs_year = min(ds_obs.years)
                    max_obs_year = max(ds_obs.years)
                    if climatology is True:
                        if (min_obs_year < max_obs_year):
                            bad_clim = True
                    if climatology is False:
                        if (min_obs_year < max_obs_year):
                            if sim_start > max_obs_year or sim_end < min_obs_year:
                                session_info["end_messages"] += [f"No observation years found for gridded {vv}. Please check start and end args!"]
                                return None
                    if climatology is False:
                        ds_obs.subset(years=sim_years)
                    ds_obs.subset(variables=definitions[vv].obs_variable)
                    ds_obs.tmean(["year", "month"], align="left")
                    ds_obs.merge("time")
                    ds_obs.tmean(["year", "month"], align="left")
                except:
                    pass

                if climatology is False:
                    year_sel = [x for x in ds_model.years if x in ds_obs.years]
                    if len(year_sel) == 0:
                        raise ValueError("There do not appear to be any years in common between model and observation!  ")
                    sim_years = year_sel
                    min_year = min(year_sel)
                    max_year = max(year_sel)
                    ds_obs.subset(years=year_sel)
                    ds_model.subset(years=year_sel)
                    ds_obs.subset(variables=definitions[vv].obs_variable)
                    ds_obs.run()

                obs_unit_multiplier = definitions[vv].obs_multiplier_gridded
                if obs_unit_multiplier != 1:
                    ds_obs *  obs_unit_multiplier
                obs_adder = definitions[vv].obs_adder_gridded
                if obs_adder != 0:
                    ds_obs + obs_adder
            
                if bad_clim:
                    raise ValueError(f"Observational data for {vv} appears to not be a climatology, but the climatology argument is set to True. Please fix this!") 

                if len(month_sel) < 12:
                    try:
                        months = ds.months
                        if len(months) > 1:
                            ds_obs.subset(months=month_sel)
                    except:
                        pass
                
                if definitions[vv].obs_variable != "auto":
                    ds_obs.subset(variables=definitions[vv].obs_variable)

                if climatology is False:
                    obs_years = ds_obs.years
                    min_obs_year = min(obs_years)
                    max_obs_year = max(obs_years)

            tidy_warnings(w)

            with warnings.catch_warnings(record=True) as w:
                if climatology is True:
                    ds_model.tmean("month", align="left")
                try:
                    if len(obs_years) == 1:
                        ds_obs.tmean("month", align="left")
                except:
                    pass

                if len(ds_obs) > 1:
                    ds_obs.merge("time")
                    ds_obs.run()

                lons = session_info["lon_lim"]
                lats = session_info["lat_lim"]
                if lons is None:
                    lons = [-180, 180]
                    lats = [-90, 90]

                # # figure out the lon/lat extent in the model

                ds_obs.rename({ds_obs.variables[0]: "observation"})
                ds_model.rename({ds_model.variables[0]: "model"})
                ds_model.run()
                ds_obs.run()

                # it is possible the years do not overlap, e.g. with satellite Chl
                if len(ds_model.times) > 12:
                    years1 = ds_model.years
                    years2 = ds_obs.years
                    all_years = [x for x in years1 if x in years2]
                    if len(all_years) != len(years1):
                        if len(all_years) != len(years2):
                            ds_obs.subset(years=all_years)
                            ds_model.subset(years=all_years)
                            ds_obs.run()
                            ds_model.run()
                if len(ds_obs) > 1:
                    ds_obs.merge("time")

                ds_obs.run()
                ds_model.run()

                if vertical_gridded is False:
                    contents = ds_model.contents
                    nlevels = contents.nlevels[0]
                    if nlevels > 1:
                        if recipe:
                            ds_obs.top()
                        else:
                            ds_obs.cdo_command("topvalue")
                try:
                    n_times = len(ds_obs.times)
                except:
                    n_times = 1
                try:
                    n_years = len(ds_obs.years)
                except:
                    n_years = 1

                ds_obs.run()
                ds_model.run()
                ds2 = ds_model.copy()
                if len(ds_model.times) == 12:
                    ds_model.set_year(2000)

                if len(ds_model.times) > 12:
                    # at this point, we need to identify the years that are common to both
                    ds_times = ds_model.times
                    try:
                        ds_years = [x.year for x in ds_times]
                        ds_months = [x.month for x in ds_times]
                    except:
                        ds_years = [int(str(x).split("T")[0].split("-")[0]) for x in ds_times ]
                        ds_months = [int(str(x).split("T")[0].split("-")[1]) for x in ds_times]

                    df_surface = pd.DataFrame(
                        {"year": ds_years, "month": ds_months}
                    )

                    ds_times = ds_obs.times
                    try:
                        ds_years = [x.year for x in ds_times]
                        ds_months = [x.month for x in ds_times]
                    except:
                        ds_years = [int(str(x).split("T")[0].split("-")[0]) for x in ds_times ]
                        ds_months = [int(str(x).split("T")[0].split("-")[1]) for x in ds_times]
                    df_obs = pd.DataFrame(
                        {"year": ds_years, "month": ds_months}
                    )
                    sel_years = list(
                        df_surface.merge(df_obs)
                        .groupby("year")
                        .count()
                        # only 12
                        .query("month == 12")
                        .reset_index()
                        .year.values
                    )
                    ds_model.subset(years=sel_years)
                    if n_years > 1: 
                        ds_obs.subset(years=sel_years)

                if len(ds_model.times) < 12:
                    sel_months = list(set(ds_model.months))
                    sel_months.sort()
                    if n_times > 1: 
                        ds_obs.subset(months=sel_months)

                # now do the surface
                ds_model_surface = ds_model.copy()
                contents = ds_model_surface.contents
                nlevels = contents.nlevels[0]
                if nlevels > 1:
                    ds_model_surface.cdo_command("topvalue")
                ds_obs_surface = ds_obs.copy()
                contents = ds_obs_surface.contents
                nlevels = contents.nlevels[0]
                if nlevels > 1: 
                    ds_obs_surface.cdo_command("topvalue")
                ds_model_surface.regrid(ds_obs_surface, method="bil")

                n_obs_times = len(ds_obs_surface.times)
                if n_obs_times <= 1:
                    ds_model_surface.tmean()
                ds_obs_surface.append(ds_model_surface)

                if len(ds_model_surface.times) > 12:
                    ds_obs_surface.merge("variable", match=["year", "month"])
                else:
                    # run both
                    ds_obs_surface.run()
                    ds_model_surface.run()
                    ds_obs_surface.merge("variable", match="month")

                ds_obs_surface.set_fill(-9999)
                ds_mask = ds_obs_surface.copy()
                ds_mask.assign( mask_these=lambda x: -1e30 * ((isnan(x.observation) + isnan(x.model)) > 0), drop=True,)
                ds_mask.as_missing([-1e40, -1e20])
                ds_mask.run()
                ds_obs_surface + ds_mask

                out_file = (
                    session_info["out_dir"]
                    + f"oceanval_matchups/gridded/{vv}/{vv_source}_{vv}_surface.nc"
                )
                out_file_vertical = (
                    session_info["out_dir"]
                    + f"oceanval_matchups/gridded/{vv}/{vv_source}_{vv}_vertical.nc"
                )

                # check directory exists for out_file
                if not os.path.exists(os.path.dirname(out_file)):
                    os.makedirs(os.path.dirname(out_file))
                # remove the file if it exists
                if os.path.exists(out_file):
                    os.remove(out_file)
                ds_obs_surface.set_precision("F32")
                ds_model_surface = ds_obs_surface.copy()

                if lon_lim is not None and lat_lim is not None:
                    ds_model_surface.subset(lon=lon_lim, lat=lat_lim)

                ds_model_surface.run()

                # unit may need some fiddling
                out1 = out_file.replace(
                    os.path.basename(out_file), "matchup_dict.pkl"
                )
                the_dict = {"start": min_year, "end": max_year}
                # write to pickle
                with open(out1, "wb") as f:
                    pickle.dump(the_dict, f)

                ds_model_surface.subset(lon=lons, lat=lats)
                ds_model_surface.run()

                lon_name = [x for x in ds_model_surface.to_xarray().coords if "lon" in x][0 ]
                lat_name = [x for x in ds_model_surface.to_xarray().coords if "lat" in x][0 ]
                ds_test = ds_model_surface.copy()
                ds_test.subset(variable = "observation")
                ds_test.tmean()
                ds_test.run()
                df_test = ds_test.to_dataframe().reset_index().dropna()
                lons = df_test[lon_name].values
                # handle lon > 180 properly
                lons = ((lons + 180) % 360) - 180
                lon_max = lons.max() 
                lon_min = lons.min()
                lat_max = df_test[lat_name].max()
                lat_min = df_test[lat_name].min()
                ds_model_surface.run()
#                ds_model_surface.subset(lon=[lon_min, lon_max], lat=[lat_min, lat_max])
                ds_model_surface.run()

                # special handling of temperature
                if vv == "temperature":
                    max_model = ds_model_surface.to_xarray().model.max()
                    max_obs = ds_model_surface.to_xarray().observation.max()
                    abs_diff = abs(max_model - max_obs)
                    if abs_diff > 40:
                        if max_model > max_obs:
                            add_to_obs = +273.15
                        else:
                            add_to_obs = -273.15
                        ds_model_surface.assign(observation = lambda x: x.observation + add_to_obs)
                    else:
                        add_to_obs = 0

                ds_model_surface.to_nc(out_file, zip=True, overwrite=True)
                out_file = out_file.replace(".nc", "_definitions.pkl")
                # save definitions
                # change start to min year
                definitions[vv].gridded_start = min_year
                definitions[vv].gridded_end = max_year
                with open(out_file, "wb") as f:
                    pickle.dump(definitions, f)


                if vertical_gridded:

                    if vertical_gridded is True:
                        levels = ds_obs.levels
                        if session_info["ds_depths"] != "z_level":
                            ds_model.vertical_interp(levels, thickness = session_info["ds_thickness"]) 
                        else:
                            ds_model.vertical_interp(levels , fixed = True)

                    ds_model.regrid(ds_obs, method="bil")
                    n_obs_times = len(ds_obs.times)
                    if n_obs_times <= 1:
                        ds_model.tmean()
                    ds_obs.append(ds_model)

                    if n_obs_times <= 1:
                            ds_obs.merge("variable")
                    else:
                        if len(ds_model.times) > 12:
                            ds_obs.merge("variable", match=["year", "month"])
                        else:
                            ds_obs.merge("variable", match="month")
                    ds_obs.set_fill(-9999)
                    ds_mask = ds_obs.copy()
                    ds_mask.assign( mask_these=lambda x: -1e30 * ((isnan(x.observation) + isnan(x.model)) > 0), drop=True,)
                    ds_mask.as_missing([-1e40, -1e20])
                    ds_mask.run()
                    ds_obs + ds_mask

                    out_file = (
                        session_info["out_dir"]
                        + f"oceanval_matchups/gridded/{vv}/{vv_source}_{vv}_surface.nc"
                    )

                    # check directory exists for out_file
                    if not os.path.exists(os.path.dirname(out_file_vertical)):
                        os.makedirs(os.path.dirname(out_file_vertical))
                    # remove the file if it exists
                    if os.path.exists(out_file_vertical):
                        os.remove(out_file_vertical)
                    ds_obs.set_precision("F32")
                    ds_model = ds_obs.copy()

                    if lon_lim is not None and lat_lim is not None:
                        ds_model.subset(lon=lon_lim, lat=lat_lim)

                    ds_model.run()

                    # unit may need some fiddling
                    out1 = out_file.replace(
                        os.path.basename(out_file), "matchup_dict.pkl"
                    )
                    the_dict = {"start": min_year, "end": max_year}
                    # write to pickle
                    with open(out1, "wb") as f:
                        pickle.dump(the_dict, f)

                    ds_test = ds_model.copy()
                    ds_test.subset(variable = "observation")
                    ds_test.tmean()
                    ds_test.run()
                    df_test = ds_test.to_dataframe().reset_index().dropna()
                    lons = df_test[lon_name].values
                    lons = ((lons + 180) % 360) - 180
                    lon_max = lons.max()
                    lon_min = lons.min()
                    lat_max = df_test[lat_name].max()
                    lat_min = df_test[lat_name].min()

                    ds_model.subset(lon=[lon_min, lon_max], lat=[lat_min, lat_max])

                    # special handling of temperature
                    if vv == "temperature":
                        max_model = ds_model.to_xarray().model.max()
                        max_obs = ds_model.to_xarray().observation.max()
                        abs_diff = abs(max_model - max_obs)
                        if abs_diff > 40:
                            if max_model > max_obs:
                                add_to_obs = +273.15
                            else:
                                add_to_obs = -273.15
                            ds_model.assign(observation = lambda x: x.observation + add_to_obs)
                        else:
                            add_to_obs = 0


                    ds_model.to_nc(out_file_vertical, zip=True, overwrite=True)
                out_file = out_file.replace(".nc", "_definitions.pkl")
                # save definitions
                with open(out_file, "wb") as f:
                    pickle.dump(definitions, f)

            tidy_warnings(w)

            out = (
                session_info["out_dir"]
                + f"oceanval_matchups/gridded/{vv}/{vv}_summary.pkl"
            )
            if not os.path.exists(os.path.dirname(out)):
                os.makedirs(os.path.dirname(out))
            var_dict["clim_years"] = [min(sim_years), max(sim_years)]
            with open(out, "wb") as f:
                pickle.dump(var_dict, f)
        
        session_info["cores"] = start_cores
        nc.options(cores = start_cores)

        return None
