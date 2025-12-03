import oceanval 

import os, pytest


class TestAnomaly:
    def test_adder_1(self):
        # very basic ValueError test
        with pytest.raises(ValueError):
            oceanval.add_point_comparison()

        with pytest.raises(ValueError):
            oceanval.add_gridded_comparison()
