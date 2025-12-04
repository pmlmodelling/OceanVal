import oceanval 
import os
import pytest
import tempfile
import shutil
import pandas as pd
import nctoolkit as nc
import numpy as np



class TestDefintions:
    """Test suite for oceanval definitions object"""
    
    def test_reset_definitions(self):
        """Test that reset method clears definitions"""
        temp_gridded_file = "data/evaldata/gridded/nws/nitrate/model_2000.nc"
        oceanval.add_gridded_comparison(
            name="testvar",
            source="TestSource",
            model_variable="temp",
            climatology=True,
            obs_path=temp_gridded_file,
            obs_variable="N3_n"
        )
        assert "testvar" in oceanval.definitions.keys
        
        oceanval.reset()

        assert "testvar" not in oceanval.definitions.keys


    def test_delete_definitions_key(self):
        """Test that reset method clears definitions"""
        temp_gridded_file = "data/evaldata/gridded/nws/nitrate/model_2000.nc"
        oceanval.add_gridded_comparison(
            name="testvar",
            source="TestSource",
            model_variable="temp",
            climatology=True,
            obs_path=temp_gridded_file,
            obs_variable="N3_n"
        )
        assert "testvar" in oceanval.definitions.keys
        
        del oceanval.definitions.testvar

        assert "testvar" not in oceanval.definitions.keys
    
    # test the remove option

    def test_remove_definitions_key(self):
        """Test that reset method clears definitions"""
        temp_gridded_file = "data/evaldata/gridded/nws/nitrate/model_2000.nc"
        oceanval.add_gridded_comparison(
            name="testvar",
            source="TestSource",
            model_variable="temp",
            climatology=True,
            obs_path=temp_gridded_file,
            obs_variable="N3_n"
        )
        assert "testvar" in oceanval.definitions.keys
        
        oceanval.definitions.remove("testvar")

        assert "testvar" not in oceanval.definitions.keys

class TestRecipeInAdder:
    """Test that recipe can be used in adders"""
    
    def test_add_point_comparison_with_recipe(self):
        """Test adding point comparison using a recipe"""

        # add the {"temperature": "cobe2"} recipe
        oceanval.add_gridded_comparison(
            recipe = {"temperature": "cobe2"},
            model_variable="temp",
            file_check= False
        )
        # Verify the variable was added
        assert hasattr(oceanval.definitions, "temperature")
        assert oceanval.definitions["temperature"].model_variable == "temp"
        assert oceanval.definitions["temperature"].gridded_source == "COBE2"
        assert oceanval.definitions["temperature"].obs_variable == "sst"
        assert oceanval.definitions["temperature"].thredds == True
    
    # ensure all recipes have obs_variable
    def test_all_recipes_have_obs_variable(self):
        """Test that all recipes have obs_variable defined"""
        recipe_list = oceanval.parsers.recipe_list
        for recipe in recipe_list:
            recipe_info = oceanval.parsers.find_recipe(recipe, start = 2000, end = 2000)
            assert "obs_variable" in recipe_info
            assert recipe_info["obs_variable"] is not None



