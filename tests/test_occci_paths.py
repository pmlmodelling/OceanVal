import pytest

from oceanval.gridded import _filter_occci_paths, _occci_year_month
from oceanval.parsers import find_recipe


@pytest.mark.parametrize("name", ["chlorophyll", "kd490"])
def test_occci_paths_are_filtered_by_year_and_month(name):
    paths = find_recipe({name: "occci"})["obs_path"]
    assert len(paths) == 27 * 12

    two_years = _filter_occci_paths(paths, [2010, 2011], range(1, 13))
    assert len(two_years) == 24
    assert {_occci_year_month(x)[0] for x in two_years} == {2010, 2011}

    spring = _filter_occci_paths(paths, [2010], [3, 4])
    assert [_occci_year_month(x) for x in spring] == [(2010, 3), (2010, 4)]

    assert _filter_occci_paths(paths, [1900], range(1, 13)) == []


def test_occci_year_month_from_path():
    path = (
        "https://www.oceancolour.org/thredds/dodsC/cci/v6.0-release/geographic/"
        "monthly/chlor_a/2018/ESACCI-OC-L3S-CHLOR_A-MERGED-1M_MONTHLY_4km_GEO_PML_OCx-201807-fv6.0.nc"
    )
    assert _occci_year_month(path) == (2018, 7)
    # only the year directory to go on: kept on year alone
    assert _occci_year_month("http://x/monthly/2018/file.nc") == (2018, None)
    assert _filter_occci_paths(["http://x/monthly/2018/file.nc"], [2018], [1]) == ["http://x/monthly/2018/file.nc"]
    # nothing readable: left to be subset once opened
    assert _occci_year_month("http://x/file.nc") == (None, None)
    assert _filter_occci_paths(["http://x/file.nc"], [2018], [1]) == ["http://x/file.nc"]
