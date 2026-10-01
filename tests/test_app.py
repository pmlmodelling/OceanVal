"""The oceanval command: the questions OceanVal asks, the process it runs
matchup and validate in, the window's server and, where a browser can be
run, the window itself."""

import ast
import io
import json
import os
import pickle
import re
import subprocess
import sys
import textwrap
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser

import numpy as np
import pytest
import xarray as xr

import oceanval
from oceanval import app_child, prompts
from oceanval.app import App, Console, Run, check_setup, check_validate
from oceanval.app_child import QUESTION_MARKER
from oceanval.gridded import _ask_minutes, _ask_yes_no
from simulations import write_fvcom, write_simulation

SETUP_FORM = {
    "simdir": "sim",
    "ndown": "2",
    "domain": "global",
    "start": "2011",
    "end": "2012",
    "exclude": "",
    "require": "",
    "out_dir": "",
    "overwrite": False,
    "out": "matchup.py",
}

# what matchup sends with its question of whether the matchups are right
MATCHUPS = {
    "kind": "matchups",
    "sim_dir": "/sim",
    "years": [2011, 2012],
    "rows": [
        {
            "variable": "temperature",
            "title": "Temperature",
            "model_variable": "thetao",
            "pattern": "x_**_grid_T.nc",
            "observations": ["COBE2", "ICES (point)"],
            "files": 2,
        }
    ],
    "files": {"x_**_grid_T.nc": ["2011/x_2011_grid_T.nc", "2012/x_2012_grid_T.nc"]},
}


def write_matchups(directory):
    """What validate looks for from a finished matchup."""
    matchups = os.path.join(directory, "oceanval_matchups")
    os.makedirs(os.path.join(matchups, "gridded", "temperature"))
    open(
        os.path.join(
            matchups, "gridded", "temperature", "cobe2_temperature_surface.nc"
        ),
        "w",
    ).close()
    for name in ("short_titles.pkl", "variables_matched.pkl"):
        with open(os.path.join(matchups, name), "wb") as saved:
            pickle.dump({}, saved)


def units_read(app):
    """Wait for the units step, after the recipes window's, to have read the
    units."""
    wait_for(lambda: app.view == "units_table" and app.units_rows is not None)


def units_match(app):
    """Carry on from the units step without changing any conversion."""
    units_read(app)
    assert post(app, "/api/units_continue", {"conversions": {}, "confirmed": True})[0] == 200


def fill_required_recipe_years(page):
    red = "rgb(192, 57, 43)"
    for name in ("start", "end"):
        assert page.input_value(f"#s-{name}") == ""
        assert page.locator(f"#s-{name}").evaluate("node => node.required")
        label = page.locator(f"#s-{name}-label")
        assert label.evaluate("node => getComputedStyle(node).color") == red
        assert label.evaluate("node => getComputedStyle(node).fontWeight") == "700"
        assert page.is_visible(f"#s-{name}-required")
    assert page.is_disabled("#write")
    page.fill("#s-start", "2011")
    page.fill("#s-end", "2012")


def recipe_settings(app, **changes):
    settings = dict(app.recipes_page.form)
    settings.update(changes)
    if not settings.get("start"):
        settings["start"] = "2011"
    if not settings.get("end"):
        settings["end"] = "2012"
    return settings


def wait_for(condition, timeout=90):
    deadline = time.time() + timeout
    while not condition():
        if time.time() > deadline:
            raise AssertionError("timed out waiting")
        time.sleep(0.05)


def page_state(body):
    return json.loads(
        re.search(
            r'<script type="application/json" id="state">(.*?)</script>', body, re.S
        ).group(1)
    )


class TestQuestions:
    def test_a_terminal_is_asked_with_input(self, monkeypatch):
        monkeypatch.setattr(
            "builtins.input", lambda question: f"typed after {question}"
        )
        assert prompts.ask("Go? ", ("y", "n")) == "typed after Go? "

    def test_an_answerer_takes_the_questions(self):
        asked = []

        def answerer(question, choices, details):
            asked.append((question, choices, details))
            return "y"

        with prompts.answered_by(answerer):
            assert prompts.interactive()
            assert prompts.ask("Go? ", ["y", "n"]) == "y"
            assert prompts.ask("These? ", ["y", "n"], details={"kind": "x"}) == "y"
        assert asked == [
            ("Go? ", ("y", "n"), None),
            ("These? ", ("y", "n"), {"kind": "x"}),
        ]
        # and afterwards the terminal is asked again
        assert prompts._answerer is None

    def test_a_terminal_is_not_shown_the_details(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda question: question)
        assert prompts.ask("Go? ", ("y", "n"), details={"kind": "x"}) == "Go? "

    def test_whether_anyone_can_be_asked_follows_the_terminal(self, monkeypatch):
        monkeypatch.setattr("sys.stdin.isatty", lambda: False, raising=False)
        assert not prompts.interactive()
        monkeypatch.setattr("sys.stdin.isatty", lambda: True, raising=False)
        assert prompts.interactive()

    def test_the_retry_questions_go_through_it(self):
        # asked when observations could not be downloaded
        answers = iter(["maybe", "yes", "soon", "-1", "15"])
        asked = []

        def answerer(question, choices, details):
            asked.append(choices)
            return next(answers)

        with prompts.answered_by(answerer):
            assert _ask_yes_no("Try again? (y/n) ") is True
            assert _ask_minutes("How long? ") == 15
        assert asked == [("y", "n"), ("y", "n"), None, None, None]


class TestConsole:
    def test_the_page_reads_what_is_new(self):
        changes = []
        console = Console(lambda: changes.append(1))
        console.write("one\n")
        console.write("")
        console.write("two\n")
        first = console.since(0, None)
        console.write("three\n")
        later = console.since(first["last"], first["epoch"])

        assert (first["text"], first["reset"]) == ("one\ntwo\n", True)
        assert (later["text"], later["reset"]) == ("three\n", False)
        assert len(changes) == 3

    def test_clearing_starts_the_page_afresh(self):
        console = Console(lambda: None)
        console.write("old\n")
        seen = console.since(0, None)
        console.clear()
        console.write("new\n")
        update = console.since(seen["last"], seen["epoch"])

        assert (update["text"], update["reset"]) == ("new\n", True)

    def test_only_the_latest_output_is_kept(self, monkeypatch):
        monkeypatch.setattr(Console, "LIMIT", 10)
        console = Console(lambda: None)
        for number in range(5):
            console.write(f"line {number}\n")
        update = console.since(1, console.epoch)

        # the page had missed some, so is sent what is left
        assert (update["text"], update["reset"], update["dropped"]) == (
            "line 4\n",
            True,
            True,
        )


def run_script(tmp_path, source, answers=()):
    """Run a script as the window does, answering its questions in turn.
    Returns what it printed, the questions it asked and the Run."""
    script = tmp_path / "script.py"
    script.write_text(textwrap.dedent(source))
    console = Console(lambda: None)
    questions = []
    answers = iter(answers)
    finished = threading.Event()

    def ask(question, choices, respond, details):
        questions.append((question, choices))
        respond(next(answers))

    run = Run(
        ["script", str(script)], str(tmp_path), console, ask, lambda run: finished.set()
    )
    run.start()
    assert finished.wait(90)
    return console.since(0, None)["text"], questions, run


class TestRun:
    def test_output_and_questions_reach_the_window(self, tmp_path):
        output, questions, run = run_script(
            tmp_path,
            """
            from oceanval import prompts
            print("before")
            answer = prompts.ask("Carry on? (y/n) ", ("y", "n"))
            print(f"answered {answer}")
            print("\\rprogress 50%", end="", flush=True)
            print("\\rprogress 100%")
            """,
            answers=["y"],
        )

        assert questions == [("Carry on? (y/n) ", ["y", "n"])]
        assert "before\n" in output
        assert "answered y\n" in output
        # redrawn lines as the terminal would get them
        assert "\rprogress 50%\rprogress 100%\n" in output
        assert (run.returncode, run.stopped) == (0, False)

    def test_an_error_is_shown_and_fails_the_run(self, tmp_path):
        output, _, run = run_script(tmp_path, "raise RuntimeError('broken')")

        assert "RuntimeError: broken" in output
        assert run.returncode != 0

    def test_it_runs_in_the_directory_worked_in_with_this_oceanval(self, tmp_path):
        output, _, _ = run_script(
            tmp_path,
            "import os, oceanval; print(os.getcwd()); print(oceanval.__file__)",
        )

        assert f"{tmp_path}\n" in output
        # not whichever oceanval happens to be installed
        assert f"{oceanval.__file__}\n" in output

    def test_stopping(self, tmp_path):
        script = tmp_path / "script.py"
        script.write_text(
            "import time\nprint('started', flush=True)\ntime.sleep(120)\n"
        )
        console = Console(lambda: None)
        finished = threading.Event()
        run = Run(
            ["script", str(script)],
            str(tmp_path),
            console,
            None,
            lambda run: finished.set(),
        )
        run.start()
        wait_for(lambda: "started" in console.since(0, None)["text"])
        run.stop()

        assert finished.wait(20)
        assert run.stopped
        assert run.returncode != 0

    def test_a_question_can_arrive_in_pieces(self):
        console = Console(lambda: None)
        asked = []
        run = Run(
            [],
            ".",
            console,
            lambda question, choices, respond, details: asked.append((question, details)),
            None,
        )
        question = (
            QUESTION_MARKER
            + json.dumps({"question": "Go? ", "choices": None, "details": {"kind": "x"}})
            + "\n"
        )
        left = ""
        for character in "before" + question + "after":
            left = run._take(left + character)

        assert asked == [("Go? ", {"kind": "x"})]
        assert console.since(0, None)["text"] + left == "beforeafter"


