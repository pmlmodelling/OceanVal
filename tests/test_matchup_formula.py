
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

        oceanval.add_gridded_comparison(
            name = "chlorophyll",
            obs_path="data/chl/model_as_obs",
            source = "foo",
            model_variable = "P1_Chl+P2_Chl+P3_Chl+P4_Chl",
            obs_variable = "total",
            climatology = False,
            start = 2000, 
            end = 2000
        )

        oceanval.add_point_comparison(
            name = "chlorophyll",
            obs_path="data/chl/obs_csv",
            source = "foo",
            model_variable = "P1_Chl+P2_Chl+P3_Chl+P4_Chl",
            start = 2000, 
            end = 2000
        )

        oceanval.matchup(
            "data/chl/simulation",
            start = 2000, 
            end = 2000, 
            n_dirs_down = 0,
            ask = False,
            cache = True,
            cores = 1
        )

        ff = "oceanval_matchups/gridded/chlorophyll/foo_chlorophyll_surface.nc"
        assert os.path.exists(ff)

        ds = nc.open_data(ff)
        df = ds.to_dataframe()
        # max diff
        diff = np.abs(df['model'] - df['observation'])
        max_diff = diff.max()
        assert max_diff < 1e-6

        ff = "oceanval_matchups/point/surface/chlorophyll/foo/foo_surface_chlorophyll.csv"
        df = pd.read_csv(ff)
        diff = np.abs(df['model'] - df['observation'])
        max_diff = diff.max()
        assert max_diff < 1e-6

        for ff in glob.glob(".cache_oceanval/output/*.pkl"):
            with open(ff, "rb") as f:
                df = pickle.load(f)   

                columns = ["lon", "lat", "year", "month", "day", "total"]
                for col in columns:
                    assert col in df.columns
                assert len(df) == 248
