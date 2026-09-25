from pathlib import Path


def test_gridded_climatology_template_displays_figure_once():
    template = Path("oceanval/data/chunk_clim.pytemplate").read_text()

    assert '\nfig\n' not in template


def test_seasonal_template_r_figures_are_guarded_by_panel_plot_flags():
    template = Path("oceanval/data/chunk_seasonal.pytemplate").read_text()

    # the R figures of each half of the year are only drawn if panel_plot did not draw them
    for flag in ["seasonal_panel_1", "seasonal_panel_2"]:
        assert f"-i {flag} " in template
        assert f"!{flag}){{" in template