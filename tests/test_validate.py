import oceanval 
import os
import pytest
import tempfile
import shutil
import glob


class TestValidate:
    """Test suite for validate function"""
    
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
    # error test for variables

    def test_variables_invalid_type(self):
        """Test that ValueError is raised when variables is of invalid type"""
        with pytest.raises(ValueError, match="variables must be either 'all' or a list of strings"):
            oceanval.validate(variables=123, test=True)
        
        with pytest.raises(ValueError, match="variables must be either 'all' or a list of strings"):
            oceanval.validate(variables={"var1": "temperature"}, test=True)
        # test with a list of non-strings
        with pytest.raises(ValueError, match="variables must be a list of strings"):
            oceanval.validate(variables=[1, 2, 3], test=True)

    
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
    
    def test_variables_all_accepted(self):
        """Test that 'all' is accepted for variables"""
        # Should not raise error about variables
        try:
            oceanval.validate(variables="all", concise = "foo_bar") 
        except ValueError as e:
            assert "variables" not in str(e)
    
    def test_variables_list_accepted(self):
        """Test that a list of strings is accepted for variables"""
        # Should not raise error about variables
        try:
            oceanval.validate(variables=["temperature", "salinity"], concise = "foo_bar") 
        except ValueError as e:
            assert "variables" not in str(e)

    def test_variables_string_accepted(self):
        """Test that a single string is accepted for variables"""
        # Should not raise error about variables
        try:
            oceanval.validate(variables="temperature", concise = "foo_bar") 
        except ValueError as e:
            assert "variables" not in str(e)

    def test_variables_empty_list(self):
        """Test that an empty list for variables raises ValueError"""
        with pytest.raises(ValueError, match="variables list is empty"):
            oceanval.validate(variables=[])
    

