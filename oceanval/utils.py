import nctoolkit as nc
import xarray as xr
import numpy as np
import subprocess
from oceanval.session import session_info


def bin_value(x, bin_res):
    return np.floor((x + bin_res / 2) / bin_res + 0.5) * bin_res - bin_res / 2


def extension_of_directory(starting_directory, exclude=[]):
    levels = session_info["levels_down"]

    new_directory = ""
    for i in range(levels):
        new_directory = new_directory + "/**"
    return new_directory + "/"



def get_extent(ff):
    # add docstring
    """ "
    Get the extent of a netcdf file

    Parameters
    ----------
    ff : str
        The path to the netcdf file

    Returns
    -------
    extent : list
        A list of the form [lon_min, lon_max, lat_min, lat_max]

    """

    ds = nc.open_data(ff)
    ds.subset(variables=ds.variables[0])
    ds.top()
    ds.tmean()
    ds.as_missing(0)
    ds_xr = ds.to_xarray()
    lon_name = [x for x in ds_xr.coords if "lon" in x][0]
    lat_name = [x for x in ds_xr.coords if "lat" in x][0]

    df = ds_xr.to_dataframe().reset_index()
    df = ds.to_dataframe().dropna().reset_index()
    df = df.rename(columns={lon_name: "lon", lat_name: "lat"})
    df = df.dropna()
    max_lon = df["lon"].max()
    if max_lon > 180:
        new_lon = df["lon"].values % 360
        new_lon = new_lon - 180
        lon_min = float(new_lon.min())
        lon_max = float(new_lon.max())
    else:
        lon_min = float(df.lon.min())
        lon_max = float(df.lon.max())
    lat_min = float(df.lat.min())
    lat_max = float(df.lat.max())
    return [lon_min, lon_max, lat_min, lat_max]

    lons = ds_xr[lon_name].values
    lons = lons.flatten()
    # as a unique, sorted list
    lons = list(set(lons))
    lats = ds_xr[lat_name].values
    lats = lats.flatten()
    # as a unique, sorted list
    lats = list(set(lats))
    lats.sort()
    lons.sort()
    lon_res = np.abs(lons[2] - lons[1])
    lat_res = np.abs(lats[2] - lats[1])
    print(lon_res)
    print(lat_res)
    ds = nc.open_data(ff)
    ds.subset(variables=ds.variables[0])
    ds.top()
    ds.tmax()
    ds.to_latlon(lon=[-180, 180], lat=[-90, 90], res=[lon_res, lat_res])
    # rename
    lon_min = df.lon.min()
    lon_max = df.lon.max()
    lat_min = df.lat.min()
    lat_max = df.lat.max()
    lons = [lon_min, lon_max]
    lats = [lat_min, lat_max]
    extent = [
        lons[0] - lon_res,
        lons[1] + lon_res,
        lats[0] - lat_res,
        lats[1] + lat_res,
    ]
    #
    return extent


def get_resolution(ff):
    ds = nc.open_data(ff, checks=False)
    var = ds.variables[0]
    ds = xr.open_dataset(ff)
    lon_name = [x for x in list(ds.coords) if "lon" in x][0]
    lat_name = [x for x in list(ds.coords) if "lat" in x][0]
    var_dims = ds[var].dims
    extent = get_extent(ff)
    if lon_name in var_dims:
        if lat_name in var_dims:
            n_lon = len(ds[lon_name])
            n_lat = len(ds[lat_name])
            lon_max = float(ds[lon_name].max())
            lon_min = float(ds[lon_name].min())
            lat_max = float(ds[lat_name].max())
            lat_min = float(ds[lat_name].min())
            lon_res = (lon_max - lon_min) / (n_lon - 1)
            lat_res = (lat_max - lat_min) / (n_lat - 1)
            return [lon_res, lat_res]
    else:
        # get the final two var_dims
        var_dims = var_dims[-2:]
        # lat should be the second
        n_lat = len(ds[var_dims[1]])
        n_lon = len(ds[var_dims[0]])
        lon_res = (extent[1] - extent[0]) / n_lon
        lat_res = (extent[3] - extent[2]) / n_lat
        return [lon_res, lat_res]
