import oceanval 
import os
import pytest
import tempfile
import shutil
import pandas as pd
import nctoolkit as nc
import numpy as np


class TestAnomaly:
    def test_adder_1(self):
        # very basic ValueError test
        with pytest.raises(ValueError):
            oceanval.add_point_comparison()

        with pytest.raises(ValueError):
            oceanval.add_gridded_comparison()

        with pytest.raises(ValueError):
            oceanval.add_gridded_comparison(name = "foo")
        with pytest.raises(ValueError):
            oceanval.add_point_comparison(name = "bar")

        with pytest.raises(TypeError):
            oceanval.add_point_comparison(name = "foo", source = "bar") 



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
    