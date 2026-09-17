import numpy as np
import nctoolkit as nc
import xarray as xr

from oceanval.gridded import _lonlat_bounds, _regrid_onto_common_grid


def _write_grid(path, lon, lat, varname):
    ds = xr.Dataset(
        {varname: (("lat", "lon"), np.random.rand(len(lat), len(lon)).astype("f4"))},
        coords={"lon": lon, "lat": lat},
    )
    ds.lon.attrs = {"units": "degrees_east", "standard_name": "longitude"}
    ds.lat.attrs = {"units": "degrees_north", "standard_name": "latitude"}
    ds.to_netcdf(path)


class TestLonLatBounds:
    def test_reads_the_grid_extent(self, tmp_path):
        path = str(tmp_path / "grid.nc")
        _write_grid(path, np.linspace(-10, 10, 5), np.linspace(40, 50, 5), "x")

        ds = nc.open_data(path, checks=False)
        lon_min, lon_max, lat_min, lat_max = _lonlat_bounds(ds)

        assert lon_min == -10
        assert lon_max == 10
        assert lat_min == 40
        assert lat_max == 50


class TestRegridOntoCommonGrid:
    def test_a_regional_model_crops_global_obs_and_skips_to_latlon(self, tmp_path):
        # a small regional model (comparable to a NW European Shelf domain)
        model_path = str(tmp_path / "model.nc")
        _write_grid(model_path, np.linspace(-3, 3, 12), np.linspace(48, 58, 20), "model")

        # a global observational product
        obs_path = str(tmp_path / "obs.nc")
        _write_grid(
            obs_path,
            np.arange(-179.875, 180, 0.25),
            np.arange(-89.875, 90, 0.25),
            "observation",
        )

        ds_model = nc.open_data(model_path, checks=False)
        ds_obs = nc.open_data(obs_path, checks=False)

        _regrid_onto_common_grid(ds_model, ds_obs)

        # cropped to the model's small extent, not put on a coarse 0.5deg
        # grid - the obs stayed at its own (finer) native resolution
        obs_xr = ds_obs.to_xarray()
        lon_coord = [c for c in obs_xr.coords if "lon" in c][0]
        spacing = float(obs_xr[lon_coord][1] - obs_xr[lon_coord][0])
        assert abs(spacing - 0.25) < 1e-6

        # both datasets end up on the same grid, which the later merge step
        # requires
        assert ds_model.to_xarray().model.shape == obs_xr.observation.shape

    def test_a_global_model_uses_a_half_degree_common_grid(self, tmp_path):
        # a near-global model - large enough that even after cropping obs to
        # its extent, that extent alone still exceeds 90 degrees
        model_path = str(tmp_path / "model.nc")
        _write_grid(
            model_path, np.linspace(-180, 179, 90), np.linspace(-80, 80, 60), "model"
        )

        obs_path = str(tmp_path / "obs.nc")
        _write_grid(
            obs_path,
            np.arange(-179.875, 180, 0.25),
            np.arange(-89.875, 90, 0.25),
            "observation",
        )

        ds_model = nc.open_data(model_path, checks=False)
        ds_obs = nc.open_data(obs_path, checks=False)

        _regrid_onto_common_grid(ds_model, ds_obs)

        model_xr = ds_model.to_xarray()
        obs_xr = ds_obs.to_xarray()

        model_lon = [c for c in model_xr.coords if "lon" in c][0]
        obs_lon = [c for c in obs_xr.coords if "lon" in c][0]
        model_lat = [c for c in model_xr.coords if "lat" in c][0]
        obs_lat = [c for c in obs_xr.coords if "lat" in c][0]

        # both regridded to a common 0.5 degree grid
        assert abs(float(model_xr[model_lon][1] - model_xr[model_lon][0]) - 0.5) < 1e-6
        assert abs(float(obs_xr[obs_lon][1] - obs_xr[obs_lon][0]) - 0.5) < 1e-6
        assert abs(float(model_xr[model_lat][1] - model_xr[model_lat][0]) - 0.5) < 1e-6
        assert abs(float(obs_xr[obs_lat][1] - obs_xr[obs_lat][0]) - 0.5) < 1e-6

        # and therefore end up with matching shapes, ready to merge
        assert model_xr.model.shape == obs_xr.observation.shape

    def test_a_wide_but_narrow_model_only_needs_one_dimension_over_90(self, tmp_path):
        # spans >90 degrees of longitude but a narrow band of latitude - the
        # rule is "either dimension", not "both"
        model_path = str(tmp_path / "model.nc")
        _write_grid(
            model_path, np.linspace(-150, 150, 60), np.linspace(48, 58, 10), "model"
        )

        obs_path = str(tmp_path / "obs.nc")
        _write_grid(
            obs_path,
            np.arange(-179.875, 180, 0.25),
            np.arange(-89.875, 90, 0.25),
            "observation",
        )

        ds_model = nc.open_data(model_path, checks=False)
        ds_obs = nc.open_data(obs_path, checks=False)

        _regrid_onto_common_grid(ds_model, ds_obs)

        obs_xr = ds_obs.to_xarray()
        obs_lon = [c for c in obs_xr.coords if "lon" in c][0]
        assert abs(float(obs_xr[obs_lon][1] - obs_xr[obs_lon][0]) - 0.5) < 1e-6
