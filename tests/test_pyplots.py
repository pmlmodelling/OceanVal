import matplotlib
matplotlib.use("Agg")

import numpy as np
import pandas as pd
import pytest

from oceanval import pyplots


def _locs_df():
    return pd.DataFrame({"lon": [-5, -4, -3, -2], "lat": [50, 51, 52, 53]})


def _point_df(with_month=False):
    n = 24 if with_month else 6
    rng = np.random.default_rng(0)
    df = pd.DataFrame(
        {
            "lon": rng.uniform(-10, 0, n),
            "lat": rng.uniform(45, 55, n),
            "model": rng.uniform(5, 15, n),
            "observation": rng.uniform(5, 15, n),
        }
    )
    if with_month:
        df["month"] = list(range(1, 13)) * 2
    return df


def _seasonal_df(months):
    rng = np.random.default_rng(1)
    rows = []
    for month in months:
        for lon in range(-4, 0):
            for lat in range(48, 52):
                rows.append({"lon": lon, "lat": lat, "month": month, "model": rng.uniform(5, 15), "observation": rng.uniform(5, 15)})
    df = pd.DataFrame(rows)
    return df


class TestPyplots:
    def test_plot_locations_map(self):
        pyplots.plot_locations_map(_locs_df())

    def test_plot_variable_map(self):
        df = _point_df()
        pyplots.plot_variable_map(df, "temperature", "degC", "sea surface", "temperature")

    def test_plot_bias_map_no_month(self):
        df = _point_df()
        pyplots.plot_bias_map(df, "degC", "temperature", "sea surface")

    def test_plot_bias_map_with_month(self):
        df = _point_df(with_month=True)
        pyplots.plot_bias_map(df, "degC", "temperature", "sea surface")

    def test_plot_model_obs_scatter_no_facet(self):
        df = _point_df()
        pyplots.plot_model_obs_scatter(df, "temperature", "degC", facet_by_month=False)

    def test_plot_model_obs_scatter_facet(self):
        df = _point_df(with_month=True)
        pyplots.plot_model_obs_scatter(df, "temperature", "degC", facet_by_month=True)

    def test_plot_seasonal_grid(self):
        months = [1, 2, 3, 4, 5, 6]
        df_model = _seasonal_df(months)
        df_obs = _seasonal_df(months)
        df_diff = df_model.merge(df_obs, on=["lon", "lat", "month"], suffixes=("", "_obs"))
        df_diff = df_diff.assign(diff=df_diff["model"] - df_diff["observation_obs"])
        pyplots.plot_seasonal_grid(df_model, df_obs, df_diff, "degC", months, fixed_scale=False)

    def test_plot_regional_timeseries(self):
        rng = np.random.default_rng(2)
        rows = []
        for region in ["Region A", "Region B"]:
            for variable in ["model", "observation"]:
                for month in range(1, 13):
                    rows.append({"long_name": region, "variable": variable, "month": month, "value": rng.uniform(5, 15)})
        df_all = pd.DataFrame(rows)
        pyplots.plot_regional_timeseries(df_all)

    def test_plot_depth_locations_map(self):
        rng = np.random.default_rng(3)
        rows = []
        for depth in ["0-10m", "10-30m", "30-60m"]:
            for _ in range(5):
                rows.append({"lon": rng.uniform(-10, 0), "lat": rng.uniform(45, 55), "depth": depth})
        df_mapped = pd.DataFrame(rows)
        pyplots.plot_depth_locations_map(df_mapped)

    def test_plot_taylor_like(self):
        rng = np.random.default_rng(4)
        rows = []
        for variable in ["Temperature", "Salinity"]:
            for _ in range(20):
                rows.append({"variable": variable, "model": rng.uniform(5, 15), "observation": rng.uniform(5, 15)})
        df_taylor = pd.DataFrame(rows)
        pyplots.plot_taylor_like(df_taylor)

    def test_plot_correlation_map(self):
        rng = np.random.default_rng(5)
        rows = []
        for variable in ["Temperature", "Salinity"]:
            for lon in range(-4, 0):
                for lat in range(48, 52):
                    rows.append({"variable": variable, "lon": lon, "lat": lat, "cor": rng.uniform(-1, 1)})
        df_cor = pd.DataFrame(rows)
        pyplots.plot_correlation_map(df_cor, global_grid=False)

    def test_plot_depth_matchup_map(self):
        rng = np.random.default_rng(6)
        rows = []
        for variable in ["Temperature", "Salinity"]:
            for depth_bin in ["0-10m", "10-30m"]:
                for _ in range(5):
                    rows.append({"variable": variable, "depth_bin": depth_bin, "lon": rng.uniform(-10, 0), "lat": rng.uniform(45, 55)})
        df_map = pd.DataFrame(rows)
        pyplots.plot_depth_matchup_map(df_map)