class TestChildProcess:
    def test_questions_are_written_out_and_the_answer_read_back(
        self, monkeypatch, capfd
    ):
        monkeypatch.setattr("sys.stdin", io.StringIO("n\n"))
        answer = app_child._ask_the_window("Go? (y/n) ", ["y", "n"])

        assert answer == "n"
        assert capfd.readouterr().out == (
            QUESTION_MARKER
            + json.dumps({"question": "Go? (y/n) ", "choices": ["y", "n"]})
            + "\n"
        )
        # with nothing left to read, as input() does
        monkeypatch.setattr("sys.stdin", io.StringIO(""))
        with pytest.raises(EOFError):
            app_child._ask_the_window("Go? ", None)

    def test_details_go_with_the_question(self, monkeypatch, capfd):
        monkeypatch.setattr("sys.stdin", io.StringIO("y\n"))
        app_child._ask_the_window("These? ", ["y", "n"], {"kind": "matchups"})

        assert capfd.readouterr().out == (
            QUESTION_MARKER
            + json.dumps(
                {"question": "These? ", "choices": ["y", "n"], "details": {"kind": "matchups"}}
            )
            + "\n"
        )

    def test_validate_is_given_its_arguments(self, monkeypatch):
        called = []
        monkeypatch.setattr(
            oceanval, "validate", lambda **arguments: called.append(arguments)
        )
        # main replaces it where no browser can be opened
        monkeypatch.setattr(webbrowser, "open", webbrowser.open)
        app_child.main(["validate", json.dumps({"data_dir": "/matchups", "pdf": True})])

        assert called == [{"data_dir": "/matchups", "pdf": True}]

    def test_without_a_display_the_report_is_not_opened(self, monkeypatch, capsys):
        # webbrowser would fall back on a text browser, which would wait for
        # keys the window never sends
        monkeypatch.setattr(sys, "platform", "linux")
        for name in ("DISPLAY", "WAYLAND_DISPLAY", "BROWSER"):
            monkeypatch.delenv(name, raising=False)
        monkeypatch.setattr(webbrowser, "open", lambda url: pytest.fail("opened"))
        monkeypatch.setattr(
            oceanval,
            "validate",
            lambda **arguments: webbrowser.open("file:///run/report.html"),
        )
        app_child.main(["validate", "{}"])

        assert "file:///run/report.html" in capsys.readouterr().out


class TestSetupChecks:
    def test_the_arguments(self, tmp_path):
        (tmp_path / "sim").mkdir()
        arguments, errors = check_setup(
            dict(SETUP_FORM, domain="nwes", out="run/m.py"), str(tmp_path)
        )

        assert errors == {}
        assert arguments == {
            "simdir": str(tmp_path / "sim"),
            "ndown": 2,
            "domain": "nwes",
            "start": 2011,
            "end": 2012,
            "exclude": None,
            "require": None,
            "out_dir": str(tmp_path),
            "overwrite": True,
            "out": str(tmp_path / "run" / "m.py"),
        }

    def test_the_output_directory(self, tmp_path):
        (tmp_path / "sim").mkdir()
        (tmp_path / "notes.txt").write_text("")

        def check(out_dir):
            return check_setup(dict(SETUP_FORM, out_dir=out_dir), str(tmp_path))

        # relative to the directory worked in, and it need not be there yet
        assert check("results")[0]["out_dir"] == str(tmp_path / "results")
        assert check(str(tmp_path / "elsewhere"))[0]["out_dir"] == str(tmp_path / "elsewhere")
        assert check("notes.txt")[1] == {"out_dir": "This is a file, not a directory."}

    def test_overwrite_is_only_used_when_matchups_already_exist(self, tmp_path):
        (tmp_path / "sim").mkdir()
        (tmp_path / "old" / "oceanval_matchups").mkdir(parents=True)

        keep, keep_errors = check_setup(dict(SETUP_FORM, out_dir="old", overwrite=False), str(tmp_path))
        replace, replace_errors = check_setup(dict(SETUP_FORM, out_dir="old", overwrite=True), str(tmp_path))
        clean, clean_errors = check_setup(dict(SETUP_FORM, out_dir="new", overwrite=False), str(tmp_path))

        assert not keep_errors and not replace_errors and not clean_errors
        assert (keep["overwrite"], replace["overwrite"], clean["overwrite"]) == (
            False,
            True,
            True,
        )

    def test_the_file_filters_are_words(self, tmp_path):
        (tmp_path / "sim").mkdir()
        form = dict(SETUP_FORM, exclude=" ptrc  5d ", require="grid_T")
        arguments = check_setup(form, str(tmp_path))[0]

        assert (arguments["exclude"], arguments["require"]) == (
            ["ptrc", "5d"],
            ["grid_T"],
        )

    @pytest.mark.parametrize(
        "changes, error",
        [
            ({"simdir": ""}, "simdir"),
            ({"simdir": "nowhere"}, "simdir"),
            ({"ndown": "-1"}, "ndown"),
            ({"ndown": "two"}, "ndown"),
            ({"domain": "arctic"}, "domain"),
            ({"start": "x"}, "start"),
            ({"end": "2010"}, "end"),
            ({"out": ""}, "out"),
            ({"out": "sim"}, "out"),
        ],
    )
    def test_boxes_that_cannot_be_used(self, tmp_path, changes, error):
        (tmp_path / "sim").mkdir()
        assert list(check_setup(dict(SETUP_FORM, **changes), str(tmp_path))[1]) == [
            error
        ]


class TestBrowsing:
    """The folder browser, and the folders suggested as a path is typed."""

    def test_a_directory(self, tmp_path):
        for name in ("b", "A", "c", ".hidden", "oceanval_matchups"):
            (tmp_path / "run" / name).mkdir(parents=True)
        for name in ("x.nc", "a.nc", "notes.txt"):
            (tmp_path / "run" / name).write_text("")
        found = App(cwd=str(tmp_path)).browse("run")

        assert (found["path"], found["shown"], found["exact"]) == (
            str(tmp_path / "run"),
            "run",
            True,
        )
        assert found["parent"] == str(tmp_path)
        # hidden folders are left out
        assert [folder["name"] for folder in found["folders"]] == [
            "A",
            "b",
            "c",
            "oceanval_matchups",
        ]
        assert found["folders"][0]["path"] == str(tmp_path / "run" / "A")
        assert (found["nc_files"], found["example"]) == (2, "a.nc")
        assert found["has_matchups"]
        assert found["error"] is None

    def test_the_working_directory_to_start_with(self, tmp_path):
        found = App(cwd=str(tmp_path)).browse("")

        assert (found["path"], found["shown"], found["exact"]) == (
            str(tmp_path),
            ".",
            True,
        )
        assert found["places"][0] == {
            "label": "Working directory",
            "path": str(tmp_path),
        }

    def test_what_is_not_a_directory_opens_the_one_above_it(self, tmp_path):
        (tmp_path / "run").mkdir()
        (tmp_path / "run" / "x.nc").write_text("")
        app = App(cwd=str(tmp_path))

        # typed only in part
        assert app.browse("run/2011/0")["path"] == str(tmp_path / "run")
        assert not app.browse("run/2011/0")["exact"]
        assert app.browse("run/x.nc")["path"] == str(tmp_path / "run")

    def test_a_random_directory_of_files(self, app, tmp_path):
        for year in ("2001", "2002"):
            (tmp_path / "sim" / year).mkdir(parents=True)
            for name in ("a_grid_T.nc", "a_restart.nc", "notes.txt"):
                (tmp_path / "sim" / year / name).write_text("")

        found = app.sample_files("sim", "1")
        assert found["directory"] == "found"
        assert found["path"] in ("sim/2001", "sim/2002")
        assert found["directories"] == 2
        # every netCDF file, restart files too, and nothing else
        assert found["files"] == ["a_grid_T.nc", "a_restart.nc"]
        # asking again for another directory
        other = app.sample_files("sim", "1", found["path"])
        assert other["path"] != found["path"]

        assert app.sample_files("", "1")["directory"] == "empty"
        assert app.sample_files("nowhere", "1")["directory"] == "missing"
        assert app.sample_files("sim", "x")["ndown"] is None
        assert app.sample_files("sim", "0")["files"] == []
        assert get_json(app, "/api/files", simdir="sim", ndown="1")[1]["directories"] == 2

    def test_the_top_of_the_file_system(self, tmp_path):
        found = App(cwd=str(tmp_path)).browse("/")
        assert (found["path"], found["parent"]) == ("/", None)

    def test_elsewhere_is_shown_in_full(self, tmp_path):
        (tmp_path / "work").mkdir()
        (tmp_path / "data").mkdir()
        found = App(cwd=str(tmp_path / "work")).browse("../data")
        assert found["shown"] == str(tmp_path / "data")

    @pytest.mark.skipif(os.geteuid() == 0, reason="root can open anything")
    def test_a_directory_that_cannot_be_opened(self, tmp_path):
        locked = tmp_path / "locked"
        locked.mkdir()
        locked.chmod(0)
        try:
            found = App(cwd=str(tmp_path)).browse("locked")
        finally:
            locked.chmod(0o755)

        assert found["error"] == "You do not have permission to open this directory."
        # so the browser can still go back up
        assert found["parent"] == str(tmp_path)


