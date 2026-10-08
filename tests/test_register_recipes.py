"""Registering recipes of your own in the oceanval window: the pages' requests,
and the pages in a browser."""

import functools
import http.server
import json
import os
import threading

import pytest

from oceanval import recipe_forms, user_recipes
from simulations import write_simulation
from test_app import (  # noqa: F401 - the fixtures
    SETUP_FORM,
    app,
    get,
    get_json,
    leftover_dir,
    page_state,
    post,
    recipe_settings,
    runs,
    units_match,
    wait_for,
)

NITRATE_DIR = os.path.abspath("data/evaldata/gridded/nws/nitrate")
NITRATE = os.path.join(NITRATE_DIR, "model_2000.nc")
POINTS = os.path.abspath("data/chl/obs_csv")


def gridded_form(**changes):
    form = recipe_forms.default_form("gridded")
    form.update(
        variable="nitrate", source="MySat", source_info="My nitrate", units="mmol N/m^3",
        where="local", obs_path=NITRATE, obs_variable="N3_n", climatology="yes",
    )
    form.update(changes)
    return form


def point_form(**changes):
    form = recipe_forms.default_form("point")
    form.update(
        variable="dic", source="DicPts", source_info="DIC samples", units="umol/kg",
        where="global", obs_path=POINTS, short_title="DIC",
    )
    form.update(changes)
    return form


def register(app, kind="gridded"):
    assert post(app, "/api/choose", {"action": "register"})[0] == 200
    assert post(app, "/api/register_kind", {"kind": kind})[0] == 200


@pytest.fixture
def served():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=NITRATE_DIR)
    handler.log_message = lambda *args: None
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}/model_2000.nc"
    server.shutdown()


class TestSteps:
    def test_registering_is_a_choice_on_the_first_page(self, app):
        body = get(app, "/")[1]
        assert 'data-action="register"' in body
        assert "Add your own validation data for future use" in body

    def test_the_way_through_and_back(self, app):
        assert post(app, "/api/choose", {"action": "register"})[0] == 200
        assert (app.view, app.action) == ("register_kind", "register")
        assert post(app, "/api/register_kind", {"kind": "nonsense"})[0] == 409
        assert post(app, "/api/register_kind", {"kind": "point"})[0] == 200
        assert app.view == "register_point"
        # Back keeps what was entered
        assert post(app, "/api/back", {"form": point_form()})[0] == 200
        assert app.view == "register_kind"
        state = app.state(console=False)["register"]
        assert state["kind"] == "point"
        assert state["forms"]["point"]["source"] == "DicPts"
        assert post(app, "/api/register_kind", {"kind": "gridded"})[0] == 200
        assert post(app, "/api/back")[0] == 200
        assert post(app, "/api/back")[0] == 200
        assert app.view == "start"

    def test_nothing_happens_out_of_turn(self, app):
        assert post(app, "/api/register_kind", {"kind": "point"})[0] == 409
        assert post(app, "/api/recipe_save", {"kind": "gridded", "form": gridded_form()})[0] == 409
        assert post(app, "/api/recipe_remove", {"variable": "a", "key": "b", "where": "local"})[0] == 409
        assert post(app, "/api/register_done")[0] == 409

    def test_every_request_needs_the_token(self, app):
        register(app)
        for route in ("recipe_names", "recipe_data", "recipe_save", "recipe_remove", "register_kind", "register_done"):
            status, _ = post(app, f"/api/{route}", {"kind": "gridded", "form": gridded_form()}, token="wrong")
            assert status == 403

    def test_a_kind_that_is_not_one(self, app):
        register(app)
        assert post(app, "/api/recipe_names", {"kind": "other", "form": {}})[0] == 400
        assert post(app, "/api/recipe_data", {"kind": "other", "form": {}})[0] == 400
        assert post(app, "/api/recipe_save", {"kind": "other", "form": {}})[0] == 400

    def test_finishing_goes_back_to_the_start(self, app):
        register(app)
        assert post(app, "/api/register_done")[0] == 200
        assert (app.view, app.action) == ("start", None)


