import json
from pathlib import Path

import pytest


def test_gridded_climatology_template_displays_figure_once():
    template = Path("oceanval/data/chunk_clim.pytemplate").read_text()

    assert '\nfig\n' not in template


def test_seasonal_template_r_figures_are_guarded_by_panel_plot_flags():
    template = Path("oceanval/data/chunk_seasonal.pytemplate").read_text()

    # the R figures of each half of the year are only drawn if panel_plot did not draw them
    assert template.count("-i seasonal_panel ") == 2
    assert template.count("!seasonal_panel){") == 2


def test_seasonal_template_shows_global_maps_four_months_at_a_time():
    template = Path("oceanval/data/chunk_seasonal.pytemplate").read_text()
    code = template[template.index("if global_grid:\n    seasonal_periods"):]
    code = code[:code.index("\n\n")]

    periods = dict()
    exec(code, {"global_grid": True}, periods)
    assert [list(x) for x in periods["seasonal_periods"]] == [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]]

    periods = dict()
    exec(code, {"global_grid": False}, periods)
    assert [list(x) for x in periods["seasonal_periods"]] == [[1, 2, 3, 4, 5, 6], [7, 8, 9, 10, 11, 12]]


@pytest.mark.parametrize("notebook", ["gridded_template.ipynb", "comparison_regional.ipynb"])
def test_region_map_r_figure_is_guarded_by_panel_plot_flag(notebook):
    text = Path(f"oceanval/data/{notebook}").read_text()

    assert "-i region_panel_plot " in text
    assert "!region_panel_plot){" in text


def test_regional_time_series_r_cell_loads_the_tidyverse_itself():
    # the R cells that used to load it earlier are skipped when panel_plot draws the maps
    cells = json.loads(Path("oceanval/data/gridded_template.ipynb").read_text())["cells"]
    sources = ["".join(cell["source"]) for cell in cells]
    source = [x for x in sources if "%%R -i df_all -i regional" in x][0]

    assert source.index("library(tidyverse") < source.index("%>%")


def test_seasonal_template_separates_groups_of_months_with_a_line():
    template = Path("oceanval/data/chunk_seasonal.pytemplate").read_text()

    # every group of months but the last is followed by a line under its difference maps
    assert "def plot_seasonal_months(months, divider = False):" in template
    assert "divider = i < len(seasonal_periods) - 1" in template


def test_seasonal_template_titles_maps_with_full_month_names():
    template = Path("oceanval/data/chunk_seasonal.pytemplate").read_text()
    source = template[template.index("def plot_seasonal_months"):template.index("    return True\n")]

    assert "calendar.month_name[month]" in source
    assert "month_abbr" not in source