class TestValidateChecks:
    def test_the_matchups_must_be_there(self, tmp_path):
        errors = check_validate({}, str(tmp_path))[1]
        assert list(errors) == ["data_dir"]
        assert "No matchups found" in errors["data_dir"]

    def test_the_arguments(self, tmp_path):
        write_matchups(tmp_path)
        form = {
            "out_dir": "report",
            "lon_min": "-20",
            "lon_max": "10",
            "lat_min": "40",
            "lat_max": "65",
            "subregions": "global",
            "pdf": True,
            "zip": True,
        }
        arguments, errors = check_validate(form, str(tmp_path))

        assert errors == {}
        assert arguments == {
            "data_dir": str(tmp_path),
            "out_dir": str(tmp_path / "report"),
            "lon_lim": [-20, 10],
            "lat_lim": [40, 65],
            "subregions": "global",
            "pdf": True,
            "zip": True,
        }

    def test_a_regions_file_is_found_in_the_directory_worked_in(self, tmp_path):
        write_matchups(tmp_path)
        form = {"subregions": "file", "subregions_file": "regions.nc"}

        assert check_validate(form, str(tmp_path))[1] == {
            "subregions_file": "There is no file at this path."
        }


def _request(app, route, data=None, token=None, **params):
    token = app.token if token is None else token
    url = f"http://127.0.0.1:{app.port}{route}"
    headers = {}
    if data is None:
        url += "?" + urllib.parse.urlencode(dict(params, token=token))
    else:
        data = json.dumps(data).encode()
        headers = {"Content-Type": "application/json", "X-OceanVal-Token": token}
    request = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status, response.read().decode()
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode()


def get(app, route, **params):
    return _request(app, route, **params)


def get_json(app, route, **params):
    status, body = _request(app, route, **params)
    return status, json.loads(body)


def post(app, route, body=None, token=None):
    status, reply = _request(app, route, data=body or {}, token=token)
    return status, json.loads(reply)


@pytest.fixture
def app(tmp_path):
    app = App(cwd=str(tmp_path))
    app.start()
    yield app
    app.close()


@pytest.fixture
def runs(app, monkeypatch):
    """The runs the app starts, which are recorded rather than started."""
    started = []
    monkeypatch.setattr(
        app, "start_run", lambda args, label: started.append((args, label))
    )
    return started