class TestChecks:
    def test_the_names(self, app):
        register(app)
        status, reply = post(app, "/api/recipe_names", {"kind": "gridded", "form": gridded_form(source="WOA23")})
        assert status == 200
        assert "own recipes" in reply["errors"]["source"]
        status, reply = post(app, "/api/recipe_names", {"kind": "gridded", "form": gridded_form()})
        assert reply["errors"] == {}
        assert reply["info"]["recipe"] == 'recipe={"nitrate": "mysat"}'
        assert reply["info"]["labels"] == ["nitrate concentration", "nitrate concentration", "Nitrate"]

    def test_the_data_on_this_machine(self, app):
        register(app)
        status, reply = post(app, "/api/recipe_data", {"kind": "gridded", "form": gridded_form()})
        assert status == 200 and reply["ok"] and reply["running"] is False
        assert reply["found"]["variables"][0]["name"] == "N3_n"
        status, reply = post(app, "/api/recipe_data", {"kind": "gridded", "form": gridded_form(obs_path="/nowhere.nc")})
        assert status == 200 and not reply["ok"]
        assert "no file or directory" in reply["error"]

    def test_data_that_is_relative_is_from_the_directory_worked_in(self, app, tmp_path):
        register(app)
        os.symlink(NITRATE, tmp_path / "obs.nc")
        reply = post(app, "/api/recipe_data", {"kind": "gridded", "form": gridded_form(obs_path="obs.nc")})[1]
        assert reply["ok"] and reply["found"]["obs_path"] == str(tmp_path / "obs.nc")

    def test_point_data(self, app):
        register(app, "point")
        reply = post(app, "/api/recipe_data", {"kind": "point", "form": point_form()})[1]
        assert reply["ok"] and reply["found"]["files"] == 1

    def test_data_on_a_server_is_a_job(self, app, served):
        register(app)
        form = gridded_form(location="url", obs_path=served)
        status, reply = post(app, "/api/recipe_data", {"kind": "gridded", "form": form})
        assert (status, reply["ok"], reply["running"]) == (200, True, True)
        wait_for(lambda: (app.state(console=False)["register"]["job"] or {}).get("status") in ("ok", "failed"))
        job = app.state(console=False)["register"]["job"]
        assert job["status"] == "ok", job
        assert job["found"]["variables"][0]["name"] == "N3_n"
        assert job["signature"] == ["url", [served]]

    def test_a_server_that_cannot_be_reached(self, app):
        register(app)
        form = gridded_form(location="thredds", obs_path="http://127.0.0.1:1/x.nc")
        post(app, "/api/recipe_data", {"kind": "gridded", "form": form})
        wait_for(lambda: (app.state(console=False)["register"]["job"] or {}).get("status") == "failed")
        job = app.state(console=False)["register"]["job"]
        assert "connection was refused" in job["error"]
        status, reply = post(app, "/api/recipe_save", {"kind": "gridded", "form": form})
        assert status == 400 and "connection was refused" in reply["errors"]["obs_path"]
        assert not os.path.exists(user_recipes.local_path(app.cwd))

    def test_an_address_that_cannot_be_used_is_refused_at_once(self, app):
        register(app)
        form = gridded_form(location="thredds", obs_path="https://x.org/thredds/fileServer/a.nc")
        reply = post(app, "/api/recipe_data", {"kind": "gridded", "form": form})[1]
        assert not reply["ok"] and "download link" in reply["error"]
        assert app.state(console=False)["register"]["job"] is None

    def test_leaving_stops_the_check(self, app):
        register(app)
        form = gridded_form(location="thredds", obs_path="http://127.0.0.1:1/x.nc")
        post(app, "/api/recipe_data", {"kind": "gridded", "form": form})
        post(app, "/api/back")
        assert app.state(console=False)["register"]["job"] is None


