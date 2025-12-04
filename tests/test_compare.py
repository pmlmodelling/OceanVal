import oceanval 
import os
import pytest
import tempfile
import shutil
from unittest.mock import patch, MagicMock


class TestCompare:
    """Test suite for compare function with error tests"""
    
    def test_none_model_dict(self):
        """Test that error is raised when model_dict is None"""
        with pytest.raises(AttributeError):
            oceanval.compare(model_dict=None, view=False)
    
    def test_missing_model_path(self):
        """Test that ValueError is raised when a model path doesn't exist"""
        with pytest.raises(ValueError, match="Path .* does not exist"):
            oceanval.compare(
                model_dict={
                    "model1": "/nonexistent/path1",
                    "model2": "/nonexistent/path2"
                },
                view=False
            )
    
    def test_one_missing_model_path(self):
        """Test that ValueError is raised when one model path doesn't exist"""
        temp_dir = tempfile.mkdtemp()
        
        try:
            with pytest.raises(ValueError, match="Path .* does not exist"):
                oceanval.compare(
                    model_dict={
                        "model1": temp_dir,
                        "model2": "/nonexistent/path"
                    },
                    view=False
                )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_first_path_missing(self):
        """Test that error is raised when first path is missing"""
        temp_dir = tempfile.mkdtemp()
        
        try:
            with pytest.raises(ValueError, match="Path .* does not exist"):
                oceanval.compare(
                    model_dict={
                        "model1": "/nonexistent/path",
                        "model2": temp_dir
                    },
                    view=False
                )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_empty_model_dict(self):
        """Test that empty model_dict is handled"""
        # Empty dict should not raise error about missing paths
        # But will fail later in processing
        try:
            oceanval.compare(model_dict={}, view=False)
        except Exception as e:
            # Should not fail on path validation
            assert "does not exist" not in str(e)
    
    def test_single_model_in_dict(self):
        """Test that single model in dict is handled"""
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Single model should be accepted (though comparison requires 2+)
            with patch('builtins.input', return_value='n'):
                oceanval.compare(
                    model_dict={"model1": temp_dir},
                    view=False
                )
        except Exception as e:
            # Should not fail on path validation
            assert "does not exist" not in str(e)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_invalid_model_dict_type(self):
        """Test that non-dict model_dict raises error"""
        with pytest.raises(AttributeError):
            oceanval.compare(model_dict="not_a_dict", view=False)
        
        with pytest.raises(AttributeError):
            oceanval.compare(model_dict=["list", "not", "dict"], view=False)
    
    def test_model_dict_with_none_value(self):
        """Test that None value in model_dict raises error"""
        with pytest.raises(TypeError):
            oceanval.compare(
                model_dict={
                    "model1": None,
                    "model2": "/some/path"
                },
                view=False
            )
    
    def test_model_dict_with_empty_string(self):
        """Test that empty string path raises error"""
        with pytest.raises(ValueError, match="Path .* does not exist"):
            oceanval.compare(
                model_dict={
                    "model1": "",
                    "model2": "/some/path"
                },
                view=False
            )
    
    def test_model_dict_with_integer_value(self):
        """Test that integer value in model_dict raises error"""
        with pytest.raises((TypeError, ValueError)):
            oceanval.compare(
                model_dict={
                    "model1": 123,
                    "model2": "/some/path"
                },
                view=False
            )