class TestServer:
    def test_everything_needs_the_token(self, app):
        assert get(app, "/", token="wrong")[0] == 403
        assert get(app, "/api/state", token="wrong")[0] == 403
        assert get(app, "/api/browse", token="wrong", path="/")[0] == 403
        assert post(app, "/api/quit", token="wrong")[0] == 403
        assert not app.closed.is_set()

    def test_the_page(self, app):
        status, body = get(app, "/")
        state = page_state(body)

        assert status == 200
        assert (state["token"], state["state"]["view"]) == (app.token, "start")
        # the shared stylesheet and scripts are inlined
        assert "__OCEANVAL_" not in body

    def test_choosing(self, app):
        assert post(app, "/api/choose", {"action": "everything"})[0] == 409
        assert post(app, "/api/choose", {"action": "matchup"})[0] == 200
        assert app.view == "setup"
        # only at the start
        assert post(app, "/api/choose", {"action": "validate"})[0] == 409
        assert post(app, "/api/back")[0] == 200
        assert app.view == "start"

    def test_the_state_waits_for_a_change(self, app):
        _, state = get_json(app, "/api/state")
        threading.Timer(0.5, lambda: app.choose("validate")).start()
        started = time.time()
        _, later = get_json(app, "/api/state", version=state["version"])

        assert later["view"] == "validate"
        assert 0.3 < time.time() - started < 15

    def test_the_live_check(self, app, tmp_path):
        write_simulation(tmp_path / "sim")
        (tmp_path / "matchup.py").write_text("")

        _, found = get_json(
            app, "/api/probe", simdir="sim", ndown="2", out="matchup.py"
        )
        assert (found["directory"], found["ndown"], found["files"]) == ("found", 2, 2)
        assert found["years"] == [2011, 2012]
        assert found["out_exists"]
        # with no files where it was told to look, it says where there are some
        _, found = get_json(app, "/api/probe", simdir="sim", ndown="1", out="")
        assert found["files"] == 0
        assert found["suggestion"] == {"ndown": 2, "files": 2, "years": [2011, 2012]}
        _, found = get_json(app, "/api/probe", simdir="sim", ndown="", out="")
        assert found["suggestion"]["ndown"] == 2
        _, found = get_json(app, "/api/probe", simdir="nowhere", ndown="2", out="")
        assert found["directory"] == "missing"

    def test_the_live_check_of_the_output_directory(self, app, tmp_path):
        (tmp_path / "old" / "oceanval_matchups").mkdir(parents=True)
        (tmp_path / "notes.txt").write_text("")

        def probe(out_dir):
            found = get_json(
                app, "/api/probe", simdir="", ndown="", out="", out_dir=out_dir
            )[1]
            return found["out_dir"], found["out_dir_has_matchups"]

        # empty is the directory worked in
        assert probe("") == ("found", False)
        assert probe("old") == ("found", True)
        assert probe("new") == ("missing", False)
        assert probe("notes.txt") == ("file", False)

    def test_the_live_check_counts_what_passes_the_file_filters(self, app, tmp_path):
        write_simulation(tmp_path / "sim", tracers=True)

        def probe(**filters):
            return get_json(
                app, "/api/probe", simdir="sim", ndown="2", out="", **filters
            )[1]

        assert (probe()["files"], probe()["all_files"]) == (4, 4)
        found = probe(exclude="ptrc")
        assert (found["files"], found["all_files"]) == (2, 4)
        assert found["years"] == [2011, 2012]
        assert probe(require="ptrc grid")["files"] == 0
        # the depth is right, so it is the filters that need changing
        found = probe(require="nothing_like_this")
        assert (found["files"], found["all_files"], found["suggestion"]) == (0, 4, None)

    def test_browsing(self, app, tmp_path):
        (tmp_path / "sim").mkdir()
        status, found = get_json(app, "/api/browse", path="")

        assert status == 200
        assert [folder["name"] for folder in found["folders"]] == ["sim"]

    def test_setup_problems_are_sent_back(self, app, runs):
        app.choose("matchup")
        status, reply = post(app, "/api/setup", {"form": {"simdir": "nowhere"}})

        assert status == 400
        assert set(reply["errors"]) == {"simdir", "ndown", "start", "end"}
        assert app.view == "setup"

    @pytest.mark.parametrize("action", ["matchup", "matchup_validate"])
    def test_matching_up(self, app, tmp_path, runs, action):
        """create_recipes reads the simulation, its window is the recipes
        step, and writing the script there starts it."""
        write_simulation(tmp_path / "sim")
        app.choose(action)
        assert post(app, "/api/setup", {"form": SETUP_FORM})[0] == 200
        # whether there is data of your own comes before the recipes
        assert app.view == "own_data"
        assert post(app, "/api/own_data", {"answer": False})[0] == 200
        wait_for(lambda: app.view == "recipes")

        status, body = get(app, "/recipes/")
        state = page_state(body)
        assert status == 200
        assert state["context"]["app"] == {"action": action, "own_vertical": False}
        # its requests are answered by the app's own server
        assert state["token"] == app.token
        # the output directory was chosen with the simulation
        assert state["settings"]["out_dir"] == ""
        assert (state["settings"]["start"], state["settings"]["end"]) == ("", "")

        rows = [
            {
                "variable": "temperature",
                "model_variable": "thetao",
                "selected": ["cobe2"],
            }
        ]
        status, reply = post(app, "/recipes/write", {"rows": rows})
        assert status == 400
        assert {"start", "end"} <= set(reply["setting_errors"])
        assert post(app, "/recipes/write", {"rows": rows, "settings": recipe_settings(app)})[0] == 200
        units_match(app)
        wait_for(lambda: runs)
        script = str(tmp_path / "matchup.py")
        text = open(script).read()

        assert runs == [(["script", script], "python matchup.py")]
        assert '\noceanval.add_gridded_comparison(\n    name="temperature",' in text
        if action == "matchup":
            # the report is left for later
            assert "\n# oceanval.validate()\n" in text
            assert "\noceanval.validate(" not in text
        else:
            assert "\noceanval.validate()\n" in text
        assert app.results_dir == str(tmp_path)
        # the recipes step is over, so its link leads back to the app
        assert 'id="view-start"' in get(app, "/recipes/")[1]

    def test_the_output_directory_reaches_the_script(self, app, tmp_path, runs):
        write_simulation(tmp_path / "sim")
        app.choose("matchup_validate")
        post(app, "/api/setup", {"form": dict(SETUP_FORM, out_dir="results")})
        post(app, "/api/own_data", {"answer": False})
        wait_for(lambda: app.view == "recipes")
        results = str(tmp_path / "results")
        # chosen with the simulation, so the recipes step does not ask again
        assert app.recipes_page.form["out_dir"] == results

        rows = [{"variable": "temperature", "model_variable": "thetao", "selected": ["cobe2"]}]
        assert post(app, "/recipes/write", {"rows": rows, "settings": recipe_settings(app)})[0] == 200
        units_match(app)
        wait_for(lambda: runs)
        text = open(tmp_path / "matchup.py").read()

        assert f'    sim_dir="{tmp_path / "sim"}",\n' in text
        assert f'    out_dir="{results}",\n' in text
        assert f'oceanval.validate(\n    data_dir="{results}",\n    out_dir="{results}",\n)' in text
        assert app.results_dir == results

    def test_the_recipes_step_always_asks_and_needs_a_thickness(self, app, tmp_path, runs):
        write_simulation(tmp_path / "sim")
        app.choose("matchup")
        post(app, "/api/setup", {"form": SETUP_FORM})
        post(app, "/api/own_data", {"answer": False})
        wait_for(lambda: app.view == "recipes")
        rows = [
            {
                "variable": "temperature",
                "model_variable": "thetao",
                "selected": ["nsbc"],
                "gridded": {"nsbc": {"start": "", "end": "", "vertical": True}},
            }
        ]
        settings = recipe_settings(app, ask=False)

        status, reply = post(app, "/recipes/write", {"rows": rows, "settings": settings})
        assert status == 400
        assert "a thickness is needed" in reply["setting_errors"]["thickness"]
        assert not (tmp_path / "matchup.py").exists()

        settings["thickness"] = "z_level"
        assert post(app, "/recipes/write", {"rows": rows, "settings": settings})[0] == 200
        units_match(app)
        wait_for(lambda: runs)
        text = open(tmp_path / "matchup.py").read()
        # asking is matchup's default, so it is not written
        assert "    ask=" not in text
        assert '    thickness="z_level",\n' in text

    def test_own_data_through_the_water_column_needs_a_thickness(self, app, tmp_path, runs):
        write_simulation(tmp_path / "sim")
        app.choose("matchup")
        post(app, "/api/setup", {"form": SETUP_FORM})
        app.own_data["point"].append(
            {"name": "cruise", "source": "mine", "model_variable": "thetao",
             "obs_path": "points", "vertical": True}
        )
        post(app, "/api/own_data", {"answer": True})
        post(app, "/api/own_next")
        post(app, "/api/own_next")
        wait_for(lambda: app.view == "recipes")

        assert app.recipes_page.context["app"]["own_vertical"] is True
        status, reply = post(app, "/recipes/write", {"rows": [], "settings": recipe_settings(app)})
        assert status == 400
        assert "thickness" in reply["setting_errors"]

    def choose_recipes(self, app, tmp_path, own_gridded=None, own_point=None, ices=False):
        """Get to the units step with temperature (COBE-SST 2) and nitrate
        (WOA23) chosen, with temperature from ICES as well if ices, and the
        user's own gridded and point data if given."""
        write_simulation(tmp_path / "sim", tracers=True)
        app.choose("matchup")
        post(app, "/api/setup", {"form": SETUP_FORM})
        if own_gridded:
            app.own_data["gridded"].append(own_gridded)
        if own_point:
            app.own_data["point"].append(own_point)
        own = bool(own_gridded or own_point)
        post(app, "/api/own_data", {"answer": own})
        if own:
            post(app, "/api/own_next")
            post(app, "/api/own_next")
        wait_for(lambda: app.view == "recipes")
        rows = [
            {
                "variable": "temperature",
                "model_variable": "thetao",
                "selected": ["cobe2", "ices"] if ices else ["cobe2"],
            },
            {"variable": "nitrate", "model_variable": "N3_n", "selected": ["woa23"]},
        ]
        assert post(app, "/recipes/write", {"rows": rows, "settings": recipe_settings(app)})[0] == 200
        units_read(app)

    def test_the_units_are_shown_after_the_recipes(self, app, tmp_path, runs):
        self.choose_recipes(app, tmp_path)
        _, state = get_json(app, "/api/state")

        assert state["view"] == "units_table"
        # the script is already written, and nothing runs until it is carried on from
        assert (tmp_path / "matchup.py").exists()
        assert runs == []
        # there is no going back to a recipes window that has been used
        assert post(app, "/api/back")[0] == 409

        # nothing is converted that the page does not send
        assert post(app, "/api/units_continue", {"conversions": {}, "confirmed": True})[0] == 200
        wait_for(lambda: runs)
        assert "obs_multiplier" not in open(tmp_path / "matchup.py").read()
        assert app.view == "running"

    def test_nothing_carries_on_while_the_units_are_read(self, app):
        app.view = "units_table"

        status, reply = post(app, "/api/units_continue", {"conversions": {}, "confirmed": True})

        assert status == 409
        assert "still being read" in reply["error"]

    @pytest.mark.parametrize("confirmed", [None, False, "true", 1])
    def test_the_units_always_have_to_be_confirmed(self, app, tmp_path, runs, confirmed):
        """Not just by a button that is disabled: only a confirmation of true
        carries on, whatever conversions are sent."""
        self.choose_recipes(app, tmp_path)
        sent = {"conversions": {}}
        if confirmed is not None:
            sent["confirmed"] = confirmed

        status, reply = post(app, "/api/units_continue", sent)

        assert status == 400
        assert "Confirm the units" in reply["error"]
        assert app.view == "units_table"
        assert runs == []
        # and it can still be confirmed
        assert post(app, "/api/units_continue", {"conversions": {}, "confirmed": True})[0] == 200
        wait_for(lambda: runs)

    def test_the_units_of_every_gridded_matchup_are_listed(self, app, tmp_path, runs):
        obs = tmp_path / "obs.nc"
        xr.Dataset(
            {"chl_obs": (("y", "x"), np.ones((2, 2)), {"units": "mg/m3"})}
        ).to_netcdf(obs)
        own = {
            "name": "chl",
            "source": "mine",
            "model_variable": "thetao+N3_n",
            "obs_path": str(obs),
            "obs_variable": "chl_obs",
            "obs_multiplier": 5,
        }
        self.choose_recipes(app, tmp_path, own)

        _, state = get_json(app, "/api/state")
        rows = {row["key"]: row for row in state["units"]["rows"]}

        assert state["view"] == "units_table"
        assert list(rows) == [
            "recipe:nitrate:woa23",
            "recipe:temperature:cobe2",
            "own:0",
        ]
        nitrate, temperature, mine = rows.values()
        assert nitrate["model"] == {
            "variable": "N3_n",
            "parts": [{"name": "N3_n", "units": "mmol N m-3"}],
        }
        assert (nitrate["obs_variable"], nitrate["obs_units"]) == (
            "n_an",
            "micromoles_per_kilogram",
        )
        assert temperature["model"]["parts"] == [{"name": "thetao", "units": "degC"}]
        assert (temperature["obs_variable"], temperature["obs_units"]) == ("sst", "degC")
        # a sum is listed by its parts, and the file's own units are read
        assert [part["name"] for part in mine["model"]["parts"]] == ["thetao", "N3_n"]
        assert (mine["obs_variable"], mine["obs_units"]) == ("chl_obs", "mg/m3")
        assert (mine["obs_multiplier"], mine["obs_adder"]) == (5, 0)
        # what OceanVal makes of each: WOA23 is per kilogram, the model per volume
        assert (nitrate["check"]["status"], nitrate["check"]["multiplier"]) == (
            "convert",
            1.025,
        )
        assert "1025 kg/m³" in nitrate["check"]["note"]
        assert temperature["check"]["status"] == "same"
        assert mine["check"]["status"] == "unknown"
        assert "different units" in mine["check"]["note"]
        # which the page fills in: the conversion already chosen is unchanged
        assert (nitrate["obs_multiplier"], nitrate["obs_adder"]) == (1, 0)

    def test_ices_and_own_point_data_are_listed_too(self, app, tmp_path, runs):
        own = {
            "name": "cruise",
            "source": "mine",
            "model_variable": "thetao",
            "obs_path": "points",
            "obs_adder": 3,
        }
        self.choose_recipes(app, tmp_path, own_point=own, ices=True)

        _, state = get_json(app, "/api/state")
        rows = {row["key"]: row for row in state["units"]["rows"]}

        assert list(rows) == [
            "recipe:nitrate:woa23",
            "recipe:temperature:cobe2",
            "point:temperature:ices",
            "ownpoint:0",
        ]
        # the page shows gridded datasets and point datasets in sections of their own
        assert {key: row["kind"] for key, row in rows.items()} == {
            "recipe:nitrate:woa23": "gridded",
            "recipe:temperature:cobe2": "gridded",
            "point:temperature:ices": "point",
            "ownpoint:0": "point",
        }
        ices = rows["point:temperature:ices"]
        assert ices["model"]["parts"] == [{"name": "thetao", "units": "degC"}]
        assert (ices["obs_variable"], ices["obs_units"]) == ("TEMPPR01", "\u00b0C")
        assert ices["check"]["status"] == "same"
        mine = rows["ownpoint:0"]
        assert mine["obs_units"] is None and "no units" in mine["obs_note"]
        assert (mine["obs_multiplier"], mine["obs_adder"]) == (1, 3)
        assert mine["check"]["status"] == "unknown"

    def test_point_conversions_are_written_into_the_script(self, app, tmp_path, runs):
        own = {
            "name": "cruise",
            "source": "mine",
            "model_variable": "thetao",
            "obs_path": "points",
        }
        self.choose_recipes(app, tmp_path, own_point=own, ices=True)
        conversions = {
            "point:temperature:ices": {"multiplier": "", "adder": "2"},
            "ownpoint:0": {"multiplier": "10", "adder": ""},
        }

        assert post(app, "/api/units_continue", {"conversions": conversions, "confirmed": True})[0] == 200
        wait_for(lambda: runs)
        text = open(tmp_path / "matchup.py").read()

        ices = text[text.index("add_point_comparison(\n    name=\"temperature\"") :].split("\n)\n")[0]
        assert "    obs_adder=2,\n" in ices
        cruise = text[text.index('name="cruise"') :].split("\n)\n")[0]
        assert "    obs_multiplier=10," in cruise
        ast.parse(text)

    def test_a_conversion_is_written_into_the_script(self, app, tmp_path, runs):
        self.choose_recipes(app, tmp_path)
        conversions = {
            "recipe:nitrate:woa23": {"multiplier": "0.001", "adder": " "},
            "recipe:temperature:cobe2": {"multiplier": "", "adder": "-273.15"},
        }

        assert post(app, "/api/units_continue", {"conversions": conversions, "confirmed": True})[0] == 200
        wait_for(lambda: runs)
        text = open(tmp_path / "matchup.py").read()

        nitrate = text[text.index('name="nitrate"') :]
        assert "    obs_multiplier=0.001,\n" in nitrate.split("\n)\n")[0]
        assert "obs_adder" not in nitrate.split("\n)\n")[0]
        temperature = text[text.index('name="temperature"') :].split("\n)\n")[0]
        assert "    obs_adder=-273.15,\n" in temperature
        ast.parse(text)

    def test_a_conversion_of_your_own_data_replaces_its_own(self, app, tmp_path, runs):
        own = {
            "name": "chl",
            "source": "mine",
            "model_variable": "thetao",
            "obs_path": "obs.nc",
            "obs_variable": "chl_obs",
            "obs_multiplier": 5,
        }
        self.choose_recipes(app, tmp_path, own)

        # blank puts it back to the default, which is left out
        conversions = {"own:0": {"multiplier": "", "adder": "2"}}
        assert post(app, "/api/units_continue", {"conversions": conversions, "confirmed": True})[0] == 200
        wait_for(lambda: runs)
        text = open(tmp_path / "matchup.py").read()
        call = text[text.index('name="chl"') :].split("\n)\n")[0]

        assert "obs_multiplier" not in call
        assert "    obs_adder=2," in call

    def test_conversions_that_cannot_be_used_are_sent_back(self, app, tmp_path, runs):
        self.choose_recipes(app, tmp_path)

        for conversions in (
            {"recipe:nitrate:woa23": {"multiplier": "x", "adder": ""}},
            {"recipe:nitrate:woa23": {"multiplier": "0", "adder": ""}},
            {"recipe:nitrate:woa23": {"multiplier": "", "adder": "inf"}},
            {"recipe:salinity:woa23": {"multiplier": "2", "adder": ""}},
        ):
            status, reply = post(app, "/api/units_continue", {"conversions": conversions, "confirmed": True})
            assert status == 400
            assert set(reply["errors"]) == set(conversions)
        assert app.view == "units_table"
        assert runs == []

    def test_own_data_is_added_one_at_a_time(self, app, tmp_path, runs):
        """Yes leads to the point data step and then the gridded data step,
        each adding entries until it is moved on from, and the calls are
        written into the script."""
        write_simulation(tmp_path / "sim")
        points = tmp_path / "points"
        points.mkdir()
        (points / "obs.csv").write_text("lon,lat,observation\n1,2,3\n")
        app.choose("matchup")
        post(app, "/api/setup", {"form": SETUP_FORM})

        assert post(app, "/api/own_data", {"answer": True})[0] == 200
        assert app.view == "point_data"
        # the wrong kind for the step is not taken
        assert post(app, "/api/own_add", {"kind": "gridded", "form": {}})[0] == 409

        status, reply = post(app, "/api/own_add", {"kind": "point", "form": {"name": "chl"}})
        assert status == 400
        assert set(reply["errors"]) == {"source", "model_variable", "obs_path"}
        form = {
            "name": "chl",
            "source": "mycruise",
            "model_variable": "thetao",
            "obs_path": "points",
            "vertical": False,
            "obs_multiplier": "2",
        }
        assert post(app, "/api/own_add", {"kind": "point", "form": form})[0] == 200
        assert app.own_data["point"] == [
            {
                "name": "chl",
                "source": "mycruise",
                "model_variable": "thetao",
                "obs_path": str(points),
                "obs_multiplier": 2,
            }
        ]
        # a second one can be added and taken off again
        assert post(app, "/api/own_add", {"kind": "point", "form": dict(form, source="other")})[0] == 200
        assert post(app, "/api/own_remove", {"kind": "point", "index": 1})[0] == 200
        assert post(app, "/api/own_remove", {"kind": "point", "index": 5})[0] == 409
        assert len(app.own_data["point"]) == 1
        _, state = get_json(app, "/api/state")
        assert state["own"]["entries"]["point"][0]["name"] == "chl"

        # Back and forward keep what was added
        assert post(app, "/api/own_next")[0] == 200
        assert app.view == "gridded_data"
        assert post(app, "/api/back")[0] == 200
        assert app.view == "point_data"
        post(app, "/api/own_next")
        assert post(app, "/api/own_next")[0] == 200
        wait_for(lambda: app.view == "recipes")
        post(app, "/recipes/write", {"rows": [], "settings": recipe_settings(app)})
        units_match(app)
        wait_for(lambda: runs)

        text = open(tmp_path / "matchup.py").read()
        assert (
            '\noceanval.add_point_comparison(\n    name="chl",\n    source="mycruise",\n'
            in text
        )
        assert text.index("add_point_comparison") < text.index("oceanval.matchup(")

    def test_skipping_own_data_leaves_it_out_of_the_script(self, app, tmp_path, runs):
        write_simulation(tmp_path / "sim")
        app.choose("matchup")
        post(app, "/api/setup", {"form": SETUP_FORM})
        post(app, "/api/own_data", {"answer": True})
        post(app, "/api/own_next")
        post(app, "/api/own_next")
        wait_for(lambda: app.view == "recipes")
        post(app, "/recipes/write", {"rows": [], "settings": recipe_settings(app)})
        units_match(app)
        wait_for(lambda: runs)

        assert "Your own observations" not in open(tmp_path / "matchup.py").read()

    def test_back_through_the_own_data_steps(self, app, tmp_path, runs):
        write_simulation(tmp_path / "sim")
        app.choose("matchup")
        post(app, "/api/setup", {"form": SETUP_FORM})
        assert app.view == "own_data"
        assert post(app, "/api/own_next")[0] == 409
        post(app, "/api/own_data", {"answer": True})
        post(app, "/api/own_next")
        assert app.view == "gridded_data"
        for view in ("point_data", "own_data", "setup"):
            assert post(app, "/api/back")[0] == 200
            assert app.view == view

    def test_the_file_filters_reach_the_script(self, app, tmp_path, runs):
        write_simulation(tmp_path / "sim", tracers=True)
        app.choose("matchup")
        post(app, "/api/setup", {"form": dict(SETUP_FORM, exclude="ptrc")})
        post(app, "/api/own_data", {"answer": False})
        wait_for(lambda: app.view == "recipes")
        page = app.recipes_page

        # the recipes step starts with them, and hides them
        assert page.context["exclude"] == ["ptrc"]
        assert page.form["exclude"] == "ptrc"
        # nitrate is only in the files they leave out
        found = {row["variable"]: row["model_variable"] for row in page.rows}
        assert (found["nitrate"], found["temperature"]) == ("", "thetao")

        rows = [
            {
                "variable": "temperature",
                "model_variable": "thetao",
                "selected": ["cobe2"],
            }
        ]
        post(app, "/recipes/write", {"rows": rows, "settings": recipe_settings(app, **page.form)})
        units_match(app)
        wait_for(lambda: runs)
        script = open(tmp_path / "matchup.py").read()
        assert '    n_dirs_down=2,\n    exclude=["ptrc"],\n)' in script

    def test_back_from_the_recipes_step(self, app, tmp_path, runs):
        write_simulation(tmp_path / "sim")
        app.choose("matchup_validate")
        post(app, "/api/setup", {"form": SETUP_FORM})
        post(app, "/api/own_data", {"answer": False})
        wait_for(lambda: app.view == "recipes")

        assert post(app, "/recipes/cancel")[0] == 200
        # back to where own data was asked about
        wait_for(lambda: app.view == "own_data")
        assert app.setup_form == SETUP_FORM
        assert runs == []
        assert not (tmp_path / "matchup.py").exists()

    def test_what_create_recipes_finds_wrong_is_shown(self, app, tmp_path, runs):
        (tmp_path / "empty").mkdir()
        app.choose("matchup")
        post(app, "/api/setup", {"form": dict(SETUP_FORM, simdir="empty")})
        post(app, "/api/own_data", {"answer": False})
        wait_for(lambda: app.view == "setup" and app.setup_error)

        assert "Check the ndown argument" in app.setup_error

    def test_the_fvcom_question_is_asked_in_the_window(self, app, tmp_path, runs):
        write_fvcom(tmp_path / "fvcom")
        app.choose("matchup")
        post(
            app, "/api/setup", {"form": dict(SETUP_FORM, simdir="fvcom", start="2012")}
        )
        post(app, "/api/own_data", {"answer": False})
        wait_for(lambda: app.question is not None)
        _, state = get_json(app, "/api/state")
        question = state["question"]

        assert question["choices"] == ["y", "n"]
        assert "looks like raw FVCOM output" in question["text"]
        assert question["text"].endswith("Is this FVCOM output? (y/n) ")
        assert post(app, "/api/answer", {"id": question["id"], "answer": "y"})[0] == 200
        wait_for(lambda: app.view == "recipes")
        assert app.recipes_page.context["fvcom"] is True
        # it can only be answered once
        assert post(app, "/api/answer", {"id": question["id"], "answer": "n"})[0] == 409

    def test_validating(self, app, tmp_path, runs):
        app.choose("validate")
        status, reply = post(app, "/api/validate", {"form": {}})
        assert status == 400
        assert "No matchups found" in reply["errors"]["data_dir"]

        write_matchups(tmp_path)
        assert (
            post(app, "/api/validate", {"form": {"out_dir": "report", "word": True}})[0]
            == 200
        )
        [(args, label)] = runs
        assert args[0] == "validate"
        assert json.loads(args[1]) == {
            "data_dir": str(tmp_path),
            "out_dir": str(tmp_path / "report"),
            "word": True,
        }
        assert label == 'oceanval.validate(data_dir=".", out_dir="report", word=True)'
        assert app.results_dir == str(tmp_path / "report")

    def test_validating_matchups_just_made(self, app, tmp_path):
        app.view, app.action, app.status = "finished", "matchup", "finished"
        post(
            app,
            "/api/choose",
            {"action": "validate", "data_dir": str(tmp_path / "run")},
        )

        assert app.view == "validate"
        assert app.validate_form["data_dir"] == "run"

    @pytest.mark.parametrize("chosen", [None, "matchups"])
    def test_validate_defaults_to_matchup_output_directory(self, app, tmp_path, chosen):
        if chosen:
            app.out_dir = str(tmp_path / chosen)

        assert post(app, "/api/choose", {"action": "validate"})[0] == 200
        expected = chosen or "."
        assert app.validate_form["data_dir"] == expected

    def test_a_run_from_start_to_finish(self, app, tmp_path):
        script = tmp_path / "run.py"
        script.write_text(
            textwrap.dedent(
                """
                from oceanval import prompts
                print("matching")
                print("answer:", prompts.ask("Happy? (y/n) ", ("y", "n")))
                """
            )
        )
        app.action = "matchup"
        app.start_run(["script", str(script)], "python run.py")
        wait_for(lambda: app.question is not None)
        _, state = get_json(app, "/api/state")

        assert state["view"] == "running"
        assert state["console"]["text"].startswith("$ python run.py\n")
        assert state["console"]["text"].endswith("matching\nHappy? (y/n) ")
        assert (
            post(app, "/api/answer", {"id": state["question"]["id"], "answer": "n"})[0]
            == 200
        )
        wait_for(lambda: app.view == "finished")
        _, state = get_json(app, "/api/state")
        assert state["run"]["status"] == "finished"
        # the answer follows the question, as at a terminal
        assert state["console"]["text"].endswith("Happy? (y/n) n\nanswer: n\n")
        assert post(app, "/api/restart")[0] == 200
        assert app.view == "start"

    def matchups_script(self, tmp_path):
        """A stand-in for matchup, asking whether the matchups are right with
        the details the window shows."""
        script = tmp_path / "run.py"
        script.write_text(
            textwrap.dedent(
                f"""
                from oceanval import prompts
                print("finding the files")
                question = "Are you happy with these matchups? (y/n) "
                print("answer:", prompts.ask(question, ("y", "n"), details={MATCHUPS!r}))
                print("matching up")
                """
            )
        )
        return script

    def test_the_matchups_are_asked_about_with_their_files(self, app, tmp_path):
        app.action = "matchup"
        app.start_run(["script", str(self.matchups_script(tmp_path))], "python run.py")
        # the page says the files are being found until it is asked
        assert get_json(app, "/api/state")[1]["run"]["identifying"]
        wait_for(lambda: app.question is not None)
        _, state = get_json(app, "/api/state")
        question = state["question"]

        assert not state["run"]["identifying"]
        assert question["details"]["rows"] == MATCHUPS["rows"]
        # the files can be many, so they are asked for a pattern at a time
        assert "files" not in question["details"]
        status, reply = get_json(
            app, "/api/question_files", id=question["id"], pattern="x_**_grid_T.nc"
        )
        assert (status, reply["files"]) == (200, MATCHUPS["files"]["x_**_grid_T.nc"])
        assert get_json(app, "/api/question_files", id=question["id"], pattern="y")[0] == 409

        assert post(app, "/api/answer", {"id": question["id"], "answer": "y"})[0] == 200
        wait_for(lambda: app.view == "finished")
        assert app.status == "finished"
        assert "answer: y\nmatching up\n" in app.console.since(0, None)["text"]
        # once it is answered, they are not listed
        assert (
            get_json(app, "/api/question_files", id=question["id"], pattern="x_**_grid_T.nc")[0]
            == 409
        )

    def test_no_to_the_matchups_stops_the_run(self, app, tmp_path):
        app.action = "matchup_validate"
        app.start_run(["script", str(self.matchups_script(tmp_path))], "python run.py")
        wait_for(lambda: app.question is not None)

        assert post(app, "/api/answer", {"id": app.question.id, "answer": "n"})[0] == 200
        wait_for(lambda: app.view == "finished", timeout=30)
        _, state = get_json(app, "/api/state")
        assert (state["run"]["status"], state["run"]["rejected"]) == ("stopped", True)
        # nothing carries on to validate
        assert "answer:" not in state["console"]["text"]

    def test_store_choice_stops_before_matching_and_keeps_the_script(self, app, tmp_path):
        script = self.matchups_script(tmp_path)
        app.action = "matchup_validate"
        app.start_run(["script", str(script)], "python run.py")
        wait_for(lambda: app.question is not None)

        assert post(app, "/api/answer", {"id": app.question.id, "answer": "save"})[0] == 200
        wait_for(lambda: app.view == "script_saved")
        _, state = get_json(app, "/api/state")
        assert state["run"]["status"] == "stopped"
        assert state["run"]["script_saved"] is True
        assert state["run"]["script"] == str(script)
        assert state["run"]["script_command"] == f"python {script}"
        assert "answer:" not in state["console"]["text"]
        assert "matching up" not in state["console"]["text"]

    def test_stopping_a_run(self, app, tmp_path):
        script = tmp_path / "run.py"
        script.write_text(
            "import time\nprint('started', flush=True)\ntime.sleep(120)\n"
        )
        app.start_run(["script", str(script)], "python run.py")
        wait_for(lambda: "started" in app.console.since(0, None)["text"])

        assert post(app, "/api/stop")[0] == 200
        wait_for(lambda: app.view == "finished", timeout=30)
        assert app.status == "stopped"

    def test_quitting(self, app):
        assert post(app, "/api/quit")[0] == 200
        assert app.closed.wait(5)
        assert get_json(app, "/api/state")[1]["closed"]