class TestSaving:
    def test_a_gridded_recipe_is_saved_to_this_directory(self, app, tmp_path):
        register(app)
        status, reply = post(app, "/api/recipe_save", {"kind": "gridded", "form": gridded_form()})
        assert status == 200, reply
        assert reply["saved"]["recipe"] == 'recipe={"nitrate": "mysat"}'
        data = json.load(open(tmp_path / ".oceanvalrc"))
        assert data["recipes"]["nitrate"]["mysat"]["obs_variable"] == "N3_n"
        assert not os.path.exists(user_recipes.global_path())
        state = app.state(console=False)["register"]
        assert [r["key"] for r in state["recipes"]] == ["mysat"]
        assert [s["recipe"] for s in state["saved"]] == ['recipe={"nitrate": "mysat"}']
        # the next recipe starts afresh, in the same place
        assert state["forms"]["gridded"]["source"] == ""
        assert state["forms"]["gridded"]["where"] == "local"

    def test_a_point_recipe_is_saved_everywhere(self, app, tmp_path):
        register(app, "point")
        status, reply = post(app, "/api/recipe_save", {"kind": "point", "form": point_form()})
        assert status == 200, reply
        data = json.load(open(user_recipes.global_path()))
        assert data["recipes"]["dic"]["dicpts"]["short_title"] == "DIC"
        assert not os.path.exists(tmp_path / ".oceanvalrc")

    def test_what_cannot_be_saved_is_sent_back(self, app, tmp_path):
        register(app)
        status, reply = post(
            app, "/api/recipe_save",
            {"kind": "gridded", "form": gridded_form(source="", units="", obs_variable="x", where="")},
        )
        assert status == 400
        assert {"source", "units", "where"} <= set(reply["errors"])
        assert not os.path.exists(tmp_path / ".oceanvalrc")

    def test_a_recipe_of_the_same_name_is_refused_and_the_other_files_is_warned_of(self, app):
        register(app)
        assert post(app, "/api/recipe_save", {"kind": "gridded", "form": gridded_form(where="global")})[0] == 200
        status, reply = post(app, "/api/recipe_save", {"kind": "gridded", "form": gridded_form(where="global")})
        assert status == 400 and "already" in reply["errors"]["source"]
        names = post(app, "/api/recipe_names", {"kind": "gridded", "form": gridded_form()})[1]
        assert names["errors"] == {} and "used in its place" in names["warnings"][0]
        status, reply = post(app, "/api/recipe_save", {"kind": "gridded", "form": gridded_form()})
        assert status == 200 and "used in its place" in reply["warnings"][0]

    def test_a_download_is_saved_once_it_has_been_checked(self, app, served):
        register(app)
        form = gridded_form(location="url", obs_path=served)
        assert "Check the data first" in post(app, "/api/recipe_save", {"kind": "gridded", "form": form})[1]["errors"]["obs_path"]
        post(app, "/api/recipe_data", {"kind": "gridded", "form": form})
        wait_for(lambda: (app.state(console=False)["register"]["job"] or {}).get("status") == "ok")
        status, reply = post(app, "/api/recipe_save", {"kind": "gridded", "form": form})
        assert status == 200, reply
        saved = user_recipes.get("nitrate", "mysat", app.cwd)
        assert (saved["location"], saved["obs_path"]) == ("url", served)

    def test_recipes_are_removed(self, app):
        register(app)
        post(app, "/api/recipe_save", {"kind": "gridded", "form": gridded_form()})
        body = {"variable": "nitrate", "key": "mysat", "where": "local"}
        assert post(app, "/api/recipe_remove", dict(body, where="nowhere"))[0] == 400
        assert post(app, "/api/recipe_remove", body)[0] == 200
        assert post(app, "/api/recipe_remove", body)[0] == 409
        assert app.state(console=False)["register"]["recipes"] == []

    def test_a_file_that_cannot_be_read_is_not_written_over(self, app, tmp_path):
        register(app)
        (tmp_path / ".oceanvalrc").write_text("{broken")
        with pytest.warns(UserWarning):
            status, reply = post(app, "/api/recipe_save", {"kind": "gridded", "form": gridded_form()})
        assert status == 400 and "could not be read" in reply["errors"][""]
        assert (tmp_path / ".oceanvalrc").read_text() == "{broken"
        assert "local" in app.state(console=False)["register"]["problems"]


class TestUsingThem:
    def test_a_registered_recipe_is_offered_ticked_and_written_into_the_script(self, app, tmp_path, runs):
        register(app)
        assert post(app, "/api/recipe_save", {"kind": "gridded", "form": gridded_form()})[0] == 200
        post(app, "/api/register_done")
        write_simulation(tmp_path / "sim", tracers=True)
        post(app, "/api/choose", {"action": "matchup"})
        assert post(app, "/api/setup", {"form": SETUP_FORM})[0] == 200
        assert post(app, "/api/own_data", {"answer": False})[0] == 200
        wait_for(lambda: app.view == "recipes")

        rows = {row["variable"]: row for row in page_state(get(app, "/recipes/")[1])["rows"]}
        mine = [d for d in rows["nitrate"]["gridded"] if d["user"]]
        assert [(d["recipe"], d["label"], d["region"], d["ticked"]) for d in mine] == [
            ("mysat", "MySat", "Yours", True)
        ]
        post_rows = [{"variable": "nitrate", "model_variable": "N3_n", "selected": ["mysat"]}]
        status, reply = post(app, "/recipes/write", {"rows": post_rows, "settings": recipe_settings(app)})
        assert status == 200, reply
        wait_for(lambda: app.view == "units_table" and app.units_rows is not None)
        row = [r for r in app.units_rows if r["title"] == "nitrate (mysat)"][0]
        assert (row["obs_units"], row["obs_variable"]) == ("mmol N/m^3", "N3_n")
        units_match(app)
        wait_for(lambda: runs)
        script = (tmp_path / "matchup.py").read_text()
        assert 'recipe={"nitrate": "mysat"},' in script
        assert "Your recipes, from .oceanvalrc" in script
        compile(script, "matchup.py", "exec")

    def test_a_variable_that_is_not_identified_is_left_blank(self, app, tmp_path):
        register(app, "point")
        assert post(app, "/api/recipe_save", {"kind": "point", "form": point_form(where="local")})[0] == 200
        post(app, "/api/register_done")
        write_simulation(tmp_path / "sim", tracers=True)
        post(app, "/api/choose", {"action": "matchup"})
        post(app, "/api/setup", {"form": SETUP_FORM})
        post(app, "/api/own_data", {"answer": False})
        wait_for(lambda: app.view == "recipes")
        rows = {row["variable"]: row for row in page_state(get(app, "/recipes/")[1])["rows"]}
        dic = rows["dic"]
        assert dic["model_variable"] == ""
        assert [d["ticked"] for d in dic["point"]] == [False]
        assert dic["point"][0]["label"] == "DicPts"


