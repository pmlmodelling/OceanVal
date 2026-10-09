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
            obs_path = "data/ukesm/1950/ukesm_subset_tos.nc",
            model_variable = "tos",
            obs_variable = "tos",
            source = "foo", 
            climatology = False
            )
        oceanval.matchup("data/ukesm",
            ask = False,
            n_dirs_down = 1,
            # one core, as nctoolkit's pools for more can hang
            cores = 1,
            start = 1950, end = 1950)

        # remembered for the oceanval window's list of simulations
        from oceanval import user_cache
        assert user_cache.recent_sim_dirs() == [os.path.abspath("data/ukesm")]

        import nctoolkit as nc
        ds = nc.open_data("oceanval_matchups/gridded/temperature/foo_temperature_surface.nc", checks = False)
        # max absolute diff between model and obs should be < 0.01
        # ensure only 12 times
        assert len(ds.times) == 12


    def test_a_simulation_is_only_remembered_once_the_matchups_are_confirmed(self, monkeypatch):
        from oceanval import prompts, user_cache

        oceanval.reset()
        oceanval.add_gridded_comparison(
            name = "temperature",
            obs_path = "data/ukesm/1950/ukesm_subset_tos.nc",
            model_variable = "tos",
            obs_variable = "tos",
            source = "foo",
            climatology = False
            )
        questions = []

        def refuse(question, *args, **kwargs):
            questions.append(question)
            return "n"

        monkeypatch.setattr(prompts, "ask", refuse)
        result = oceanval.matchup("data/ukesm", n_dirs_down = 1, cores = 1, start = 1950, end = 1950)

        assert result is None
        assert questions == ["Are you happy with these matchups? (y/n) "]
        assert user_cache.recent_sim_dirs() == []
