import pytest

from oceanval.parsers import find_recipe, recipe_list


RECIPE_CASES = [
    (next(iter(recipe)), recipe[next(iter(recipe))])
    for recipe in recipe_list
]


@pytest.mark.parametrize("name, source", RECIPE_CASES)
def test_recipe_returns_required_metadata(name, source):
    """Every registered recipe should resolve without accessing remote data."""
    start = 2005 if source == "woa23" and name in {"temperature", "salinity"} else None
    end = 2014 if start is not None else None

    result = find_recipe({name: source}, start=start, end=end)

    required_fields = {
        "name",
        "source",
        "source_info",
        "obs_path",
        "obs_variable",
        "climatology",
        "thredds",
    }
    assert required_fields.issubset(result)
    assert result["name"] == name
    assert result["obs_variable"]
    assert result["obs_path"]
    assert result["source"]
    assert isinstance(result["climatology"], bool)
    assert result["thredds"] is True


@pytest.mark.parametrize(
    "recipe, expected_source",
    [
        ({"temperature": "cobe2"}, "COBE2"),
        ({"nitrate": "woa23"}, "WOA23"),
        ({"chlorophyll": "occci"}, "OCCCI"),
        ({"ph": "glodap"}, "GLODAPv2.2016b"),
        ({"oxygen": "nsbc"}, "NSBC"),
    ],
)
def test_recipe_source_metadata(recipe, expected_source):
    """Representative recipes should identify their expected data source."""
    result = find_recipe(
        recipe,
        start=2005 if recipe == {"temperature": "cobe2"} else None,
        end=2014 if recipe == {"temperature": "cobe2"} else None,
    )

    assert result["source"] == expected_source


def test_woa23_temperature_and_salinity_select_requested_period():
    """WOA23 temperature and salinity URLs should encode the decade period."""
    for name, variable in (("temperature", "t_an"), ("salinity", "s_an")):
        result = find_recipe({name: "woa23"}, start=1995, end=2004)

        assert result["obs_variable"] == variable
        assert len(result["obs_path"]) == 1
        assert "95A4" in result["obs_path"][0]
        assert result["climatology"] is True


def test_woa23_temperature_and_salinity_require_years():
    """Decadal WOA23 recipes must receive a climatology period."""
    for name in ("temperature", "salinity"):
        with pytest.raises(ValueError, match="Start and end depth must be provided"):
            find_recipe({name: "woa23"})


def test_woa23_rejects_years_outside_supported_periods():
    with pytest.raises(ValueError, match="End year cannot be greater than 2022"):
        find_recipe({"temperature": "woa23"}, start=2023, end=2032)


def test_recipe_name_and_source_are_case_insensitive():
    result = find_recipe({"TeMpErAtUrE": "CoBe2"})

    assert result["name"] == "temperature"
    assert result["source"] == "COBE2"


@pytest.mark.parametrize(
    "recipe, message",
    [
        ({}, "exactly one key"),
        ({"temperature": "cobe2", "oxygen": "woa23"}, "exactly one key"),
        ({"temperature": None}, "not valid"),
        ({"temperature": "unknown"}, "not valid"),
        ({"unknown": "cobe2"}, "not valid"),
    ],
)
def test_invalid_recipe_definitions_raise(recipe, message):
    with pytest.raises(ValueError, match=message):
        find_recipe(recipe)
