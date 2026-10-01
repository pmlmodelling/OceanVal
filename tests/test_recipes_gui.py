"""The create_recipes window: its rows, the server behind it and, where a
browser can be run, the page itself."""

import json
import queue
import re
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request

import numpy as np
import pytest
import xarray as xr

import oceanval
import oceanval.recipes_gui as recipes_gui
from oceanval.create_recipes import RECIPE_VARIABLES, default_selection
from oceanval.recipes_gui import (
    RecipePage,
    check_gridded_options,
    check_point_options,
    check_settings,
    choose_recipes,
    default_form,
    default_settings,
    recipe_rows,
)

CONTEXT = {
    "simdir": "/sim",
    "ndown": 2,
    "domain": "nwes",
    "region": "Northwest European Shelf",
    "start": 2011,
    "end": 2012,
    "fvcom": False,
    "out": "/out/matchup.py",
}


def ticks(rows, variable, kind="gridded"):
    row = next(row for row in rows if row["variable"] == variable)
    return {dataset["recipe"]: dataset["ticked"] for dataset in row[kind]}


class TestRows:
    def test_there_is_one_row_per_variable_alphabetically(self):
        rows = recipe_rows({}, "global")
        assert [row["variable"] for row in rows] == sorted(RECIPE_VARIABLES)

    def test_titles_are_the_ones_the_notes_use(self):
        titles = {row["variable"]: row["title"] for row in recipe_rows({}, "global")}
        assert titles["ph"] == "pH"
        assert titles["kd490"] == "KD490"
        assert titles["ammonium"] == "Ammonium"

    @pytest.mark.parametrize("domain", ["global", "nwes"])
    def test_the_ticks_are_what_the_script_would_leave_live(self, domain):
        # so writing the script straight away gives the one gui=False would
        mapping = {variable: variable for variable in RECIPE_VARIABLES}
        ticked = {
            (row["variable"], dataset["recipe"])
            for row in recipe_rows(mapping, domain)
            for dataset in row["gridded"] + row["point"]
            if dataset["ticked"]
        }
        assert ticked == default_selection(mapping, domain)


class TestErsemDetection:
    def test_more_than_twenty_signature_variables_are_required(self):
        variables = sorted(recipes_gui.ERSEM_VARIABLES)

        assert not recipes_gui.is_likely_nemo_ersem(variables[:20])
        assert recipes_gui.is_likely_nemo_ersem(variables[:21])

    @pytest.mark.parametrize("has_e3t", [True, False])
    def test_hosted_page_suggests_ersem_values_in_amber(self, browser, has_e3t):
        available = set(recipes_gui.ERSEM_VARIABLES)
        if has_e3t:
            available.add("e3t")
        else:
            available.discard("e3t")
        recipe_page = RecipePage(
            recipe_rows({}, "global"),
            available,
            dict(CONTEXT, app={"action": "matchup", "own_vertical": False}),
            lambda *chosen: "/out/matchup.py",
        )
        url = recipe_page.start()
        try:
            browser_page = browser.new_page()
            browser_page.goto(url)

            assert browser_page.input_value("#s-thickness") == ("e3t" if has_e3t else "")
            assert browser_page.input_value("#s-missing_from") == "0"
            assert browser_page.input_value("#s-missing_to") == "0"
            assert browser_page.locator("#g-missing").get_by_text(
                "This appears to be an ERSEM simulation and the above values are assumed."
            ).count() == 1
            for name in ("missing_from", "missing_to"):
                assert "is-ersem" in browser_page.locator(f"#s-{name}").get_attribute("class")
            if has_e3t:
                assert "is-ersem" in browser_page.locator("#s-thickness").get_attribute("class")
            amber = browser_page.locator("#g-missing .group__line.is-ersem")
            assert amber.evaluate("node => getComputedStyle(node).color") == "rgb(138, 90, 0)"
        finally:
            recipe_page.close()

    def test_the_other_regions_datasets_start_unticked(self):
        rows = recipe_rows({"temperature": "thetao"}, "nwes")
        assert ticks(rows, "temperature") == {"cobe2": False, "woa23": False, "nsbc": True}
        assert ticks(rows, "temperature", "point") == {"ices": True}

        rows = recipe_rows({"temperature": "thetao"}, "global")
        # and within a region only the recipe the script leaves live is ticked
        assert ticks(rows, "temperature") == {"cobe2": True, "woa23": False, "nsbc": False}
        assert ticks(rows, "temperature", "point") == {"ices": False}

    def test_a_dataset_outside_the_domain_is_ticked_if_it_is_the_only_one(self):
        assert ticks(recipe_rows({"ammonium": "N4_n"}, "global"), "ammonium") == {
            "nsbc": True
        }
        assert ticks(recipe_rows({"alkalinity": "O3_TA"}, "nwes"), "alkalinity") == {
            "glodap": True
        }

    def test_an_unidentified_variable_is_blank_with_nothing_ticked(self):
        row = next(
            row for row in recipe_rows({}, "nwes") if row["variable"] == "salinity"
        )
        datasets = row["gridded"] + row["point"]

        assert row["model_variable"] == ""
        assert not any(dataset["ticked"] for dataset in datasets)
        # what the page ticks once a model variable is filled in
        assert {dataset["recipe"]: dataset["default"] for dataset in datasets} == {
            "woa23": False,
            "nsbc": True,
            "ices": True,
        }

    def test_kd490_has_no_point_dataset(self):
        row = next(
            row for row in recipe_rows({}, "global") if row["variable"] == "kd490"
        )
        assert row["point"] == []
        assert [dataset["label"] for dataset in row["gridded"]] == ["OC-CCI"]

    def test_vertical_is_only_offered_where_the_observations_have_depths(self):
        rows = recipe_rows({}, "global")
        offered = {
            (row["variable"], dataset["recipe"])
            for row in rows
            for dataset in row["gridded"] + row["point"]
            if dataset["vertical_option"]
        }

        assert {recipe for _, recipe in offered} == {"woa23", "nsbc", "ices"}
        # surface-only: satellite, sea surface temperature and GLODAP's surface
        assert not offered & {
            ("chlorophyll", "occci"), ("kd490", "occci"),
            ("temperature", "cobe2"), ("ph", "glodap"), ("alkalinity", "glodap"),
        }

    def test_only_woa23_temperature_and_salinity_are_per_decade(self):
        decadal = {
            (row["variable"], dataset["recipe"])
            for row in recipe_rows({}, "global")
            for dataset in row["gridded"]
            if dataset["decadal"]
        }
        assert decadal == {("temperature", "woa23"), ("salinity", "woa23")}

    def test_tooltips_leave_out_what_only_makes_sense_in_the_script(self):
        for row in recipe_rows({}, "global"):
            for dataset in row["gridded"] + row["point"]:
                assert "below" not in dataset["details"]
                assert "recipe:" not in dataset["details"]


