import oceanval 
import os
import pytest
import tempfile
import shutil
import glob


class TestValidate:
    """Test suite for validate function"""

    def test_invalid_region(self):
        """Test that ValueError is raised for invalid subregions"""
        with pytest.raises(ValueError, match="subregions must be 'nwes', 'global' or a path to a .nc file"):
            oceanval.validate(subregions="invalid_region", test=True)

    def test_valid_regions(self):
        """Test that supported regions pass validation."""
        for region in ["nwes", "global"]:
            with pytest.raises(ValueError) as error:
                oceanval.validate(subregions=region, lon_lim="not_a_list", test=True)
            assert "subregions must be" not in str(error.value)

    def test_region_deprecated(self):
        """Test that region still works, with a FutureWarning"""
        with pytest.warns(FutureWarning, match="region is deprecated, use subregions instead"):
            with pytest.raises(ValueError, match="subregions must be"):
                oceanval.validate(region="invalid_region", test=True)
    
    def test_lon_lim_not_list(self):
        """Test that ValueError is raised when lon_lim is not a list"""
        with pytest.raises(ValueError, match="lon_lim must be a list"):
            oceanval.validate(lon_lim="not_a_list", test=True)
    
    def test_lon_lim_wrong_length(self):
        """Test that ValueError is raised when lon_lim doesn't have length 2"""
        with pytest.raises(ValueError, match="lon_lim must be a list of length 2"):
            oceanval.validate(lon_lim=[-10], test=True)
        
        with pytest.raises(ValueError, match="lon_lim must be a list of length 2"):
            oceanval.validate(lon_lim=[-10, 0, 10], test=True)
    
    def test_lat_lim_not_list(self):
        """Test that ValueError is raised when lat_lim is not a list"""
        with pytest.raises(ValueError, match="lat_lim must be a list"):
            oceanval.validate(lat_lim="not_a_list", test=True)
    
    def test_lat_lim_wrong_length(self):
        """Test that ValueError is raised when lat_lim doesn't have length 2"""
        with pytest.raises(ValueError, match="lat_lim must be a list of length 2"):
            oceanval.validate(lat_lim=[40], test=True)
        
        with pytest.raises(ValueError, match="lat_lim must be a list of length 2"):
            oceanval.validate(lat_lim=[40, 50, 60], test=True)
    
    # concise must be bool

    def test_concise_not_bool(self):
        """Test that ValueError is raised when concise is not a boolean"""
        with pytest.raises(ValueError, match="concise must be a boolean"):
            oceanval.validate(concise="not_a_bool", test=True)
    
    def test_valid_lon_lat_lim(self):
        """Test that valid lon_lim and lat_lim are accepted"""
        # Should not raise errors about lon_lim or lat_lim validation
        try:
            oceanval.validate(
                lon_lim=[-10, 10],
                lat_lim=[40, 50],
                fixed_scale = "foobar"
            )
        except ValueError as e:
            # Should not fail on lon_lim or lat_lim validation
            assert "lon_lim must be a list" not in str(e)
            assert "lat_lim must be a list" not in str(e)

    
    def test_lon_lim_none_accepted(self):
        """Test that None is accepted for lon_lim"""
        # Should not raise error about lon_lim
        try:
            oceanval.validate(lon_lim=None, concise = "foo_bar")
        except ValueError as e:
            assert "lon_lim" not in str(e)
    
    def test_lat_lim_none_accepted(self):
        """Test that None is accepted for lat_lim"""
        # Should not raise error about lat_lim
        try:
            oceanval.validate(lat_lim=None, concise = "foo_bar") 
        except ValueError as e:
            assert "lat_lim" not in str(e)
    
    



def _write_region_file(path, values):
    """Write a small regions netCDF with a single region variable."""
    import numpy as np
    import xarray as xr
    ds = xr.Dataset(
        {"box": (("lat", "lon"), np.array(values, dtype="float32"))},
        coords={"lat": [50.0, 51.0], "lon": [0.0, 1.0]},
    )
    ds.box.attrs["long_name"] = "Box"
    ds.to_netcdf(path)
    return str(path)


class TestRegionFile:
    """Test suite for passing a regions file to validate via subregions"""

    def test_region_and_subregions(self, tmp_path):
        """Test that ValueError is raised when region and subregions are both given"""
        ff = _write_region_file(tmp_path / "regions.nc", [[1, 1], [1, 1]])
        with pytest.raises(ValueError, match="give subregions or region, not both"):
            oceanval.validate(region="nwes", subregions=ff, test=True)

    def test_region_file_not_nc(self, tmp_path):
        """Test that ValueError is raised when subregions is a path that is not a .nc file"""
        with pytest.raises(ValueError, match="subregions must be 'nwes', 'global' or a path to a .nc file"):
            oceanval.validate(subregions=str(tmp_path / "regions.txt"), test=True)

    def test_region_file_missing(self, tmp_path):
        """Test that ValueError is raised when the regions file does not exist"""
        with pytest.raises(ValueError, match="does not exist"):
            oceanval.validate(subregions=str(tmp_path / "missing.nc"), test=True)

    def test_region_file_bad_values(self, tmp_path):
        """Test that ValueError is raised when the regions file has values other than 1, 0 or missing"""
        ff = _write_region_file(tmp_path / "regions.nc", [[1, 2], [0, float("nan")]])
        with pytest.raises(ValueError, match="box must only contain 1, 0 or missing values"):
            oceanval.validate(subregions=ff, test=True)

    def test_region_file_valid(self, tmp_path):
        """Test that a regions file with 1, 0 and missing values is accepted"""
        ff = _write_region_file(tmp_path / "regions.nc", [[1, 0], [1, float("nan")]])
        assert oceanval._check_region_file(ff) == 1
