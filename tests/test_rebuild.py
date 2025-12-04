import oceanval 
import os
import pytest
import tempfile
import shutil


class TestRebuild:
    """Test suite for rebuild function"""
    
    # ensure file path exists
    def test_data_dir_not_exist(self):
        """Test that ValueError is raised when data_dir does not exist"""
        with pytest.raises(ValueError, match="data_dir .* does not exist"):
            oceanval.rebuild(data_dir="/non/existent/path")