def _get(page, query=""):
    url = page.url.split("?")[0] + query
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return response.status, response.read().decode()
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode()


def _post(url, path, body, token=None):
    """POST to the server behind url, as the page does."""
    parts = urllib.parse.urlsplit(url)
    if token is None:
        token = urllib.parse.parse_qs(parts.query)["token"][0]
    request = urllib.request.Request(
        f"{parts.scheme}://{parts.netloc}{path}",
        data=json.dumps(body).encode(),
        method="POST",
        headers={"Content-Type": "application/json", "X-OceanVal-Token": token},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


@pytest.fixture
def page():
    written = []

    def write(*chosen):
        written.append(chosen)
        return "/out/matchup.py"

    page = RecipePage(
        recipe_rows({"temperature": "thetao"}, "nwes"),
        {"thetao", "so", "P1_Chl", "P2_Chl"},
        CONTEXT,
        write,
    )
    page.written = written
    page.start()
    yield page
    page.close()


class TestServer:
    def test_the_page_needs_the_token(self, page):
        assert _get(page)[0] == 403
        assert _get(page, "?token=wrong")[0] == 403

    def test_the_page_holds_the_rows(self, page):
        status, body = _get(page, f"?token={page.token}")
        state = re.search(r'<script type="application/json" id="state">(.*?)</script>', body, re.S)
        state = json.loads(state.group(1))

        assert status == 200
        assert [row["variable"] for row in state["rows"]] == sorted(RECIPE_VARIABLES)
        assert state["context"] == CONTEXT

    def test_a_variable_name_cannot_break_out_of_the_page(self, page):
        page.available.add("</script><script>alert(1)</script>")
        _, body = _get(page, f"?token={page.token}")

        assert "<script>alert(1)" not in body

    def test_posting_needs_the_token(self, page):
        status, _ = _post(page.url, "/cancel", {}, token="wrong")

        assert status == 403
        assert not page._done.is_set()

    def test_a_model_variable_not_in_the_output_is_sent_back(self, page):
        status, reply = _post(
            page.url,
            "/write",
            {"rows": [{"variable": "temperature", "model_variable": "thetaoo", "selected": ["nsbc"]}]},
        )

        assert status == 400
        assert reply["errors"] == {"temperature": "thetaoo is not in the model output."}
        assert page.written == []
        assert not page._done.is_set()

    def test_the_script_is_written_with_what_was_chosen(self, page):
        rows = [
            {"variable": "temperature", "model_variable": "thetao", "selected": ["cobe2", "nsbc", "ices"]},
            {"variable": "chlorophyll", "model_variable": " P1_Chl + P2_Chl ", "selected": ["nsbc"]},
            {"variable": "salinity", "model_variable": "", "selected": []},
        ]
        status, reply = _post(page.url, "/write", {"rows": rows})
        # a request without settings keeps the defaults
        chosen = (
            {"temperature": "thetao", "chlorophyll": "P1_Chl+P2_Chl"},
            {
                ("temperature", "cobe2"),
                ("temperature", "nsbc"),
                ("temperature", "ices"),
                ("chlorophyll", "nsbc"),
            },
            default_settings(2011, 2012),
            {},
            {},
        )

        assert (status, reply) == (200, {"ok": True, "out": "/out/matchup.py"})
        assert page.written == [chosen]
        assert page.wait() == chosen
        # and a second click does not write it again
        assert _post(page.url, "/write", {"rows": rows})[0] == 409
        assert len(page.written) == 1

    def test_a_dataset_the_variable_does_not_have_is_refused(self, page):
        status, _ = _post(
            page.url,
            "/write",
            {"rows": [{"variable": "kd490", "model_variable": "thetao", "selected": ["ices"]}]},
        )

        assert status == 400
        assert page.written == []

    def test_a_failed_write_is_reported_and_can_be_tried_again(self, page):
        def write(*chosen):
            raise PermissionError("read-only file system")

        page.write = write
        status, reply = _post(page.url, "/write", {"rows": []})

        assert status == 500
        assert "read-only file system" in reply["error"]
        assert not page._done.is_set()

    def test_cancelling(self, page):
        assert _post(page.url, "/cancel", {})[0] == 200
        assert page.wait() is None

    def test_settings_and_point_options_are_written(self, page):
        form = dict(default_form(2011, 2012), cores="12", lon_min="-20", lon_max="10",
                    lat_min="40", lat_max="65", pdf=True)
        rows = [{
            "variable": "temperature",
            "model_variable": "thetao",
            "selected": ["nsbc", "ices"],
            "point": {"ices": {"point_time_res": "month", "start": "2011", "end": ""}},
        }]
        status, _ = _post(page.url, "/write", {"rows": rows, "settings": form})
        mapping, selection, settings, point_options, gridded_options = page.written[0]

        assert status == 200
        assert (settings["cores"], settings["pdf"]) == (12, True)
        assert (settings["lon_lim"], settings["lat_lim"]) == ([-20, 10], [40, 65])
        assert point_options == {
            ("temperature", "ices"): {
                "start": 2011, "end": None, "point_time_res": ["month"], "vertical": None
            }
        }
        assert gridded_options == {}

    def test_gridded_options_are_written(self, page):
        rows = [{
            "variable": "temperature",
            "model_variable": "thetao",
            "selected": ["cobe2", "nsbc"],
            "gridded": {
                "cobe2": {"start": "2012", "end": "", "vertical": False},
                "nsbc": {"start": "", "end": "", "vertical": True},
            },
        }]
        status, _ = _post(page.url, "/write", {"rows": rows})

        assert status == 200
        assert page.written[0][4] == {
            ("temperature", "cobe2"): {"start": 2012, "end": None, "vertical": None},
            ("temperature", "nsbc"): {"start": None, "end": None, "vertical": True},
        }

    def test_gridded_options_that_cannot_be_used_are_sent_back(self, page):
        rows = [{
            "variable": "temperature",
            "model_variable": "thetao",
            "selected": ["woa23"],
            "gridded": {"woa23": {"start": "2011", "end": "2016"}},
        }]
        status, reply = _post(page.url, "/write", {"rows": rows})

        assert status == 400
        assert reply["gridded_errors"] == {
            "temperature": {
                "woa23": {"end": "These years must sit inside one WOA23 decade, e.g. 2005–2014."}
            }
        }
        assert page.written == []

    def test_settings_that_cannot_be_used_are_sent_back(self, page):
        form = dict(default_form(2011, 2012), cores="0", lon_min="-20")
        status, reply = _post(page.url, "/write", {"rows": [], "settings": form})

        assert status == 400
        assert set(reply["setting_errors"]) == {"cores", "lon_max", "lat_min", "lat_max"}
        assert page.written == []

    def test_point_options_that_cannot_be_used_are_sent_back(self, page):
        rows = [{
            "variable": "temperature",
            "model_variable": "thetao",
            "selected": ["ices"],
            "point": {"ices": {"start": "2020"}},
        }]
        status, reply = _post(page.url, "/write", {"rows": rows})

        assert status == 400
        assert reply["point_errors"] == {
            "temperature": {"ices": {"start": "These years miss the 2011–2012 being matched up."}}
        }

    def test_an_unticked_datasets_options_are_ignored(self, page):
        # the page only shows them for ticked datasets
        rows = [{
            "variable": "temperature",
            "model_variable": "thetao",
            "selected": ["nsbc"],
            "point": {"ices": {"start": "nonsense"}},
        }]
        status, _ = _post(page.url, "/write", {"rows": rows})

        assert status == 200
        assert page.written[0][3] == {}

    def test_an_unticked_gridded_datasets_options_are_ignored(self, page):
        rows = [{
            "variable": "temperature",
            "model_variable": "thetao",
            "selected": ["nsbc"],
            "gridded": {"cobe2": {"start": "nonsense"}},
        }]
        status, _ = _post(page.url, "/write", {"rows": rows})

        assert status == 200
        assert page.written[0][4] == {}


class TestSettingsChecks:
    AVAILABLE = {"thetao", "e3t"}

    def check(self, fvcom=False, **changes):
        return check_settings(dict(default_form(2011, 2012), **changes), self.AVAILABLE, fvcom)

    def test_the_boxes_start_at_the_defaults(self):
        settings, errors = self.check()

        assert errors == {}
        assert settings == default_settings(2011, 2012)

    def test_core_count_cannot_exceed_system_cores(self):
        cpu_count = recipes_gui.os.cpu_count()
        if not cpu_count:
            pytest.skip("system core count is unavailable")
        _, errors = self.check(cores=str(cpu_count + 1))

        assert errors["cores"] == f"This machine has {cpu_count} cores. Choose {cpu_count} or fewer."

    @pytest.mark.parametrize(
        "changes, errors",
        [
            ({"start": "2011.5"}, {"start"}),
            ({"end": "2010"}, {"end"}),
            ({"lon_min": "-20"}, {"lon_max", "lat_min", "lat_max"}),
            ({"lon_min": "x", "lon_max": "1", "lat_min": "2", "lat_max": "3"}, {"lon_min"}),
            ({"lon_min": "5", "lon_max": "1", "lat_min": "2", "lat_max": "3"}, {"lon_max"}),
            ({"lon_min": "0", "lon_max": "1", "lat_min": "-95", "lat_max": "3"}, {"lat_min"}),
            ({"missing_to": "5"}, {"missing_from"}),
            ({"missing_from": "5", "missing_to": "1"}, {"missing_to"}),
            ({"missing_from": "inf"}, {"missing_from"}),
            ({"cores": "0"}, {"cores"}),
            ({"thickness": "not_there"}, {"thickness"}),
            ({"point_time_res": "week"}, {"point_time_res"}),
            ({"subregions": "arctic"}, {"subregions"}),
        ],
    )
    def test_boxes_that_cannot_be_used(self, changes, errors):
        assert set(self.check(**changes)[1]) == errors

    def test_the_report_is_concise_unless_unticked(self):
        assert self.check()[0]["concise"] is True
        assert self.check(concise=False)[0]["concise"] is False
        assert self.check(concise="true")[0]["concise"] is True
        assert self.check(concise="false")[0]["concise"] is False

    def test_the_detail_choice_must_be_known(self):
        assert self.check(concise="verbose")[1] == {"concise": "Choose concise or detailed."}

    def test_the_file_filters_create_recipes_was_given(self):
        form = default_form(2011, 2012, ["ptrc", "5d"], ["grid_T"])
        settings, errors = check_settings(form, self.AVAILABLE)

        assert (form["exclude"], form["require"]) == ("ptrc 5d", "grid_T")
        assert errors == {}
        assert (settings["exclude"], settings["require"]) == (["ptrc", "5d"], ["grid_T"])

    def test_the_subset_is_all_four_limits(self):
        settings, _ = self.check(lon_min="-20", lon_max="10.5", lat_min="40", lat_max="65")
        assert (settings["lon_lim"], settings["lat_lim"]) == ([-20, 10.5], [40, 65])

    @pytest.mark.parametrize(
        "low, high, value", [("0", "", 0), ("0", "1e20", [0, 1e20])]
    )
    def test_as_missing_is_a_value_or_a_range(self, low, high, value):
        assert self.check(missing_from=low, missing_to=high)[0]["as_missing"] == value

    @pytest.mark.parametrize("typed", ["z_level", "z-level", "z level"])
    def test_z_level_however_it_is_written(self, typed):
        assert self.check(thickness=typed)[0]["thickness"] == "z_level"

    def test_thickness_can_be_a_variable_or_a_file(self, tmp_path):
        assert self.check(thickness="e3t")[0]["thickness"] == "e3t"
        path = tmp_path / "thickness.nc"
        path.write_text("")
        assert self.check(thickness=str(path))[0]["thickness"] == str(path)

    def test_fvcom_needs_no_thickness(self):
        settings, errors = self.check(fvcom=True, thickness="anything")
        assert (settings["thickness"], errors) == (None, {})

    def test_out_dir_must_not_be_a_file(self, tmp_path):
        path = tmp_path / "a_file"
        path.write_text("")
        assert set(self.check(out_dir=str(path))[1]) == {"out_dir"}
        assert self.check(out_dir=str(tmp_path / "new"))[0]["out_dir"] == str(tmp_path / "new")

    def test_regional_summaries_can_come_from_a_file(self, tmp_path):
        path = tmp_path / "regions.nc"
        path.write_text("")
        assert self.check(subregions="file", subregions_file=str(path))[0]["subregions"] == str(path)
        assert set(self.check(subregions="file")[1]) == {"subregions_file"}
        assert set(self.check(subregions="file", subregions_file="regions.txt")[1]) == {"subregions_file"}
        assert set(self.check(subregions="file", subregions_file=str(tmp_path / "no.nc"))[1]) == {"subregions_file"}

    def test_file_filters_are_split_on_spaces(self):
        settings, _ = self.check(exclude="restart 5d", require="")
        assert (settings["exclude"], settings["require"]) == (["restart", "5d"], None)


class TestPointOptions:
    def test_empty_boxes_leave_everything_to_the_global_settings(self):
        assert check_point_options({}, (2011, 2012)) == (
            {"start": None, "end": None, "point_time_res": None, "vertical": None},
            {},
        )

    def test_the_options_are_read(self):
        options, errors = check_point_options(
            {"point_time_res": "month,day", "start": "2011", "end": "2012"}, (2011, 2012)
        )
        assert errors == {}
        assert options == {
            "start": 2011, "end": 2012, "point_time_res": ["month", "day"], "vertical": None
        }

    def test_vertical_is_surface_only_until_ticked(self):
        assert check_point_options({}, None)[0]["vertical"] is None
        assert check_point_options({"vertical": True}, None)[0]["vertical"] is True

    @pytest.mark.parametrize(
        "form, error",
        [
            ({"start": "x"}, "start"),
            ({"start": "2012", "end": "2011"}, "end"),
            ({"start": "2015"}, "start"),
            ({"end": "2000"}, "end"),
            ({"point_time_res": "week"}, "point_time_res"),
        ],
    )
    def test_options_that_cannot_be_used(self, form, error):
        assert list(check_point_options(form, (2011, 2012))[1]) == [error]


class TestGriddedOptions:
    def test_empty_boxes_leave_everything_to_the_global_settings(self):
        assert check_gridded_options({}, (2011, 2012), True) == (
            {"start": None, "end": None, "vertical": None},
            {},
        )

    def test_the_years_are_read(self):
        options, errors = check_gridded_options({"start": "2011", "end": "2012"}, (2011, 2012))
        assert errors == {}
        assert options == {"start": 2011, "end": 2012, "vertical": None}

    def test_vertical_is_only_read_where_it_is_offered(self):
        assert check_gridded_options({"vertical": True}, None, True)[0]["vertical"] is True
        assert check_gridded_options({"vertical": True}, None, False)[0]["vertical"] is None

    @pytest.mark.parametrize(
        "form, error",
        [
            ({"start": "x"}, "start"),
            ({"start": "2012", "end": "2011"}, "end"),
            ({"start": "2015"}, "start"),
            ({"end": "2000"}, "end"),
        ],
    )
    def test_years_that_cannot_be_used(self, form, error):
        assert list(check_gridded_options(form, (2011, 2012))[1]) == [error]

    @pytest.mark.parametrize(
        "form, errors",
        [
            ({}, []),
            ({"start": "2011", "end": "2012"}, []),
            ({"start": "2015", "end": "2022"}, []),
            ({"start": "2011"}, ["end"]),
            ({"end": "2012"}, ["start"]),
            ({"start": "2011", "end": "2016"}, ["end"]),
        ],
    )
    def test_woa23_years_must_sit_inside_one_decade(self, form, errors):
        # were they not per decade, all of these could be used
        assert list(check_gridded_options(form, None, True, decadal=True)[1]) == errors
        assert check_gridded_options(form, None, True)[1] == {}

    def test_global_years_without_a_woa23_decade_require_dataset_years(self):
        options, errors = check_gridded_options({}, (1990, 2020), True, decadal=True)

        assert errors == {
            "start": "WOA23 publishes this per decade, so give both years.",
            "end": "WOA23 publishes this per decade, so give both years.",
        }
        options, errors = check_gridded_options(
            {"start": "2005", "end": "2014"}, (1990, 2020), True, decadal=True
        )
        assert errors == {}
        assert (options["start"], options["end"]) == (2005, 2014)


class TestHosting:
    def test_the_oceanval_app_shows_the_window_instead(self, monkeypatch):
        monkeypatch.setattr(recipes_gui, "_open_browser", lambda url: pytest.fail("opened"))
        shown = []

        class Host:
            def show_recipes(self, page):
                shown.append(page)
                return "chosen"

        with recipes_gui.hosted_by(Host()):
            result = choose_recipes(
                {"temperature": "thetao"}, "global", {"thetao"}, CONTEXT, lambda *args: None
            )

        assert result == "chosen"
        [page] = shown
        # it has no server of its own
        assert page._server is None
        assert page.context == CONTEXT
        assert recipes_gui._host is None

    VERTICAL = [{
        "variable": "temperature",
        "model_variable": "thetao",
        "selected": ["nsbc"],
        "gridded": {"nsbc": {"start": "", "end": "", "vertical": True}},
    }]

    def app_page(self, own_vertical=False, fvcom=False):
        """The window as the oceanval app shows it."""
        written = []
        page = RecipePage(
            recipe_rows({"temperature": "thetao"}, "nwes"),
            {"thetao"},
            dict(CONTEXT, fvcom=fvcom, app={"action": "matchup", "own_vertical": own_vertical}),
            lambda *chosen: written.append(chosen) or "/out/matchup.py",
        )
        page.written = written
        return page

    def test_the_app_always_asks(self):
        page = self.app_page()
        status, _ = page.submit({"rows": [], "settings": dict(page.form, ask=False)})

        assert status == 200
        assert page.written[0][2]["ask"] is True

    def test_in_the_app_vertical_needs_a_thickness(self):
        page = self.app_page()
        status, reply = page.submit({"rows": self.VERTICAL})

        assert status == 400
        assert reply["setting_errors"] == {"thickness": recipes_gui.THICKNESS_NEEDED}
        assert page.written == []
        settings = dict(page.form, thickness="z_level")
        assert page.submit({"rows": self.VERTICAL, "settings": settings})[0] == 200

    def test_so_does_your_own_data_through_the_water_column(self):
        assert "thickness" in self.app_page(own_vertical=True).submit({"rows": []})[1]["setting_errors"]
        # FVCOM output is regridded onto z-levels
        assert self.app_page(own_vertical=True, fvcom=True).submit({"rows": []})[0] == 200

    @pytest.mark.parametrize("action", ["matchup", "matchup_validate"])
    def test_the_report_options_are_asked_for_elsewhere(self, browser, action):
        """In the app they come once the matchups are checked, or when the
        report is built later; matchup's own subset stays."""
        recipe_page = RecipePage(
            recipe_rows({"temperature": "thetao"}, "global"),
            {"thetao"},
            dict(CONTEXT, app={"action": action, "own_vertical": False}),
            lambda *chosen: "/out/matchup.py",
        )
        url = recipe_page.start()
        try:
            page = browser.new_page()
            page.goto(url)

            for group in ("group-report", "group-detail", "group-regional"):
                assert page.is_hidden(f"#{group}")
            assert page.is_visible("#group-subset")
        finally:
            recipe_page.close()


class TestChooseRecipes:
    def test_it_waits_for_the_page_to_be_written(self, monkeypatch, capsys):
        written = []

        def write(*chosen):
            written.append(chosen)
            return "/out/matchup.py"

        def open_browser(url):
            # the user ticks WOA23 and clicks Write script
            rows = [{"variable": "temperature", "model_variable": "thetao", "selected": ["woa23"]}]
            threading.Thread(target=_post, args=(url, "/write", {"rows": rows})).start()
            return True

        monkeypatch.setattr(recipes_gui, "_can_open_browser", lambda: True)
        monkeypatch.setattr(recipes_gui, "_open_browser", open_browser)
        result = choose_recipes({"temperature": "thetao"}, "global", {"thetao"}, CONTEXT, write)

        assert result == (
            {"temperature": "thetao"},
            {("temperature", "woa23")},
            default_settings(2011, 2012),
            {},
            {},
        )
        assert written == [result]
        assert "open in your web browser" in capsys.readouterr().out

    def test_the_link_is_printed_when_no_browser_can_be_opened(self, monkeypatch, capsys):
        wait = RecipePage.wait

        def cancel_then_wait(page):
            # the user follows the printed link, and cancels
            threading.Thread(target=_post, args=(page.url, "/cancel", {})).start()
            return wait(page)

        monkeypatch.setattr(recipes_gui, "_can_open_browser", lambda: False)
        monkeypatch.setattr(RecipePage, "wait", cancel_then_wait)
        result = choose_recipes({}, "global", set(), CONTEXT, lambda *args: "/out")
        printed = capsys.readouterr().out

        assert result is None
        assert "Open this link in a web browser" in printed
        assert re.search(r"http://127\.0\.0\.1:(\d+)/\?token=\S+", printed)
        assert "forward port" in printed

    def test_no_browser_is_opened_without_a_display(self, monkeypatch):
        # webbrowser would fall back on a text browser in the terminal
        monkeypatch.setattr(sys, "platform", "linux")
        for name in ("DISPLAY", "WAYLAND_DISPLAY", "BROWSER"):
            monkeypatch.delenv(name, raising=False)
        assert not recipes_gui._can_open_browser()

        monkeypatch.setenv("DISPLAY", ":1")
        assert recipes_gui._can_open_browser()

    def test_a_browser_set_by_vs_code_is_used(self, monkeypatch):
        monkeypatch.setattr(sys, "platform", "linux")
        for name in ("DISPLAY", "WAYLAND_DISPLAY"):
            monkeypatch.delenv(name, raising=False)
        monkeypatch.setenv("BROWSER", "/home/me/.vscode-server/bin/helpers/browser.sh")

        assert recipes_gui._can_open_browser()


def _open_window(browser, tmp_path, monkeypatch):
    """Run create_recipes(gui=True) on a small NEMO-like simulation, whose KD490
    is not identified, and open its window. Returns the page, the path the
    script is written to, and a function waiting for create_recipes."""
    values = np.random.rand(1, 3, 2, 2).astype("f4")
    dims = ("time", "deptht", "y", "x")
    dataset = xr.Dataset(
        {
            "thetao": (dims, values, {"long_name": "sea water potential temperature"}),
            # nothing identifies a variable described like this as KD490
            "kd_misc": (dims, values, {"long_name": "light extinction"}),
        }
    )
    dataset["time"] = ("time", [0.0], {"units": "days since 2011-01-01"})
    (tmp_path / "sim").mkdir()
    dataset.to_netcdf(tmp_path / "sim" / "output.nc")

    links = queue.Queue()
    monkeypatch.setattr(recipes_gui, "_can_open_browser", lambda: True)
    monkeypatch.setattr(recipes_gui, "_open_browser", lambda url: links.put(url) or True)
    out = str(tmp_path / "matchup.py")
    returned = {}
    thread = threading.Thread(
        target=lambda: returned.update(
            out=oceanval.create_recipes(
                simdir=str(tmp_path / "sim"), ndown=0, out=out, domain="nwes",
                start=2011, end=2012, ask=False, gui=True,
            )
        ),
        daemon=True,
    )
    thread.start()

    page = browser.new_page()
    page.goto(links.get(timeout=120))

    def finished():
        thread.join(timeout=60)
        return returned["out"]

    return page, out, finished


def test_filling_in_a_variable_in_the_browser(browser, tmp_path, monkeypatch):
    """The page, driven as a user would: fill in the variable that was not
    identified, and write the script."""
    page, out, finished = _open_window(browser, tmp_path, monkeypatch)
    kd490 = page.locator('input[aria-label="Model variable for KD490"]')
    occci = page.locator('input[aria-label="OC-CCI, Global, for KD490"]')
    assert kd490.input_value() == ""
    assert occci.is_disabled()

    # a name that is not in the output holds up writing the script
    kd490.fill("kd_mis")
    assert page.is_disabled("#write")
    # a real one unlocks the datasets, ticking what nwes would use - the
    # global OC-CCI, as the shelf has no KD490 dataset of its own
    kd490.fill("kd_misc")
    assert occci.is_enabled()
    assert occci.is_checked()

    page.click("#write")
    page.wait_for_selector("#done:not([hidden])")

    assert finished() == out
    assert (
        '\noceanval.add_gridded_comparison(\n    name="kd490",\n'
        '    model_variable="kd_misc",\n'
    ) in open(out).read()


def test_settings_in_the_browser(browser, tmp_path, monkeypatch):
    """A partial subset holds up writing; the settings and a point dataset's
    own options reach the script."""
    page, out, finished = _open_window(browser, tmp_path, monkeypatch)

    assert page.locator(".settings__grid > .settings__column").count() == 4
    assert page.locator("#s-cores").evaluate(
        "node => node.closest('.settings__column') === document.querySelector('#s-start').closest('.settings__column')"
    )
    assert page.locator("#s-pdf").evaluate(
        "node => node.closest('.settings__column') === document.querySelector('#s-lon_min').closest('.settings__column')"
    )
    assert page.locator("#s-subregions").evaluate(
        "node => node.closest('.settings__column') === document.querySelector('#s-point_time_res').closest('.settings__column')"
    )
    assert page.text_content("#settings-title") == "Global settings"
    assert page.locator("#s-start-label").text_content().startswith("First")
    assert page.locator("#s-end-label").text_content().startswith("Last")
    assert page.locator("#s-start").locator("xpath=ancestor::fieldset").locator("legend").text_content() == "What years do you want to validate?"
    page.fill("#s-start", "")
    page.fill("#s-end", "")
    assert "First must be a year, e.g. 2011." in page.text_content("#g-years")
    assert "Last must be a year, e.g. 2011." in page.text_content("#g-years")
    page.fill("#s-start", "2011")
    page.fill("#s-end", "2012")
    assert page.locator(".settings__sub").count() == 0
    assert "Matchup" not in page.locator(".settings__grid legend").all_text_contents()
    assert page.locator("#group-subset legend").text_content() == "Do you want a spatial subset?"
    assert page.locator("#s-thickness").evaluate("node => node.previousElementSibling.textContent") == "Is the model z-level or is thickness supplied?"
    assert page.locator("#s-missing_from").evaluate("node => node.closest('.g-row').querySelector('.g-label').textContent") == "What should be treated as missing values?"
    assert page.locator("#s-point_time_res").evaluate("node => node.closest('.g-row').querySelector('.g-label').textContent") == "Match point observations by"
    # a "?" beside it explains each option, and only opens when asked
    assert page.locator("#help-point_time_res").evaluate("node => node.open") is False
    assert not page.locator("#help-point_time_res .opts__help-popover").is_visible()
    page.click("#help-point_time_res > summary")
    assert page.locator("#help-point_time_res").evaluate("node => node.open") is True
    popover = page.locator("#help-point_time_res .opts__help-popover")
    assert popover.is_visible()
    for label in ("Year, month, day", "Year, month", "Month, day", "Month"):
        assert label in popover.locator("dt").all_text_contents()
    box = popover.bounding_box()
    assert box["x"] >= 0 and box["x"] + box["width"] <= page.viewport_size["width"]
    page.click("#help-point_time_res > summary")
    assert not popover.is_visible()
    assert page.locator("#group-detail legend").count() == 0
    assert page.locator("#group-regional legend").count() == 0
    assert page.locator("#s-subregions").evaluate("node => node.closest('label').querySelector('.g-label').textContent") == "Which region do you want to use for subregion analysis?"

    page.fill("#s-lon_min", "-20")
    assert page.is_disabled("#write")
    page.fill("#s-lon_max", "10")
    page.fill("#s-lat_min", "40")
    page.fill("#s-lat_max", "65")
    cpu_count = page.evaluate("JSON.parse(document.getElementById('state').textContent).cpu_count")
    valid_cores = min(3, cpu_count) if cpu_count else 3
    if cpu_count:
        page.fill("#s-cores", str(cpu_count + 1))
        assert page.is_disabled("#write")
        assert f"This machine has {cpu_count} cores" in page.text_content("#g-matchup")
    page.fill("#s-cores", str(valid_cores))
    assert page.locator(".cores-row .g-label").text_content() == "How many cores do you want to use?"
    assert page.text_content("#group-report legend") == "Which additional validation report formats do you want?"
    assert page.locator("#s-pdf").bounding_box()["y"] == page.locator("#s-word").bounding_box()["y"]
    assert page.locator("#s-concise").evaluate("node => node.tagName") == "SELECT"
    assert page.locator("#s-concise").locator("option").all_text_contents() == ["Concise", "Detailed"]
    assert page.text_content("#group-detail .g-label") == "How detailed do you want the validation to be?"
    page.select_option("#s-concise", "false")
    assert page.is_enabled("#write")
    page.select_option('select[aria-label="Match ICES observations for Temperature by"]', "month")
    # a gridded dataset's years and Vertical, which only depth-resolved ones offer
    page.fill('input[aria-label="First year of NSBC observations for Temperature"]', "2012")
    page.check(
        'input[aria-label="Validate NSBC observations for Temperature through the full water column"]'
    )
    assert page.locator(
        'input[aria-label="Validate COBE2 observations for Temperature through the full water column"]'
    ).count() == 0
    page.click("#write")
    page.wait_for_selector("#done:not([hidden])")

    assert finished() == out
    script = open(out).read()
    assert f"    lon_lim=[-20, 10],\n    lat_lim=[40, 65],\n    cores={valid_cores},\n" in script
    assert "    concise=False,\n" in script
    assert '    recipe={"temperature": "ices"},\n    point_time_res=["month"],\n' in script
    assert (
        '    recipe={"temperature": "nsbc"},\n'
        '    start=2012,\n'
        '    climatology=True,\n'
        '    vertical=True,'
    ) in script


def test_woa23_dataset_years_are_required_when_global_years_have_no_decade(browser, tmp_path, monkeypatch):
    page, _, finished = _open_window(browser, tmp_path, monkeypatch)
    page.fill("#s-start", "1990")
    page.fill("#s-end", "2020")
    page.check('input[aria-label="WOA23, Global, for Temperature"]')

    first_year = page.locator('input[aria-label="First year of WOA23 observations for Temperature"]')
    last_year = page.locator('input[aria-label="Last year of WOA23 observations for Temperature"]')
    year_row = first_year.locator("xpath=ancestor::div[contains(concat(' ', @class, ' '), ' opts__row ')]")
    assert "is-required" in year_row.get_attribute("class")
    assert first_year.get_attribute("aria-required") == "true"
    assert last_year.get_attribute("aria-required") == "true"
    assert first_year.get_attribute("aria-invalid") == "true"
    assert last_year.get_attribute("aria-invalid") == "true"
    opts_block = first_year.locator("xpath=ancestor::div[contains(concat(' ', @class, ' '), ' opts ')]")
    help = opts_block.locator(".opts__help")
    assert help.locator("summary").get_attribute("aria-label") == "Show available WOA23 year periods"
    assert help.locator(".opts__help-popover").is_hidden()
    help.locator("summary").click()
    popover = help.locator(".opts__help-popover")
    assert popover.is_visible()
    assert popover.locator("li").all_text_contents() == [
        "1955–1964", "1965–1974", "1975–1984", "1985–1994",
        "1995–2004", "2005–2014", "2015–2022",
    ]
    assert "First and Last must fit within the same period." in popover.text_content()
    assert page.is_disabled("#write")
    assert page.is_visible("#fix-settings")

    first_year.fill("2005")
    last_year.fill("2014")
    assert first_year.get_attribute("aria-invalid") == "false"
    assert last_year.get_attribute("aria-invalid") == "false"
    assert page.is_enabled("#write")
    assert page.is_hidden("#fix-settings")

    page.click("#cancel")
    page.wait_for_selector("#done:not([hidden])")
    assert finished() is None