class TestAddPointComparison:
    """Test suite for add_point_comparison method"""
    
    @pytest.fixture
    def temp_point_dir(self):
        """Create a temporary directory with valid point observation CSV files"""
        temp_dir = tempfile.mkdtemp()
        
        # Create a valid CSV file with required columns
        df = pd.DataFrame({
            'lon': [10.0, 11.0, 12.0],
            'lat': [50.0, 51.0, 52.0],
            'observation': [15.5, 16.2, 14.8],
            'year': [2020, 2020, 2020],
            'month': [1, 1, 1],
            'day': [1, 2, 3]
        })
        df.to_csv(os.path.join(temp_dir, 'obs1.csv'), index=False)
        
        # Create another CSV with depth column for vertical validation
        df_depth = pd.DataFrame({
            'lon': [10.0, 11.0],
            'lat': [50.0, 51.0],
            'depth': [0.0, 10.0],
            'observation': [15.5, 16.2],
            'year': [2020, 2020],
            'month': [1, 1],
            'day': [1, 2]
        })
        df_depth.to_csv(os.path.join(temp_dir, 'obs2.csv'), index=False)
        
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_missing_name(self):
        """Test that ValueError is raised when name is not provided"""
        with pytest.raises(ValueError, match="Name must be supplied"):
            oceanval.add_point_comparison()
    
    def test_invalid_name_characters(self):
        """Test that ValueError is raised for names with invalid characters"""
        with pytest.raises(ValueError, match="Name can only contain letters and numbers"):
            oceanval.add_point_comparison(name="test-variable", source="TestSource")
        
        with pytest.raises(ValueError, match="Name can only contain letters and numbers"):
            oceanval.add_point_comparison(name="test_variable", source="TestSource")
        
        with pytest.raises(ValueError, match="Name can only contain letters and numbers"):
            oceanval.add_point_comparison(name="test variable", source="TestSource")
    
    def test_missing_source(self):
        """Test that ValueError is raised when source is not provided"""
        with pytest.raises(ValueError, match="Source must be supplied"):
            oceanval.add_point_comparison(name="testvar")
    
    def test_source_with_underscore(self):
        """Test that ValueError is raised when source contains underscore"""
        with pytest.raises(ValueError, match="Source key cannot contain '_'"):
            oceanval.add_point_comparison(name="testvar", source="test_source")
    
    def test_invalid_obs_multiplier(self):
        """Test that ValueError is raised for non-numeric obs_multiplier"""
        with pytest.raises(ValueError, match="obs_multiplier must be a number"):
            oceanval.add_point_comparison(
                name="testvar",
                source="TestSource",
                obs_multiplier="not_a_number"
            )
    
    def test_invalid_obs_adder(self):
        """Test that ValueError is raised for non-numeric obs_adder"""
        with pytest.raises(ValueError, match="obs_adder must be a number"):
            oceanval.add_point_comparison(
                name="testvar",
                source="TestSource",
                obs_adder="not_a_number"
            )
    
    def test_invalid_vertical_type(self):
        """Test that ValueError is raised when vertical is not boolean"""
        with pytest.raises(ValueError, match="vertical must be a boolean value"):
            oceanval.add_point_comparison(
                name="testvar",
                source="TestSource",
                vertical="yes"
            )
    
    def test_invalid_start_end(self):
        """Test that ValueError is raised when start/end cannot be cast to int"""
        with pytest.raises(ValueError, match="start and end must be integers"):
            oceanval.add_point_comparison(
                name="testvar",
                source="TestSource",
                start="not_an_int"
            )
        
        with pytest.raises(ValueError, match="start and end must be integers"):
            oceanval.add_point_comparison(
                name="testvar",
                source="TestSource",
                end="not_an_int"
            )
    
    def test_no_csv_files_in_directory(self, temp_point_dir):
        """Test that ValueError is raised when no CSV files exist in obs_path"""
        empty_dir = tempfile.mkdtemp()
        try:
            with pytest.raises(ValueError, match="No csv files found in point directory"):
                oceanval.add_point_comparison(
                    name="testvar",
                    source="TestSource",
                    obs_path=empty_dir
                )
        finally:
            shutil.rmtree(empty_dir)
    
    def test_invalid_columns_in_csv(self, temp_point_dir):
        """Test that ValueError is raised for invalid columns in CSV"""
        # Create a CSV with invalid column
        df_invalid = pd.DataFrame({
            'lon': [10.0],
            'lat': [50.0],
            'observation': [15.5],
            'invalid_col': ['bad']
        })
        df_invalid.to_csv(os.path.join(temp_point_dir, 'invalid.csv'), index=False)
        
        with pytest.raises(ValueError, match="Invalid columns"):
            oceanval.add_point_comparison(
                name="testvar",
                source="TestSource",
                obs_path=temp_point_dir
            )
    
    def test_missing_required_columns(self, temp_point_dir):
        """Test that ValueError is raised when required columns are missing"""
        # Create a CSV without observation column
        df_missing = pd.DataFrame({
            'lon': [10.0],
            'lat': [50.0]
        })
        df_missing.to_csv(os.path.join(temp_point_dir, 'missing.csv'), index=False)
        
        with pytest.raises(ValueError, match="Required column observation not found"):
            oceanval.add_point_comparison(
                name="testvar2",
                source="TestSource",
                obs_path=temp_point_dir
            )
    
    def test_vertical_without_depth(self, temp_point_dir):
        """Test that ValueError is raised when vertical=True but no depth column"""
        # Create directory with only non-depth files
        temp_dir_no_depth = tempfile.mkdtemp()
        try:
            df = pd.DataFrame({
                'lon': [10.0],
                'lat': [50.0],
                'observation': [15.5]
            })
            df.to_csv(os.path.join(temp_dir_no_depth, 'obs.csv'), index=False)
            
            with pytest.raises(ValueError, match="vertical is set to True but no depth column found"):
                oceanval.add_point_comparison(
                    name="testvar",
                    source="TestSource",
                    obs_path=temp_dir_no_depth,
                    vertical=True
                )
        finally:
            shutil.rmtree(temp_dir_no_depth)
    
    def test_invalid_binning_format(self, temp_point_dir):
        """Test that ValueError is raised for invalid binning format"""
        with pytest.raises(ValueError, match="binning must be a list of two values"):
            oceanval.add_point_comparison(
                name="testvar",
                source="TestSource",
                obs_path=temp_point_dir,
                binning=[1.0]  # Only one value
            )
        
        with pytest.raises(ValueError, match="binning must be a list of two values"):
            oceanval.add_point_comparison(
                name="testvar",
                source="TestSource",
                obs_path=temp_point_dir,
                binning="not_a_list"
            )
    
    def test_invalid_binning_values(self, temp_point_dir):
        """Test that ValueError is raised when binning values are not numeric"""
        with pytest.raises(ValueError, match="Each element of binning must be a number"):
            oceanval.add_point_comparison(
                name="testvar",
                source="TestSource",
                obs_path=temp_point_dir,
                binning=["not_a_number", 1.0]
            )
    
    def test_nonexistent_directory(self):
        """Test that ValueError is raised when obs_path doesn't exist"""
        with pytest.raises(ValueError, match="Observation path .* does not exist"):
            oceanval.add_point_comparison(
                name="testvar",
                source="TestSource",
                obs_path="/nonexistent/path"
            )
    
    def test_successful_addition_basic(self, temp_point_dir):
        """Test successful addition with minimal required parameters"""
        oceanval.reset()
        oceanval.add_point_comparison(
            name="temperature",
            source="TestSource",
            model_variable="temp",
            obs_path=temp_point_dir
        )
        
        # Verify the variable was added
        assert hasattr(oceanval.definitions, "temperature")
        assert oceanval.definitions["temperature"].model_variable == "temp"
        assert oceanval.definitions["temperature"].point_source == "TestSource"
        assert oceanval.definitions["temperature"].point_dir == temp_point_dir
        assert oceanval.definitions["temperature"].obs_multiplier_point == 1
        assert oceanval.definitions["temperature"].obs_adder_point == 0
        assert oceanval.definitions["temperature"].vertical_point == False
    
    def test_successful_addition_with_all_params(self, temp_point_dir):
        """Test successful addition with all parameters specified"""
        oceanval.reset()
        oceanval.add_point_comparison(
            name="salinity",
            long_name="sea water salinity",
            vertical=True,
            short_name="salinity",
            short_title="Salinity",
            source="TestSource",
            source_info="Test source information",
            model_variable="sal",
            start=-500,
            end=2000,
            obs_path=temp_point_dir,
            obs_multiplier=1.5,
            obs_adder=0.5,
            binning=[1.0, 10.0]
        )
        
        # Verify all attributes
        assert oceanval.definitions["salinity"].long_name == "sea water salinity"
        assert oceanval.definitions["salinity"].short_name == "salinity"
        assert oceanval.definitions["salinity"].short_title == "Salinity"
        assert oceanval.definitions["salinity"].vertical_point == True
        assert oceanval.definitions["salinity"].point_start == -500
        assert oceanval.definitions["salinity"].point_end == 2000
        assert oceanval.definitions["salinity"].obs_multiplier_point == 1.5
        assert oceanval.definitions["salinity"].obs_adder_point == 0.5
        assert oceanval.definitions["salinity"].binning == [1.0, 10.0]
    
    def test_numeric_conversion_for_start_end(self, temp_point_dir):
        """Test that start and end are properly converted to integers"""
        oceanval.reset()
        oceanval.add_point_comparison(
            name="oxygen",
            source="TestSource",
            model_variable="o2",
            obs_path=temp_point_dir,
            start="0",
            end="100"
        )
        
        assert oceanval.definitions["oxygen"].point_start == 0
        assert oceanval.definitions["oxygen"].point_end == 100
    
    def test_assumed_attributes_warning(self, temp_point_dir, capsys):
        """Test that warnings are printed for assumed attributes"""
        oceanval.reset()
        oceanval.add_point_comparison(
            name="chlorophyll",
            source="TestSource",
            model_variable="chl",
            obs_path=temp_point_dir
        )
        
        captured = capsys.readouterr()
        # Should print warnings for assumed attributes
        assert "Warning" in captured.out