def test_the_command_runs():
    root = os.path.dirname(os.path.dirname(os.path.abspath(oceanval.__file__)))
    result = subprocess.run(
        [sys.executable, "-m", "oceanval", "--help"],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=180,
    )

    assert result.returncode == 0, result.stderr
    assert "--port" in result.stdout


def test_the_window_in_a_browser(browser, tmp_path, monkeypatch):
    """The whole of matching up only, driven as a user would, with a stand-in
    for the script, which would otherwise download observations."""
    write_simulation(tmp_path / "sim")
    stand_in = tmp_path / "stand_in.py"
    stand_in.write_text(
        textwrap.dedent(
            f"""
            import time
            from oceanval import prompts
            # long enough for the page to say the files are being found
            time.sleep(2)
            question = "Are you happy with these matchups? (y/n) "
            print("answer:", prompts.ask(question, ("y", "n"), details={MATCHUPS!r}))
            print("again:", prompts.ask("Try again? (y/n) ", ("y", "n")))
            """
        )
    )
    app = App(cwd=str(tmp_path))
    start_run = app.start_run
    monkeypatch.setattr(
        app,
        "start_run",
        lambda args, label: start_run(["script", str(stand_in)], label),
    )
    url = app.start()
    try:
        page = browser.new_page()
        page.goto(url)
        assert "Choose what to do. Matchups, scripts and reports are written" not in page.text_content("#view-start")
        page.click('button.choice[data-action="matchup"]')
        page.wait_for_function(
            "document.querySelector('#title').textContent === 'Provide some essential information about your simulation data'"
        )
        assert page.text_content("#title") == "Provide some essential information about your simulation data"
        assert page.locator("#title").evaluate("node => getComputedStyle(node).whiteSpace") == "nowrap"
        assert "OceanVal is running from" in page.text_content("#meta")
        assert "Next, OceanVal reads the simulation, and shows you what it found." not in page.text_content("#bar")
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.locator("#title").evaluate("node => getComputedStyle(node).whiteSpace") == "normal"
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        page.set_viewport_size({"width": 1280, "height": 720})
        assert page.locator(".ndown-row").evaluate(
            "node => getComputedStyle(node).display"
        ) == "grid"
        assert page.locator("#f-ndown").evaluate(
            "node => node.getBoundingClientRect().width"
        ) <= 100
        assert page.locator("#ndown-example").evaluate(
            "node => node.getBoundingClientRect().left >= document.querySelector('#f-ndown').getBoundingClientRect().right"
        )
        assert page.locator("#ndown-example").evaluate(
            "node => getComputedStyle(node).color"
        ) == "rgb(7, 92, 104)"
        ndown_label = page.locator('label[for="f-ndown"]')
        assert page.locator("#f-ndown").evaluate("node => node.required")
        assert ndown_label.evaluate("node => getComputedStyle(node).color") == "rgb(192, 57, 43)"
        assert ndown_label.evaluate("node => getComputedStyle(node).fontWeight") == "700"
        assert "Required" in ndown_label.text_content()
        assert page.is_hidden("#f-start")
        assert page.is_hidden("#f-end")
        assert "Years to validate" not in page.locator("#view-setup").text_content()
        simdir_label = page.locator('label[for="f-simdir"]')
        assert simdir_label.text_content().startswith("Which directory stores your simulation data?")
        assert simdir_label.locator(".own-req").text_content() == "Required"
        assert simdir_label.evaluate("node => getComputedStyle(node).color") == "rgb(192, 57, 43)"
        assert simdir_label.evaluate("node => getComputedStyle(node).fontWeight") == "700"
        assert page.text_content("#summary").strip() == ""
        page.fill("#f-simdir", "sim")
        # years are inferred, but the user must choose the directory depth
        page.wait_for_function("document.querySelector('#f-end').value === '2012'")
        assert page.input_value("#f-ndown") == ""
        assert page.is_disabled("#continue")
        assert page.input_value("#f-start") == "2011"
        page.fill("#f-ndown", "2")
        assert page.is_enabled("#continue")
        # the output goes where oceanval was started, unless changed
        assert page.input_value("#f-out_dir") == str(tmp_path)
        assert page.text_content("#f-out_dir-label") == "Where do you want matchups to be saved?"
        assert page.is_hidden("#row-overwrite")

        page.click("#continue")
        assert page.text_content("#summary").strip() == ""
        # no data of our own
        page.click("#own-no")
        page.wait_for_url("**/recipes/**", timeout=90000)
        assert page.text_content("#write") == "Match up"
        assert page.locator("#meta .meta__k").all_text_contents() == ["Simulation"]
        # chosen with the simulation instead
        assert page.is_hidden("#group-files")
        assert page.is_hidden("#group-output")
        assert page.is_hidden("#group-report")
        assert page.is_hidden("#group-detail")
        assert page.is_hidden("#group-regional")
        # the app always asks
        assert page.is_hidden("#s-ask")
        fill_required_recipe_years(page)
        # the thickness hint is between its box and the missing-values label
        assert "What should be treated as missing values?" in page.evaluate(
            "document.getElementById('g-thickness').nextElementSibling.textContent"
        )
        # a dataset through the water column cannot go ahead without a thickness
        nsbc = 'input[aria-label="NSBC, Northwest European Shelf, for Temperature"]'
        page.check(nsbc)
        page.check(
            'input[aria-label="Validate NSBC observations for Temperature through the full water column"]'
        )
        assert page.is_disabled("#write")
        assert "a thickness is needed" in page.text_content("#g-thickness")
        page.fill("#s-thickness", "z_level")
        assert page.is_enabled("#write")
        page.uncheck(nsbc)
        page.click("#write")
        # the units have to be confirmed, once they have been read
        page.wait_for_selector("#units-body-gridded tr[data-units-row]")
        page.check("#units-confirm")
        page.click("#units-continue")

        # until matchup asks, the page says it is finding the files
        page.wait_for_selector("#identify:not([hidden])", timeout=90000)
        assert "Identifying files that meet criteria. Please wait!" in page.text_content("#identify")
        # and then shows what it found as a table, in place of the question below the output
        page.wait_for_selector("#review:not([hidden])", timeout=90000)
        assert page.is_hidden("#identify")
        assert page.is_hidden("#ask")
        assert page.text_content("#review-time-note") == (
            "Temporal subsetting will be applied to the files listed below, based on the time criteria you provided on the previous pages. "
            "Any year limits set for an individual dataset will also apply."
        )
        row = page.locator('#review-body tr[data-variable="temperature"]')
        for text in ("Temperature", "thetao", "COBE2, ICES (point)", "x_**_grid_T.nc", "2 files"):
            assert text in row.text_content()

        row.locator("button:has-text('List all files')").click()
        page.wait_for_selector("#files-list .picker__file")
        assert page.text_content("#files-notice").startswith(
            "Temporal subsetting will be applied to these files by OceanVal"
        )
        assert "2011 to 2012" in page.text_content("#files-notice")
        assert page.locator("#files-list .picker__file").all_text_contents() == [
            "2011/x_2011_grid_T.nc",
            "2012/x_2012_grid_T.nc",
        ]
        page.keyboard.press("Escape")
        assert page.is_hidden("#files")
        page.click("#review-actions button:has-text('Yes')")

        # any other question is asked under the output
        page.wait_for_selector("#ask:not([hidden])", timeout=60000)
        assert page.is_hidden("#review")
        # the buttons say what "(y/n)" would
        assert page.text_content("#ask-question") == "Try again?"
        page.click("#ask-answer button:has-text('Yes')")
        page.wait_for_selector("#result:not([hidden])", timeout=60000)

        assert "The matchups are ready" in page.text_content("#result")
        assert "answer: y" in page.text_content("#console-text")
    finally:
        app.close()


