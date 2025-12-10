import oceanval 
import os
import pytest
import tempfile
import shutil


class TestMatchup:
    """Test suite for matchup function"""
    
    def test_a_short_one(self):
        """Test that a simulation with less than 1 Year of data works"""
        oceanval.reset()
        oceanval.add_gridded_comparison(
            name = "temperature",
            obs_path = "data/ukesm/ukesm_subset_tos.nc",
            model_variable = "tos",
            obs_variable = "tos",
            source = "foo", 
            climatology = False
            )
        oceanval.matchup("data/ukesm",
            ask = False,
            n_dirs_down = 1,
            start = 1950, end = 1950)

        import nctoolkit as nc
        ds = nc.open_data("oceanval_matchups/gridded/temperature/foo_temperature_surface.nc", checks = False)
        # max absolute diff between model and obs should be < 0.01
        # ensure only 12 times
        assert len(ds.times) == 12