class TestAddGriddedComparison:
    """Test suite for add_gridded_comparison method"""
    
    @pytest.fixture
    def temp_gridded_file(self):
        """Create a temporary NetCDF file for gridded observations"""
        temp_dir = tempfile.mkdtemp()
        nc_file = os.path.join(temp_dir, 'obs_gridded.nc')
        
        # Create a simple NetCDF file with nctoolkit
        ds = nc.open_data(nc_file, checks=False)
        # Create dummy data
        import xarray as xr
        data = xr.Dataset({
            'sst': (['time', 'lat', 'lon'], np.random.rand(12, 10, 10))
        }, coords={
            'time': pd.date_range('2020-01-01', periods=12, freq='MS'),
            'lat': np.linspace(-90, 90, 10),
            'lon': np.linspace(-180, 180, 10)
        })
        data.to_netcdf(nc_file)
        
        yield nc_file
        shutil.rmtree(temp_dir)
    
    def test_missing_name(self):
        """Test that ValueError is raised when name is not provided"""
        with pytest.raises(ValueError, match="Name must be supplied"):
            oceanval.add_gridded_comparison()
    
    def test_invalid_name_characters(self):
        """Test that ValueError is raised for names with invalid characters"""
        with pytest.raises(ValueError, match="Name can only contain letters and numbers"):
            oceanval.add_gridded_comparison(name="test-variable", source="TestSource")
        
        with pytest.raises(ValueError, match="Name can only contain letters and numbers"):
            oceanval.add_gridded_comparison(name="test_variable", source="TestSource")
    
    def test_missing_source(self):
        """Test that ValueError is raised when source is not provided"""
        with pytest.raises(ValueError, match="Source must be supplied"):
            oceanval.add_gridded_comparison(name="testvar")
    
    def test_missing_model_variable(self):
        """Test that ValueError is raised when model_variable is not provided"""
        with pytest.raises(ValueError, match="Model variable must be supplied"):
            oceanval.add_gridded_comparison(name="testvar", source="TestSource")
    
    def test_missing_climatology(self):
        """Test that ValueError is raised when climatology is not provided"""
        with pytest.raises(ValueError, match="Climatology must be provided"):
            oceanval.add_gridded_comparison(
                name="testvar",
                source="TestSource",
                model_variable="temp"
            )
    
    def test_missing_obs_path(self):
        """Test that ValueError is raised when obs_path is not provided"""
        with pytest.raises(ValueError, match="obs_path must be provided"):
            oceanval.add_gridded_comparison(
                name="testvar",
                source="TestSource",
                model_variable="temp",
                climatology=True
            )
    
    def test_invalid_climatology_type(self):
        """Test that ValueError is raised when climatology is not boolean"""
        with pytest.raises(ValueError, match="Climatology must be a boolean value"):
            oceanval.add_gridded_comparison(
                name="testvar",
                source="TestSource",
                model_variable="temp",
                climatology="yes",
                obs_path="/some/path"
            )
    
    def test_invalid_obs_multiplier(self):
        """Test that ValueError is raised for non-numeric obs_multiplier"""
        with pytest.raises(ValueError, match="obs_multiplier must be a number"):
            oceanval.add_gridded_comparison(
                name="testvar",
                source="TestSource",
                model_variable="temp",
                climatology=True,
                obs_path="/some/path",
                obs_multiplier="not_a_number"
            )
    
    def test_invalid_obs_adder(self):
        """Test that ValueError is raised for non-numeric obs_adder"""
        with pytest.raises(ValueError, match="obs_adder must be a number"):
            oceanval.add_gridded_comparison(
                name="testvar",
                source="TestSource",
                model_variable="temp",
                climatology=True,
                obs_path="/some/path",
                obs_adder="not_a_number"
            )
    
    def test_source_with_underscore(self):
        """Test that ValueError is raised when source contains underscore"""
        with pytest.raises(ValueError, match="Source cannot contain '_'"):
            oceanval.add_gridded_comparison(
                name="testvar",
                source="test_source",
                model_variable="temp",
                climatology=True,
                obs_variable = "foobar",
                obs_path="/some/path"
            )
    
    def test_missing_obs_variable(self):
        """Test that ValueError is raised when obs_variable is not a string"""
        # create temp_gridded_file
        temp_gridded_file = "data/evaldata/gridded/nws/nitrate/model_2000.nc"
        # temp_gridded_file = "../data/evaldata/gridded/nws/nitrate/model_2000.nc"
        assert os.path.exists(temp_gridded_file)
        with pytest.raises(ValueError, match="obs_variable be provided"):
            oceanval.add_gridded_comparison(
                name="testvar",
                source="TestSource",
                model_variable="temp",
                climatology=True,
                obs_path=temp_gridded_file,
                obs_variable=None
            )
    
    def test_nonexistent_directory(self):
        """Test that ValueError is raised when gridded directory doesn't exist"""
        with pytest.raises(ValueError, match="Gridded directory .* does not exist"):
            oceanval.add_gridded_comparison(
                name="testvar",
                source="TestSource",
                model_variable="temp",
                climatology=True,
                obs_path="/nonexistent/path",
                obs_variable="sst"
            )
    
    def test_invalid_thredds_type(self):
        """Test that ValueError is raised when thredds is not boolean"""
        temp_gridded_file = "data/evaldata/gridded/nws/nitrate/model_2000.nc"
        assert os.path.exists(temp_gridded_file)
        with pytest.raises(ValueError, match="thredds must be a boolean value"):
            oceanval.add_gridded_comparison(
                name="testvar",
                source="TestSource",
                model_variable="temp",
                climatology=True,
                obs_path=temp_gridded_file,
                obs_variable="sst",
                thredds="yes"
            )
    
    def test_obs_variable_not_in_file(self):
        """Test that ValueError is raised when obs_variable not in NetCDF file"""
        temp_gridded_file = "data/evaldata/gridded/nws/nitrate/model_2000.nc"
        with pytest.raises(ValueError, match="obs_variable .* not found in observation data files"):
            oceanval.add_gridded_comparison(
                name="testvar",
                source="TestSource",
                model_variable="temp",
                climatology=True,
                obs_path=temp_gridded_file,
                obs_variable="nonexistent_var"
            )
    
    def test_successful_addition_basic(self):
        """Test successful addition with minimal required parameters"""
        temp_gridded_file = "data/evaldata/gridded/nws/nitrate/model_2000.nc"
        oceanval.reset()
        oceanval.add_gridded_comparison(
            name="temperature",
            source="TestSource",
            model_variable="temp",
            climatology=True,
            obs_path=temp_gridded_file,
            obs_variable="N3_n"
        )
        
        # Verify the variable was added
        assert hasattr(oceanval.definitions, "temperature")
        assert oceanval.definitions["temperature"].model_variable == "temp"
        assert oceanval.definitions["temperature"].gridded_source == "TestSource"
        assert oceanval.definitions["temperature"].gridded_dir == temp_gridded_file
        assert oceanval.definitions["temperature"].climatology == True
        assert oceanval.definitions["temperature"].obs_variable == "N3_n"
        assert oceanval.definitions["temperature"].obs_multiplier_gridded == 1
        assert oceanval.definitions["temperature"].obs_adder_gridded == 0
        assert oceanval.definitions["temperature"].thredds == False
    
    def test_successful_addition_with_all_params(self):
        temp_gridded_file = "data/evaldata/gridded/nws/nitrate/model_2000.nc"
        """Test successful addition with all parameters specified"""
        oceanval.reset()
        oceanval.add_gridded_comparison(
            name="salinity",
            long_name="sea water salinity",
            short_name="salinity",
            short_title="Salinity",
            source="TestSource",
            source_info="Test source information",
            model_variable="sal",
            obs_path=temp_gridded_file,
            obs_variable="N3_n",
            start=-500,
            end=2000,
            vertical=True,
            climatology=False,
            obs_multiplier=1.5,
            obs_adder=0.5,
            thredds=False
        )
        
        # Verify all attributes
        assert oceanval.definitions["salinity"].long_name == "sea water salinity"
        assert oceanval.definitions["salinity"].short_name == "salinity"
        assert oceanval.definitions["salinity"].short_title == "Salinity"
        assert oceanval.definitions["salinity"].vertical_gridded == True
        assert oceanval.definitions["salinity"].gridded_start == -500
        assert oceanval.definitions["salinity"].gridded_end == 2000
        assert oceanval.definitions["salinity"].obs_multiplier_gridded == 1.5
        assert oceanval.definitions["salinity"].obs_adder_gridded == 0.5
        assert oceanval.definitions["salinity"].climatology == False
        assert oceanval.definitions["salinity"].thredds == False
    