def test_storing_the_matchup_script_opens_run_instructions(browser, tmp_path):
    script = tmp_path / "matchup.py"
    script.write_text(
        textwrap.dedent(
            f"""
            from oceanval import prompts
            question = "Are you happy with these matchups? (y/n) "
            prompts.ask(question, ("y", "n"), details={MATCHUPS!r})
            print("matching up")
            """
        )
    )
    app = App(cwd=str(tmp_path))
    app.action = "matchup_validate"
    app.start_run(["script", str(script)], f"python {script}")
    url = app.start()
    try:
        page = browser.new_page()
        page.goto(url)
        page.wait_for_selector("#review:not([hidden])")
        page.click('#review-actions button:has-text("No, store the matchup Python script. I will run it later.")')
        page.wait_for_selector("#view-script-saved:not([hidden])")

        assert page.text_content("#title") == "Your matchup script is saved"
        assert "The matchup has not been run" in page.text_content("#view-script-saved")
        assert page.text_content("#script-saved-command") == f"python {script}"
        assert page.text_content("#script-saved-path") == str(script)
        assert "matching up" not in page.text_content("#console-text")
        page.click('#actions button:has-text("Start again")')
        page.wait_for_function("document.querySelector('#title').textContent === 'Validate an ocean model'")
    finally:
        app.close()


