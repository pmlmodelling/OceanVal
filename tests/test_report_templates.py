import json
from pathlib import Path

import pytest


def test_gridded_climatology_template_displays_figure_once():
    template = Path("oceanval/data/chunk_clim.pytemplate").read_text()

    assert '\nfig\n' not in template


def test_seasonal_template_r_figures_are_guarded_by_panel_plot_flags():
    template = Path("oceanval/data/chunk_seasonal.pytemplate").read_text()

    # the R figures of each half of the year are only drawn if panel_plot did not draw them
    for flag in ["seasonal_panel_1", "seasonal_panel_2"]:
        assert f"-i {flag} " in template
        assert f"!{flag}){{" in template


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
