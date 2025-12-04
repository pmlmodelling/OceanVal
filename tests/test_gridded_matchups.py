
import oceanval
import nctoolkit as nc
import pickle

import numpy as np
import pandas as pd
import glob
import os
import shutil


class TestFinal:

    def test_gridded(self):

        oceanval.definitions.reset()
        # raise ValueError(oceanval.definitions.keys)

        oceanval.add_gridded_comparison(
            name = "temperature",
            obs_path="data/evaldata/gridded/nws/temperature",
            source = "foo",
            model_variable = "votemper",
            obs_variable = "votemper",
            climatology = True,
            start = 2000, 
            end = 2010
        )
        # raise ValueError(oceanval.definitions["temperature"])

        oceanval.matchup(
            sim_dir = "data/example",
            start = 2000,
            end = 2000,
            ask = False,
            cores = 1)
        
        assert os.path.exists("oceanval_matchups/gridded/temperature/foo_temperature_surface.nc")
        assert os.path.exists("oceanval_matchups/gridded/temperature/foo_temperature_surface_definitions.pkl")
        assert os.path.exists("oceanval_matchups/gridded/temperature/matchup_dict.pkl")
        assert os.path.exists("oceanval_matchups/gridded/temperature/temperature_summary.pkl")
        assert os.path.exists("oceanval_matchups/mapping.csv")
        assert os.path.exists("oceanval_matchups/short_titles.pkl")
        assert os.path.exists("oceanval_matchups/times_dict.pkl")
        assert os.path.exists("oceanval_matchups/variables_matched.pkl")

        ff = "oceanval_matchups/gridded/temperature/matchup_dict.pkl"
        with open(ff, 'rb') as f:
            matchup_dict = pickle.load(f)
            start = matchup_dict['start']
            end = matchup_dict['end']
            assert start == 2000
            assert end == 2000
        
        ds = nc.open_data("oceanval_matchups/gridded/temperature/foo_temperature_surface.nc")
        df = ds.to_dataframe().assign(diff = lambda x: x.model - x.observation)
        # get absolute max difference
        max_diff = np.abs(df['diff']).max()
        assert max_diff < 1e-5
#        shutil.rmtree("oceanval_matchups/gridded/temperature", ignore_errors=True)
        shutil.rmtree("oceanval_matchups", ignore_errors=True)

        oceanval.reset()

        oceanval.add_gridded_comparison(
            name = "temperature",
            obs_path="data/evaldata/gridded/nws/temperature",
            source = "foo",
            model_variable = "votemper",
            obs_variable = "votemper",
            climatology = True,
            start = 2000, 
            end = 2010
        )

        oceanval.matchup(
            sim_dir = "data/example",
            start = 2000,
            end = 2001,
            ask = False,
            cores = 1)
        
        assert os.path.exists("oceanval_matchups/gridded/temperature/foo_temperature_surface.nc")
        assert os.path.exists("oceanval_matchups/gridded/temperature/foo_temperature_surface_definitions.pkl")
        assert os.path.exists("oceanval_matchups/gridded/temperature/matchup_dict.pkl")
        assert os.path.exists("oceanval_matchups/gridded/temperature/temperature_summary.pkl")
        assert os.path.exists("oceanval_matchups/mapping.csv")
        assert os.path.exists("oceanval_matchups/short_titles.pkl")
        assert os.path.exists("oceanval_matchups/times_dict.pkl")
        assert os.path.exists("oceanval_matchups/variables_matched.pkl")
        
        ds = nc.open_data("oceanval_matchups/gridded/temperature/foo_temperature_surface.nc")
        df = ds.to_dataframe().assign(diff = lambda x: x.model - x.observation)
        # get absolute max difference
        max_diff = np.abs(df['diff']).max()
        assert max_diff == np.float32(1.0664015) 

        ff ="oceanval_matchups/gridded/temperature/matchup_dict.pkl"
        with open(ff, 'rb') as f:
            matchup_dict = pickle.load(f)
            start = matchup_dict['start']
            end = matchup_dict['end']
            assert start == 2000
            assert end == 2001
        
        # read in the definitions
        ff = "oceanval_matchups/gridded/temperature/foo_temperature_surface_definitions.pkl"
        with open(ff, 'rb') as f:
            definitions = pickle.load(f)
            model_variable = definitions["temperature"].model_variable
            obs_variable = definitions["temperature"].obs_variable
            start = definitions["temperature"].gridded_start
            end = definitions["temperature"].gridded_end
            obs_path = definitions["temperature"].gridded_dir
            climatology = definitions["temperature"].climatology
            short_name = definitions["temperature"].short_name
            long_name = definitions["temperature"].long_name
            short_title = definitions["temperature"].short_title
            source = definitions["temperature"].gridded_source
            point_source = definitions["temperature"].point_source
            point_dir = definitions["temperature"].point_dir
            point_start = definitions["temperature"].point_start
            point_end = definitions["temperature"].point_end
            vertical_point = definitions["temperature"].vertical_point
            binning = definitions["temperature"].binning
            n_levels = definitions["temperature"].n_levels
            recipe = definitions["temperature"].recipe
            thredds = definitions["temperature"].thredds

            assert model_variable == "votemper"
            assert obs_variable == "votemper"
            assert start == 2000
            assert end == 2001
            assert obs_path == "data/evaldata/gridded/nws/temperature"
            assert climatology is True
            assert short_name == "temperature"
            assert long_name == "temperature"
            assert short_title == "Temperature"
            assert source == "foo"
            assert point_source is None
            assert point_dir is None
            point_end = -1000
            point_start = 3000
            vertical_point = None
            binning = None
            n_levels = 51
            recipe = False
            thredds = False
    
        shutil.rmtree("oceanval_matchups", ignore_errors=True)
 