def test_overwrite_choice_only_appears_for_existing_matchups(browser, tmp_path):
    write_simulation(tmp_path / "sim")
    (tmp_path / "old" / "oceanval_matchups").mkdir(parents=True)
    app = App(cwd=str(tmp_path))
    url = app.start()
    try:
        page = browser.new_page()
        page.goto(url)
        page.click('button.choice[data-action="matchup"]')
        page.fill("#f-simdir", "sim")
        page.wait_for_function("document.querySelector('#f-end').value === '2012'")
        page.fill("#f-ndown", "2")
        assert page.is_hidden("#row-overwrite")

        page.fill("#f-out_dir", "old")
        page.wait_for_selector("#row-overwrite:not([hidden])")
        warning = page.locator("#m-out_dir .group__line.is-warn")
        assert "There are matchups here already" in warning.text_content()
        assert warning.text_content() == "There are matchups here already, from an earlier run. Choose another directory if you need to keep them apart."
        assert warning.evaluate("node => getComputedStyle(node).color") == "rgb(184, 83, 47)"
        assert not page.is_checked("#f-overwrite")
        assert page.text_content("#row-overwrite").strip() == "Do you want to overwrite existing matchups in this directory?"
        page.check("#f-overwrite")
        page.click("#continue")
        page.click("#own-no")
        page.wait_for_url("**/recipes/**", timeout=90000)
        assert page.is_hidden("#s-overwrite")
        assert app.recipes_page.form["overwrite"] is True
    finally:
        app.close()


def test_the_units_step_in_a_browser(browser, tmp_path, monkeypatch):
    """The table lists the units of each matchup with the conversion OceanVal
    fills in where they differ, in red and bold for as long as it is OceanVal's,
    the units have to be confirmed to carry on, a conversion that is not a
    number is marked, and those that are go into the script."""
    write_simulation(tmp_path / "sim", tracers=True)
    stand_in = tmp_path / "stand_in.py"
    stand_in.write_text("print('running')\n")
    app = App(cwd=str(tmp_path))
    start_run = app.start_run
    monkeypatch.setattr(
        app,
        "start_run",
        lambda args, label: start_run(["script", str(stand_in)], label),
    )
    url = app.start()
    try:
        page = browser.new_page()
        page.goto(url)
        page.click('button.choice[data-action="matchup"]')
        page.fill("#f-simdir", "sim")
        page.wait_for_function("document.querySelector('#f-end').value === '2012'")
        page.fill("#f-ndown", "2")
        page.click("#continue")
        page.click("#own-no")
        page.wait_for_url("**/recipes/**", timeout=90000)
        fill_required_recipe_years(page)
        page.click("#write")

        page.wait_for_selector("#units-body-gridded tr[data-units-row]")
        # the units start unconfirmed, and nothing carries on until they are
        assert page.is_visible("#units-title-confirm")
        assert not page.is_checked("#units-confirm")
        assert page.is_disabled("#units-continue")
        assert "Units" in page.text_content("#steps")
        assert page.text_content("#steps .is-current .steps__label") == "Units"
        assert page.is_hidden("#units-reading")
        # two sections, and with no point datasets the second says so
        assert page.text_content("#units-title-gridded") == "Gridded datasets"
        assert page.text_content("#units-title-point") == "Point datasets"
        assert page.locator("#units-body-point tr").count() == 0
        assert page.is_visible("#units-empty-point")
        assert page.is_hidden("#units-empty-gridded")

        temperature = page.locator('tr[data-units-row="recipe:temperature:cobe2"]')
        for text in ("temperature (cobe2)", "thetao", "degC", "sst"):
            assert text in temperature.text_content()
        # what OceanVal made of the units is on the line under each row
        below = "xpath=following-sibling::tr[1]"
        assert "OceanVal thinks these are the same units" in temperature.locator(below).text_content()
        # which is a suggestion, so it is not ticked off
        assert temperature.locator(f"{below}//*[contains(@class, 'icon')]").count() == 0
        multiplier = temperature.locator('input[data-units-box="multiplier"]')
        assert multiplier.input_value() == ""
        # WOA23's nitrate is per kilogram, and the model's per volume
        nitrate = page.locator('tr[data-units-row="recipe:nitrate:woa23"]')
        assert nitrate.locator('input[data-units-box="multiplier"]').input_value() == "1.025"
        assert "1025 kg/m³" in nitrate.locator(below).text_content()

        # what OceanVal filled in is red and bold, and what it did not is not
        def look(box):
            return box.evaluate(
                "node => [getComputedStyle(node).color, getComputedStyle(node).fontWeight]"
            )

        red_bold = ["rgb(192, 57, 43)", "700"]
        oceanval = nitrate.locator('input[data-units-box="multiplier"]')
        oceanval_note = nitrate.locator(f"{below}//*[contains(@class, 'group__line')]")
        assert look(oceanval) == red_bold
        assert look(oceanval_note) == red_bold
        assert look(multiplier)[1] == "400"
        assert look(temperature.locator(f"{below}//*[contains(@class, 'group__line')]"))[1] == "400"
        # but not once it is changed, which the note says, and it is again if put back
        oceanval.fill("2")
        assert look(oceanval)[1] == "400"
        assert look(oceanval_note)[1] == "400"
        assert "You have changed the conversion OceanVal filled in" in nitrate.locator(below).text_content()
        oceanval.fill("1.025")
        assert look(oceanval) == red_bold
        assert look(oceanval_note) == red_bold

        # the units always have to be confirmed, under the tables, to carry on
        page.check("#units-confirm")
        assert page.is_enabled("#units-continue")
        page.uncheck("#units-confirm")
        assert page.is_disabled("#units-continue")

        # changing a conversion undoes the confirmation, as it is not what was confirmed
        page.check("#units-confirm")
        multiplier.fill("abc")
        assert not page.is_checked("#units-confirm")
        assert page.is_disabled("#units-continue")
        page.check("#units-confirm")
        page.click("#units-continue")
        page.wait_for_selector(".units-body .is-invalid")
        error = page.locator('[data-units-error="recipe:temperature:cobe2"]')
        assert error.text_content() != ""
        multiplier.fill("2")
        page.check("#units-confirm")
        page.click("#units-continue")
        page.wait_for_selector("#console-text:has-text('running')", timeout=60000)

        text = open(tmp_path / "matchup.py").read()
        assert "    obs_multiplier=1.025,\n" in text[text.index('name="nitrate"') :].split("\n)\n")[0]
        assert "    obs_multiplier=2,\n" in text
    finally:
        app.close()


