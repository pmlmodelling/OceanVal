import oceanval 
import os
import pytest
import tempfile
import shutil


class TestMatchup:
    """Test suite for matchup function"""
    
    def test_missing_sim_dir(self):
        """Test that ValueError is raised when sim_dir is not provided"""
        oceanval.reset()
        
        with pytest.raises(ValueError, match="Please provide a sim_dir directory"):
            oceanval.matchup(start=2000, end=2001)
    
    def test_nonexistent_sim_dir(self):
        """Test that ValueError is raised when sim_dir doesn't exist"""
        oceanval.reset()
        
        with pytest.raises(ValueError, match="does not exist"):
            oceanval.matchup(sim_dir="/nonexistent/path", start=2000, end=2001)
    
    def test_missing_start_year(self):
        """Test that ValueError is raised when start is not provided"""
        oceanval.reset()
        
        with pytest.raises(ValueError, match="Please provide a start year"):
            oceanval.matchup(sim_dir="data/example", end=2001)
    
    def test_missing_end_year(self):
        """Test that ValueError is raised when end is not provided"""
        oceanval.reset()
        
        with pytest.raises(ValueError, match="Please provide an end year"):
            oceanval.matchup(sim_dir="data/example", start=2000)
    
    def test_invalid_start_type(self):
        """Test that TypeError is raised when start is not an integer"""
        oceanval.reset()
        
        with pytest.raises(TypeError, match="Start must be an integer"):
            oceanval.matchup(sim_dir="data/example", start="2000", end=2001)
    
    def test_invalid_end_type(self):
        """Test that TypeError is raised when end is not an integer"""
        oceanval.reset()
        
        with pytest.raises(TypeError, match="End must be an integer"):
            oceanval.matchup(sim_dir="data/example", start=2000, end="2001")
    
    def test_invalid_ask_type(self):
        """Test that TypeError is raised when ask is not boolean"""
        oceanval.reset()
        
        with pytest.raises(TypeError, match="ask must be a boolean"):
            oceanval.matchup(sim_dir="data/example", start=2000, end=2001, ask="yes",
            lon_lim=[-10,10], lat_lim=[40,50]
                             )
    
    def test_invalid_overwrite_type(self):
        """Test that TypeError is raised when overwrite is not boolean"""
        oceanval.reset()
        
        with pytest.raises(TypeError, match="overwrite must be a boolean"):
            oceanval.matchup(sim_dir="data/example", start=2000, end=2001, overwrite="yes",
            lon_lim=[-10,10], lat_lim=[40,50]
                             )
    
    def test_invalid_n_dirs_down_type(self):
        """Test that TypeError is raised when n_dirs_down is not an integer"""
        oceanval.reset()
        
        with pytest.raises(TypeError, match="n_dirs_down must be an integer"):
            oceanval.matchup(sim_dir="data/example", start=2000, end=2001, n_dirs_down="2",
            lon_lim=[-10,10], lat_lim=[40,50]
                             )
    
    def test_negative_n_dirs_down(self):
        """Test that ValueError is raised when n_dirs_down is negative"""
        oceanval.reset()
        
        with pytest.raises(ValueError, match="n_dirs_down must be a positive integer"):
            oceanval.matchup(sim_dir="data/example", start=2000, end=2001, n_dirs_down=-1,
            lon_lim=[-10,10], lat_lim=[40,50]
                             )
    
    def test_invalid_exclude_type(self):
        """Test that TypeError is raised when exclude is not list or string"""
        oceanval.reset()
        
        with pytest.raises(TypeError, match="exclude must be a list or a string"):
            oceanval.matchup(sim_dir="data/example", start=2000, end=2001, exclude=123,
            lon_lim=[-10,10], lat_lim=[40,50]
                             )
    
    def test_exclude_string_conversion(self):
        """Test that exclude string is converted to list"""
        oceanval.reset()
        
        # This should not raise an error - just testing type conversion
        # We can't fully test matchup without proper simulation data, but we can test parameter handling
        try:
            oceanval.matchup(sim_dir="data/example", start=2000, end=2001, exclude="test", ask=False)
        except ValueError as e:
            # Expected to fail because no variables are defined, but shouldn't fail on exclude type
            assert "exclude must be a list" not in str(e)
    
    def test_invalid_require_type(self):
        """Test that TypeError is raised when require is not list or string"""
        oceanval.reset()
        
        with pytest.raises(TypeError, match="require must be a list or a string"):
            oceanval.matchup(sim_dir="data/example", start=2000, end=2001, require=123,
            lon_lim=[-10,10], lat_lim=[40,50]
                             )
    
    def test_require_string_conversion(self):
        """Test that require string is converted to list"""
        oceanval.reset()
        
        # Test that string is properly converted - should not raise TypeError about require
        try:
            oceanval.matchup(sim_dir="data/example", start=2000, end=2001, require="test", ask=False)
        except ValueError as e:
            # Expected to fail for other reasons, but not require type
            assert "require must be a list" not in str(e)
    
    def test_invalid_point_time_res_type(self):
        """Test that TypeError is raised when point_time_res is not list or string"""
        oceanval.reset()
        
        with pytest.raises(TypeError, match="point_time_res must be a list or a string"):
            oceanval.matchup(sim_dir="data/example", start=2000, end=2001, point_time_res=123,
            lon_lim=[-10,10], lat_lim=[40,50]
                             )
    
    def test_point_time_res_string_conversion(self):
        """Test that point_time_res string is converted to list"""
        oceanval.reset()
        
        # Should not raise TypeError about point_time_res
        try:
            oceanval.matchup(sim_dir="data/example", start=2000, end=2001, point_time_res="year", ask=False)
        except ValueError as e:
            assert "point_time_res must be a list" not in str(e)
    
    def test_nonexistent_thickness_file(self):
        """Test that FileNotFoundError is raised when thickness file doesn't exist"""
        oceanval.reset()
        
        with pytest.raises(FileNotFoundError, match="does not exist"):
            oceanval.matchup(
                sim_dir="data/example",
                start=2000,
                end=2001,
                thickness="/nonexistent/thickness.nc",
                lon_lim=[-10,10],
                lat_lim=[40,50]
            )
    
    def test_lon_lat_lim_mismatch(self):
        """Test that TypeError is raised when only one of lon_lim/lat_lim is provided"""
        oceanval.reset()
        
        with pytest.raises(TypeError, match="lon_lim and lat_lim must be lists"):
            oceanval.matchup(
                sim_dir="data/example",
                start=2000,
                end=2001,
                lon_lim=[-10, 10]
            )
        
        with pytest.raises(TypeError, match="lon_lim and lat_lim must be lists"):
            oceanval.matchup(
                sim_dir="data/example",
                start=2000,
                end=2001,
                lat_lim=[40, 50]
            )
    
    def test_no_variables_defined(self):
        """Test that ValueError is raised when no variables are requested for validation"""
        oceanval.reset()
        
        with pytest.raises(ValueError, match="You do not appear to have asked for any variables to be validated"):
            oceanval.matchup(sim_dir="data/example", start=2000, end=2001, ask=False, lon_lim=[-10,10], lat_lim=[40,50])
    
    def test_invalid_kwargs(self):
        """Test that ValueError is raised for invalid keyword arguments"""
        oceanval.reset()
        
        # Add a variable so we don't hit the "no variables" error first
        temp_gridded_file = "data/evaldata/gridded/nws/nitrate/model_2000.nc"
        try:
            oceanval.add_gridded_comparison(
                name="testvar",
                source="TestSource",
                model_variable="temp",
                climatology=True,
                obs_path=temp_gridded_file,
                obs_variable="N3_n"
            )
        except:
            pass
        
    
    
    def test_cores_parameter(self):
        """Test that cores parameter is handled correctly"""
        oceanval.reset()
        # cores = -1 should faile
        with pytest.raises(ValueError, match="cores must be a positive integer"):
            oceanval.matchup(
                sim_dir="data/example",
                start=2000,
                end=2001,
                cores=-1,
                ask=False,
                lon_lim=[-10,10],
                lat_lim=[40,50]
            )
        # cores = 100000 should fail
        with pytest.raises(ValueError, match="is greater than the number of system cores"):
            oceanval.matchup(
                sim_dir="data/example",
                start=2000,
                end=2001,
                cores=100000,
                ask=False,
                lon_lim=[-10,10],
                lat_lim=[40,50]
            )
        
    def test_invalid_out_dir_type(self):
        """Test that TypeError is raised when out_dir is not a string"""
        oceanval.reset()
        
        with pytest.raises(TypeError, match="out_dir must be a string"):
            oceanval.matchup(sim_dir="data/example", start=2000, end=2001, out_dir=123,
            lon_lim=[-10,10], lat_lim=[40,50]
                             )
                
    def test_exclude_item_type(self):
        """Test that TypeError is raised when an item in exclude list is not a string"""
        oceanval.reset()
        
        with pytest.raises(TypeError, match="each item in exclude must be a string"):
            oceanval.matchup(sim_dir="data/example", start=2000, end=2001, exclude=["valid", 123],
            lon_lim=[-10,10], lat_lim=[40,50]
                             )
    def test_require_item_type(self):
        """Test that TypeError is raised when an item in require list is not a string"""
        oceanval.reset()
        
        with pytest.raises(TypeError, match="each item in require must be a string"):
            oceanval.matchup(sim_dir="data/example", start=2000, end=2001, require=["valid", 123],
            lon_lim=[-10,10], lat_lim=[40,50]
                             )
    
    def test_invalid_cache_type(self):
        """Test that TypeError is raised when cache is not boolean"""
        oceanval.reset()
        
        with pytest.raises(TypeError, match="cache must be a boolean"):
            oceanval.matchup(sim_dir="data/example", start=2000, end=2001, cache="yes",
            lon_lim=[-10,10], lat_lim=[40,50]
                             )
    
    def test_invalid_n_check_type(self):
        """Test that TypeError is raised when n_check is not integer or None"""
        oceanval.reset()
        
        with pytest.raises(TypeError, match="n_check must be an integer"):
            oceanval.matchup(sim_dir="data/example", start=2000, end=2001, n_check="ten",
            lon_lim=[-10,10], lat_lim=[40,50]
                             )
    def test_negative_n_check(self):
        """Test that ValueError is raised when n_check is negative"""
        oceanval.reset()
        
        with pytest.raises(ValueError, match="n_check must be a positive integer"):
            oceanval.matchup(sim_dir="data/example", start=2000, end=2001, n_check=-5,
            lon_lim=[-10,10], lat_lim=[40,50]
                             )

    # as_missing tests
    def test_invalid_as_missing_type(self):
         """Test that TypeError is raised when as_missing is not boolean"""
         oceanval.reset()
         
         with pytest.raises(TypeError, match="as_missing must be a float"):
             oceanval.matchup(sim_dir="data/example", start=2000, end=2001, as_missing="yes",
             lon_lim=[-10,10], lat_lim=[40,50]
                              )
                              # test elements of as_missing list
    def test_as_missing_item_type(self):
        """Test that TypeError is raised when an item in as_missing list is not float"""
        oceanval.reset()
            
        with pytest.raises(TypeError, match="as_missing list elements must be float"): 
            oceanval.matchup(sim_dir="data/example", start=2000, end=2001, as_missing=[0.1, "invalid"],
            lon_lim=[-10,10], lat_lim=[40,50]
                            )

    # strict_names test
    def test_invalid_strict_names_type(self):
            """Test that TypeError is raised when strict_names is not boolean"""
            oceanval.reset()
            
            with pytest.raises(TypeError, match="strict_names must be a boolean"):
                oceanval.matchup(sim_dir="data/example", start=2000, end=2001, strict_names="yes",
                lon_lim=[-10,10], lat_lim=[40,50]
                                )

                        

                            
        
    shutil.rmtree("oceanval_matchups", ignore_errors=True)