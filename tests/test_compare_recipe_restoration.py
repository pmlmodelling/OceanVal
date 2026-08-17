import pytest

import oceanval


def test_compare_restored():
    assert callable(oceanval.compare)

    with pytest.raises(AttributeError):
        oceanval.compare(model_dict=None, view=False)


def test_recipe_option_restored():
    from oceanval.parsers import find_recipe

    recipe = find_recipe({"temperature": "woa23"}, start=1955, end=1964)
    assert recipe["source"] == "WOA23"
    assert recipe["obs_variable"] == "t_an"

    oceanval.reset()
    oceanval.add_gridded_comparison(
        name="temperature",
        source="TestSource",
        model_variable="votemper",
        recipe={"temperature": "woa23"},
        start=1955,
        end=1964,
        obs_path="data/evaldata/gridded/nws/temperature",
        obs_variable="votemper",
        climatology=True,
    )
    assert oceanval.definitions["temperature"].recipe is True