def test_the_pages_in_a_browser(browser, tmp_path):
    from oceanval.app import App

    app = App(cwd=str(tmp_path))
    app.leftovers_asked = True
    url = app.start()
    try:
        page = browser.new_page()
        failures = []
        page.on("pageerror", lambda error: failures.append(str(error)))
        page.goto(url)
        page.wait_for_selector("#view-start:not([hidden])")
        assert page.locator("#view-start .choice:not(.is-demo):not(.is-register)").count() == 4
        page.click('button.choice[data-action="register"]')
        page.wait_for_selector("#view-register-kind:not([hidden])")
        assert page.text_content("#title") == "Which kind of data is your recipe for?"
        assert page.locator("#steps li").count() == 3
        page.click("#register-gridded")
        page.wait_for_selector("#view-register-gridded:not([hidden])")
        assert page.is_disabled("#register-save")

        page.fill("#r-gridded-variable", "nitrate")
        page.fill("#r-gridded-source", "MySat")
        page.fill("#r-gridded-source_info", "My nitrate")
        page.fill("#r-gridded-obs_path", NITRATE)
        page.wait_for_function("document.querySelector('#r-gridded-obs_variable').value === 'N3_n'")
        # what OceanVal filled in is red and bold
        red = "rgb(192, 57, 43)"
        for selector in ("#r-gridded-obs_variable", "#r-gridded-units"):
            assert page.locator(selector).evaluate("node => getComputedStyle(node).color") == red
            assert page.locator(selector).evaluate("node => getComputedStyle(node).fontWeight") == "700"
        assert page.input_value("#r-gridded-units") == "mmol N/m^3"
        assert "recipe={\"nitrate\": \"mysat\"}" in page.text_content("#r-gridded-preview")
        page.select_option("#r-gridded-climatology", "yes")
        page.check("#r-gridded-where-local")
        page.wait_for_function("!document.querySelector('#register-save').disabled")

        # Back keeps what was entered
        page.click("text=Back")
        page.wait_for_selector("#view-register-kind:not([hidden])")
        page.click("#register-gridded")
        page.wait_for_selector("#view-register-gridded:not([hidden])")
        assert page.input_value("#r-gridded-source") == "MySat"
        page.wait_for_function("!document.querySelector('#register-save').disabled")

        # a name that cannot be used
        page.fill("#r-gridded-source", "WOA23")
        page.wait_for_function("document.querySelector('#r-gridded-source-err').textContent.includes('own recipes')")
        assert page.is_disabled("#register-save")
        page.fill("#r-gridded-source", "MySat")
        page.wait_for_function("!document.querySelector('#register-save').disabled")

        page.click("#register-save")
        page.wait_for_selector("#register-list-gridded:not([hidden])")
        assert json.load(open(tmp_path / ".oceanvalrc"))["recipes"]["nitrate"]["mysat"]["units"] == "mmol N/m^3"
        assert page.input_value("#r-gridded-source") == ""
        assert page.is_checked("#r-gridded-where-local")

        # removing takes two clicks
        page.click("#register-list-gridded >> text=Remove")
        assert user_recipes.get("nitrate", "mysat", str(tmp_path)) is not None
        page.click("#register-list-gridded >> text=Click again to remove")
        page.wait_for_selector("#register-list-gridded", state="hidden")
        assert user_recipes.get("nitrate", "mysat", str(tmp_path)) is None

        # point data is on this machine only
        page.click("text=Back")
        page.click("#register-point")
        page.wait_for_selector("#view-register-point:not([hidden])")
        assert page.locator("#r-point-location").count() == 0
        page.fill("#r-point-obs_path", "/nowhere")
        page.wait_for_function("document.querySelector('#r-point-data-msg').innerText.includes('no directory')")
        assert failures == []
    finally:
        app.close()
