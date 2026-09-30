"""Small simulations written to disk, for the tests that read model output."""

import os

import numpy as np
import xarray as xr


def write_simulation(root, years=(2011, 2012), tracers=False):
    """A small NEMO-like simulation, filed as root/<year>/01/<file>: a grid_T
    stream of temperature, and with tracers, a ptrc_T stream of nitrate."""
    streams = [("grid_T", "thetao", "sea water potential temperature", "degC")]
    if tracers:
        streams.append(("ptrc_T", "N3_n", "nitrate nitrogen", "mmol N m-3"))
    for year in years:
        folder = os.path.join(root, str(year), "01")
        os.makedirs(folder, exist_ok=True)
        dims = ("time", "deptht", "y", "x")
        for stream, variable, long_name, units in streams:
            dataset = xr.Dataset(
                {
                    variable: (
                        dims,
                        np.random.rand(1, 3, 2, 2).astype("f4"),
                        {"long_name": long_name, "units": units},
                    )
                }
            )
            dataset["time"] = ("time", [0.0], {"units": f"days since {year}-01-01"})
            dataset.to_netcdf(
                os.path.join(folder, f"nemo_1m_{year}0101_{year}0131_{stream}.nc")
            )


def write_fvcom(root):
    """A month of raw FVCOM output, filed as root/2012/01/<file>."""
    folder = os.path.join(root, "2012", "01")
    os.makedirs(folder)
    dataset = xr.Dataset(
        {
            "nv": (("three", "nele"), np.array([[1, 1], [2, 4], [4, 3]], dtype="i4")),
            "lon": ("node", np.array([-5.0, -4.9, -5.0, -4.9], dtype="f4")),
            "lat": ("node", np.array([50.0, 50.0, 50.1, 50.1], dtype="f4")),
            "h": ("node", np.full(4, 20.0, dtype="f4")),
            "temp": (
                ("time", "siglay", "node"),
                np.random.rand(1, 5, 4).astype("f4"),
                {"long_name": "temperature", "units": "degree_C"},
            ),
        }
    )
    dataset["time"] = (
        "time",
        np.array([55927.0]),
        {"units": "days since 1858-11-17 00:00:00"},
    )
    dataset.to_netcdf(os.path.join(folder, "run_avg_0001.nc"))