def test_clearing_every_selection_in_a_browser(browser, tmp_path):
    """Clear all selections unticks every dataset, and is then disabled until
    one is ticked again."""
    write_simulation(tmp_path / "sim")
    app = App(cwd=str(tmp_path))
    url = app.start()
    try:
        page = browser.new_page()
        page.goto(url)
        page.click('button.choice[data-action="matchup"]')
        page.fill("#f-simdir", "sim")
        page.wait_for_function("document.querySelector('#f-end').value === '2012'")
        page.fill("#f-ndown", "2")
        page.click("#continue")
        page.click("#own-no")
        page.wait_for_url("**/recipes/**", timeout=90000)

        ticked = ".chip input:checked"
        assert page.locator(ticked).count() > 0
        assert page.is_enabled("#clear-selections")
        page.click("#clear-selections")

        assert page.locator(ticked).count() == 0
        assert "0 comparisons selected" in page.text_content("#summary")
        assert page.is_disabled("#clear-selections")
        # a dataset can be ticked again
        page.locator(".chip input:not(:disabled)").first.check()
        assert page.is_enabled("#clear-selections")
    finally:
        app.close()


def test_adding_your_own_data_in_a_browser(browser, tmp_path):
    """Yes leads to the point data step, where what has to be given is marked
    in red, an entry is added, and Skip becomes Continue."""
    write_simulation(tmp_path / "sim")
    (tmp_path / "points").mkdir()
    (tmp_path / "points" / "obs.csv").write_text("lon,lat,observation\n1,2,3\n")
    app = App(cwd=str(tmp_path))
    url = app.start()
    try:
        page = browser.new_page()
        page.goto(url)
        page.click('button.choice[data-action="matchup"]')
        page.fill("#f-simdir", "sim")
        page.wait_for_function("document.querySelector('#f-end').value === '2012'")
        page.fill("#f-ndown", "2")
        page.click("#continue")
        page.click("#own-yes")
        page.wait_for_selector("#own-form-point")

        assert page.text_content("#own-next") == "Skip"
        assert page.get_attribute("#o-point-name", "list") == "own-variable-options"
        suggestions = page.locator("#own-variable-options option").evaluate_all(
            "nodes => nodes.map(node => node.value)"
        )
        assert {"temperature", "nitrate"} <= set(suggestions)
        optional = page.locator("#own-optional-point")
        chevron = optional.locator(".own-optional__chevron")
        assert not optional.evaluate("node => node.open")
        closed_chevron = chevron.evaluate("node => getComputedStyle(node).transform")
        page.locator("#own-optional-point > summary").click()
        assert optional.evaluate("node => node.open")
        assert chevron.evaluate("node => getComputedStyle(node).transform") != closed_chevron
        red = "rgb(192, 57, 43)"

        def field_of(name):
            return page.locator(f"#o-point-{name}").locator(
                "xpath=ancestor::div[contains(concat(' ', @class, ' '), ' own-field ')]"
            )

        for name in ("name", "source", "model_variable", "obs_path"):
            field = field_of(name)
            assert "is-required" in field.get_attribute("class")
            assert field.locator(".g-label").evaluate("node => getComputedStyle(node).color") == red
        # optional ones are not
        assert field_of("long_name").get_attribute("class") == "own-field"

        page.click("#own-add-point")
        page.wait_for_selector("#o-point-name-err:not(:empty)")
        assert page.get_attribute("#o-point-name", "aria-invalid") == "true"

        page.fill("#o-point-name", "chl")
        page.fill("#o-point-source", "cruise")
        page.fill("#o-point-model_variable", "thetao")
        page.fill("#o-point-obs_path", "points")
        page.click("#own-add-point")
        page.wait_for_selector("#own-list-point:not([hidden])")
        page.wait_for_function("document.querySelector('#own-next').textContent === 'Continue'")

        page.click("#own-next")
        page.wait_for_selector("#own-form-gridded")
        assert page.get_attribute("#o-gridded-name", "list") == "own-variable-options"
        assert page.is_visible("#o-gridded-climatology")
        assert app.own_data["point"][0]["name"] == "chl"
    finally:
        app.close()


def test_choosing_directories_in_a_browser(browser, tmp_path):
    """The folder browser and the folders suggested as a path is typed, on the
    simulation step's directory and the validate step's matchups."""
    write_simulation(tmp_path / "sim")
    (tmp_path / "sim_old").mkdir()
    write_matchups(tmp_path / "run")
    app = App(cwd=str(tmp_path))
    url = app.start()
    try:
        page = browser.new_page()
        page.goto(url)
        page.click('button.choice[data-action="matchup"]')

        page.click('[data-browse="f-simdir"]')
        page.click('#picker-list .picker__row[title="sim"]')
        page.wait_for_function(
            "document.querySelector('#picker-crumbs .is-current').textContent === 'sim'"
        )
        page.click("#picker-choose")
        # as if it had been typed: the live check fills in the rest
        page.wait_for_function("document.querySelector('#f-end').value === '2012'")
        assert page.input_value("#f-simdir") == "sim"
        assert page.input_value("#f-ndown") == ""

        page.fill("#f-simdir", "si")
        page.wait_for_function(
            "document.querySelectorAll('#f-simdir-folders option').length === 2"
        )
        assert page.eval_on_selector_all(
            "#f-simdir-folders option", "options => options.map(o => o.value)"
        ) == ["sim/", "sim_old/"]

        page.click("text=Back")
        page.click('button.choice[data-action="validate"]')
        page.click('[data-browse="v-data_dir"]')
        page.click('#picker-list .picker__row[title="run"]')
        page.wait_for_function(
            "document.querySelector('#picker-crumbs .is-current').textContent === 'run'"
        )
        assert page.text_content("#picker-info") == "oceanval_matchups is here."
        page.click("#picker-choose")
        assert page.input_value("#v-data_dir") == "run"
        assert page.is_hidden("#picker")
    finally:
        app.close()


def test_viewing_files_in_a_random_directory_in_a_browser(browser, tmp_path):
    """The pop-up on the simulation step that lists the file names in one
    directory of the simulation, chosen at random."""
    for year in ("2001", "2002"):
        (tmp_path / "sim" / year).mkdir(parents=True)
        for name in ("a_grid_T.nc", "a_ptrc_T.nc"):
            (tmp_path / "sim" / year / name).write_text("")
    app = App(cwd=str(tmp_path))
    url = app.start()
    try:
        page = browser.new_page()
        page.goto(url)
        page.click('button.choice[data-action="matchup"]')

        # nothing to look in yet
        page.click("#view-files")
        page.wait_for_selector("#sample-list .picker__empty")
        assert "Enter the directory" in page.text_content("#sample-list")
        page.keyboard.press("Escape")
        assert page.is_hidden("#sample")

        page.fill("#f-simdir", "sim")
        page.fill("#f-ndown", "1")
        page.click("#view-files")
        page.wait_for_selector("#sample-list .picker__file")
        assert page.eval_on_selector_all(
            "#sample-list .picker__file", "nodes => nodes.map(n => n.textContent)"
        ) == ["a_grid_T.nc", "a_ptrc_T.nc"]
        first = page.text_content("#sample-intro")
        assert first in ("sim/2001", "sim/2002")

        # another directory, never the same one twice running
        page.click("#sample-another")
        page.wait_for_function(
            "text => document.querySelector('#sample-intro').textContent !== text", arg=first
        )
        page.click("#sample-close")
        assert page.is_hidden("#sample")
    finally:
        app.close()