class TestFindRecipe:
    """Test suite for find_recipe function"""
    
    def test_multiple_keys_error(self):
        """Test that ValueError is raised when recipe has multiple keys"""
        from oceanval.parsers import find_recipe
        
        with pytest.raises(ValueError, match="Recipe dictionary must have exactly one key"):
            find_recipe({"chlorophyll": "occci", "temperature": "woa23"})
    
    def test_multiple_values_error(self):
        """Test that ValueError is raised when recipe has multiple values"""
        from oceanval.parsers import find_recipe
        
        # This is a bit tricky - dict can't have duplicate keys, but test the logic
        # The function checks len(x.values()) != 1, but this is always 1 for valid dicts
        # Still, we should test the validation exists
        with pytest.raises(ValueError, match="Recipe dictionary must have exactly one"):
            find_recipe({})
    
    def test_invalid_recipe_value(self):
        """Test that ValueError is raised for invalid recipe value"""
        from oceanval.parsers import find_recipe
        
        with pytest.raises(ValueError, match="Recipe value .* is not valid"):
            find_recipe({"temperature": "invalid_source"})
    
    def test_chlorophyll_metadata(self):
        """Test that chlorophyll gets correct metadata"""
        from oceanval.parsers import find_recipe
        
        result = find_recipe({"chlorophyll": "occci"})
        
        assert result["short_name"] == "chlorophyll concentration"
        assert result["long_name"] == "chlorophyll a concentration"
        assert result["short_title"] == "Chlorophyll"
        assert result["name"] == "chlorophyll"
        assert result["obs_variable"] == "chlor_a"
        assert result["thredds"] == True
        assert result["climatology"] == False
        assert result["source"] == "OCCCI"
        assert "OC-CCI" in result["source_info"]
        assert isinstance(result["obs_path"], list)
        assert len(result["obs_path"]) > 0
    
    def test_oxygen_metadata(self):
        """Test that oxygen gets correct metadata"""
        from oceanval.parsers import find_recipe
        
        result = find_recipe({"oxygen": "woa23"})
        
        assert result["short_name"] == "dissolved oxygen"
        assert result["long_name"] == "dissolved oxygen concentration"
        assert result["short_title"] == "Oxygen"
        assert result["name"] == "oxygen"
        assert result["obs_variable"] == "o_an"
        assert result["thredds"] == True
        assert result["climatology"] == True
        assert result["source"] == "WOA23"
        assert isinstance(result["obs_path"], list)
        assert len(result["obs_path"]) == 12  # Monthly data
    
    def test_temperature_metadata(self):
        """Test that temperature gets correct metadata"""
        from oceanval.parsers import find_recipe
        
        result = find_recipe({"temperature": "cobe2"})
        
        assert result["short_name"] == "sea temperature"
        assert result["long_name"] == "sea water temperature"
        assert result["short_title"] == "Temperature"
        assert result["name"] == "temperature"
        assert result["obs_variable"] == "sst"
        assert result["thredds"] == True
        assert result["climatology"] == False
        assert result["source"] == "COBE2"
        assert result["vertical"] == False
        assert "COBE-SST" in result["source_info"]
    
    def test_salinity_metadata(self):
        """Test that salinity gets correct metadata"""
        from oceanval.parsers import find_recipe
        
        result = find_recipe({"salinity": "nsbc"})
        
        assert result["short_name"] == "salinity"
        assert result["long_name"] == "sea water salinity"
        assert result["short_title"] == "Salinity"
        assert result["name"] == "salinity"
        assert result["obs_variable"] == "salinity_mean"
        assert result["thredds"] == True
        assert result["climatology"] == True
        assert result["source"] == "NSBC"
    
    def test_nitrate_metadata(self):
        """Test that nitrate gets correct metadata"""
        from oceanval.parsers import find_recipe
        
        result = find_recipe({"nitrate": "woa23"})
        
        assert result["short_name"] == "nitrate concentration"
        assert result["long_name"] == "nitrate concentration"
        assert result["short_title"] == "Nitrate"
        assert result["obs_variable"] == "n_an"
        assert result["source"] == "WOA23"
        assert isinstance(result["obs_path"], list)
        assert len(result["obs_path"]) == 12
    
    def test_ammonium_metadata(self):
        """Test that ammonium gets correct metadata"""
        from oceanval.parsers import find_recipe
        
        result = find_recipe({"ammonium": "nsbc"})
        
        assert result["short_name"] == "ammonium concentration"
        assert result["long_name"] == "ammonium concentration"
        assert result["short_title"] == "Ammonium"
        assert result["obs_variable"] == "ammonium_mean"
    
    def test_phosphate_metadata(self):
        """Test that phosphate gets correct metadata"""
        from oceanval.parsers import find_recipe
        
        result = find_recipe({"phosphate": "woa23"})
        
        assert result["short_name"] == "phosphate concentration"
        assert result["long_name"] == "phosphate concentration"
        assert result["short_title"] == "Phosphate"
        assert result["obs_variable"] == "p_an"
        assert isinstance(result["obs_path"], list)
    
    def test_silicate_metadata(self):
        """Test that silicate gets correct metadata"""
        from oceanval.parsers import find_recipe
        
        result = find_recipe({"silicate": "woa23"})
        
        assert result["short_name"] == "silicate concentration"
        assert result["long_name"] == "silicate concentration"
        assert result["short_title"] == "Silicate"
        assert result["obs_variable"] == "i_an"
    
    def test_kd490_metadata(self):
        """Test that kd490 gets correct metadata"""
        from oceanval.parsers import find_recipe
        
        result = find_recipe({"kd490": "occci"})
        
        assert result["short_name"] == "KD490"
        assert result["long_name"] == "diffuse attenuation coefficient at 490 nm"
        assert result["short_title"] == "KD490"
        assert result["obs_variable"] == "kd_490"
        assert result["thredds"] == True
        assert result["climatology"] == False
    
    def test_ph_metadata(self):
        """Test that pH gets correct metadata with case insensitivity"""
        from oceanval.parsers import find_recipe
        
        result = find_recipe({"pH": "glodap"})
        
        assert result["short_name"] == "pH"
        assert result["long_name"] == "sea water pH"
        assert result["short_title"] == "pH"
        assert result["obs_variable"] == "pHtsinsitutp"
        assert result["source"] == "GLODAPv2.2016b"
        assert result["thredds"] == True
        assert result["climatology"] == True
        assert "GLODAPv2.2016b" in result["obs_path"]
    
    def test_alkalinity_metadata(self):
        """Test that alkalinity gets correct metadata"""
        from oceanval.parsers import find_recipe
        
        result = find_recipe({"alkalinity": "glodap"})
        
        assert result["short_name"] == "total alkalinity"
        assert result["long_name"] == "sea water total alkalinity"
        assert result["short_title"] == "Total Alkalinity"
        assert result["obs_variable"] == "TAlk"
        assert result["source"] == "GLODAPv2.2016b"
    
    def test_woa23_temperature_with_valid_period(self):
        """Test WOA23 temperature recipe with valid time period"""
        from oceanval.parsers import find_recipe
        
        result = find_recipe({"temperature": "woa23"}, start=1955, end=1964)
        
        assert result["obs_variable"] == "t_an"
        assert isinstance(result["obs_path"], list)
        assert len(result["obs_path"]) == 12
        assert "5564" in result["obs_path"][0]
    
    def test_woa23_salinity_with_valid_period(self):
        """Test WOA23 salinity recipe with valid time period"""
        from oceanval.parsers import find_recipe
        
        result = find_recipe({"salinity": "woa23"}, start=2005, end=2014)
        
        assert result["obs_variable"] == "s_an"
        assert isinstance(result["obs_path"], list)
        assert "A5B4" in result["obs_path"][0]
    
    def test_woa23_temperature_missing_start_end(self):
        """Test that WOA23 temperature/salinity requires start and end"""
        from oceanval.parsers import find_recipe
        
        with pytest.raises(ValueError, match="Start and end depth must be provided"):
            find_recipe({"temperature": "woa23"})
        
        with pytest.raises(ValueError, match="Start and end depth must be provided"):
            find_recipe({"salinity": "woa23"})
    
    def test_woa23_temperature_period_too_long(self):
        """Test that WOA23 rejects periods longer than 10 years"""
        from oceanval.parsers import find_recipe
        
        with pytest.raises(ValueError, match="must fall within a single WOA23 climatological period"):
            find_recipe({"temperature": "woa23"}, start=1955, end=1966)
    
    def test_woa23_temperature_end_year_too_late(self):
        """Test that WOA23 rejects end year > 2022"""
        from oceanval.parsers import find_recipe
        
        with pytest.raises(ValueError, match="End year cannot be greater than 2022"):
            find_recipe({"temperature": "woa23"}, start=2020, end=2025)
    
    def test_woa23_all_time_periods(self):
        """Test all valid WOA23 time periods"""
        from oceanval.parsers import find_recipe
        
        periods = [
            (1955, 1964, "5564"),
            (1965, 1974, "6574"),
            (1975, 1984, "7584"),
            (1985, 1994, "8594"),
            (1995, 2004, "95A4"),
            (2005, 2014, "A5B4"),
            (2015, 2022, "B5C2")
        ]
        
        for start, end, period_code in periods:
            result = find_recipe({"temperature": "woa23"}, start=start, end=end)
            assert period_code in result["obs_path"][0]
    
    def test_vertical_attribute_default(self):
        """Test that vertical attribute is None by default"""
        from oceanval.parsers import find_recipe
        
        result = find_recipe({"nitrate": "woa23"})
        assert result["vertical"] is None
    
    def test_nsbc_all_variables(self):
        """Test NSBC recipe for all supported variables"""
        from oceanval.parsers import find_recipe
        
        variables = {
            "ammonium": "ammonium_mean",
            "nitrate": "nitrate_mean",
            "phosphate": "phosphate_mean",
            "silicate": "silicate_mean",
            "chlorophyll": "chlorophyll_a_mean",
            "oxygen": "oxygen_mean",
            "temperature": "temperature_mean",
            "salinity": "salinity_mean"
        }
        
        for var_name, expected_obs_var in variables.items():
            result = find_recipe({var_name: "nsbc"})
            assert result["obs_variable"] == expected_obs_var
            assert result["source"] == "NSBC"
            assert result["climatology"] == True
            assert result["thredds"] == True
    
    def test_case_insensitivity_for_values(self):
        """Test that recipe values are case-insensitive"""
        from oceanval.parsers import find_recipe
        
        # Test uppercase
        result1 = find_recipe({"oxygen": "WOA23"})
        result2 = find_recipe({"oxygen": "woa23"})
        result3 = find_recipe({"oxygen": "Woa23"})
        
        assert result1["source"] == result2["source"] == result3["source"] == "WOA23"
    
    def test_case_sensitivity_for_keys(self):
        """Test case handling for recipe keys (variable names)"""
        from oceanval.parsers import find_recipe
        
        # Lower case should work
        result = find_recipe({"ph": "glodap"})
        assert result["short_title"] == "pH"
        
        # Upper case should work
        result = find_recipe({"PH": "glodap"})
        assert result["short_title"] == "pH"
    
    def test_occci_url_generation(self):
        """Test that OCCCI generates correct URL structure"""
        from oceanval.parsers import find_recipe
        
        result = find_recipe({"chlorophyll": "occci"})
        
        # Check that URLs are generated for years 1998-2024
        assert len(result["obs_path"]) > 0
        # Verify URL structure
        assert any("1998" in url for url in result["obs_path"])
        assert any("oceancolour.org/thredds" in url for url in result["obs_path"])
    
    def test_woa23_url_structure(self):
        """Test that WOA23 URLs have correct structure"""
        from oceanval.parsers import find_recipe
        
        result = find_recipe({"oxygen": "woa23"})
        
        # Should have 12 monthly URLs
        assert len(result["obs_path"]) == 12
        
        # Check URL structure
        for i, url in enumerate(result["obs_path"], 1):
            month_str = f"{i:02d}"
            assert month_str in url
            assert "woa23" in url
            assert "ncei.noaa.gov/thredds-ocean" in url

    shutil.rmtree("oceanval_matchups", ignore_errors=True)