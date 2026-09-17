import builtins
import os
import shutil

import nctoolkit as nc
import pytest

import oceanval
import oceanval.gridded as gridded
from oceanval.session import session_info


def boom(*args, **kwargs):
    raise ConnectionError("Connection timed out: www.ncei.noaa.gov")


def answer_with(answers):
    """Feed a fixed list of answers to input(), echoing them like a user."""
    remaining = iter(answers)

    def fake_input(prompt=""):
        value = next(remaining)
        print(f"{prompt}{value}")
        return value

    return fake_input


@pytest.fixture(autouse=True)
def clean_matchups():
    # oceanval.reset() rather than definitions.reset(): the latter leaves
    # session_info["short_title"] behind, which then refuses the same
    # variable being registered again by another test file
    oceanval.reset()
    session_info["failed_gridded"] = []
    session_info["end_messages"] = []
    shutil.rmtree("oceanval_matchups", ignore_errors=True)
    yield
    shutil.rmtree("oceanval_matchups", ignore_errors=True)
    oceanval.reset()
    session_info["failed_gridded"] = []
    session_info["end_messages"] = []


class TestRemoteDetection:
    def test_a_thredds_recipe_is_remote(self):
        oceanval.add_gridded_comparison(
            name="nitrate",
            model_variable="N3_n",
            recipe={"nitrate": "woa23"},
            climatology=True,
            file_check=False,
        )

        assert gridded.remote_gridded_source("nitrate", "WOA23") is True

    def test_a_local_file_is_not_remote(self):
        oceanval.add_gridded_comparison(
            name="temperature",
            obs_path="data/evaldata/gridded/nws/temperature",
            source="foo",
            model_variable="votemper",
            obs_variable="votemper",
            climatology=True,
            obs_adder=273.15,
        )

        # a local file that errors is a data or settings problem, and
        # retrying it would just fail the same way
        assert gridded.remote_gridded_source("temperature", "foo") is False


class TestFailedRemoteMatchup:
    def test_a_failed_remote_variable_does_not_stop_the_others(self, monkeypatch):
        oceanval.add_gridded_comparison(
            name="temperature",
            obs_path="data/evaldata/gridded/nws/temperature",
            source="foo",
            model_variable="votemper",
            obs_variable="votemper",
            climatology=True,
            start=2000,
            end=2010,
            obs_adder=273.15,
        )
        oceanval.add_gridded_comparison(
            name="nitrate",
            model_variable="N3_n",
            recipe={"nitrate": "woa23"},
            climatology=True,
            file_check=False,
        )
        # the observations are downloaded as the matchup runs, so this is
        # what a server being unreachable looks like from inside the loop
        monkeypatch.setattr(nc, "open_thredds", boom)

        oceanval.matchup(
            sim_dir="data/example", start=2000, end=2000, ask=False, cores=1
        )

        # the local variable still made it all the way through
        assert os.path.exists(
            "oceanval_matchups/gridded/temperature/foo_temperature_surface.nc"
        )
        # and the remote one was recorded rather than taking the run down
        failed = [(x["variable"], x["source"]) for x in session_info["failed_gridded"]]
        assert failed == [("nitrate", "WOA23")]

    def test_a_failed_remote_source_does_not_stop_another_source(self, monkeypatch):
        # one variable, validated against a local and a remote source
        oceanval.add_gridded_comparison(
            name="temperature",
            obs_path="data/evaldata/gridded/nws/temperature",
            source="foo",
            model_variable="votemper",
            obs_variable="votemper",
            climatology=True,
            start=2000,
            end=2010,
            obs_adder=273.15,
        )
        oceanval.add_gridded_comparison(
            name="temperature",
            model_variable="votemper",
            recipe={"temperature": "nsbc"},
            file_check=False,
        )
        monkeypatch.setattr(nc, "open_thredds", boom)

        oceanval.matchup(
            sim_dir="data/example", start=2000, end=2000, ask=False, cores=1
        )

        assert os.path.exists(
            "oceanval_matchups/gridded/temperature/foo_temperature_surface.nc"
        )
        failed = [(x["variable"], x["source"]) for x in session_info["failed_gridded"]]
        assert failed == [("temperature", "NSBC")]

    def test_the_failure_is_logged_with_its_traceback(self, monkeypatch):
        oceanval.add_gridded_comparison(
            name="nitrate",
            model_variable="N3_n",
            recipe={"nitrate": "woa23"},
            climatology=True,
            file_check=False,
        )
        monkeypatch.setattr(nc, "open_thredds", boom)

        oceanval.matchup(
            sim_dir="data/example", start=2000, end=2000, ask=False, cores=1
        )

        log = "oceanval_matchups/matchup_failures.log"
        assert os.path.exists(log)
        logged = open(log).read()
        assert "nitrate" in logged
        assert "ConnectionError" in logged
        assert "Traceback" in logged

    def test_a_failure_warns_loudly(self, monkeypatch, capsys):
        oceanval.add_gridded_comparison(
            name="nitrate",
            model_variable="N3_n",
            recipe={"nitrate": "woa23"},
            climatology=True,
            file_check=False,
        )
        monkeypatch.setattr(nc, "open_thredds", boom)

        with pytest.warns(UserWarning, match="Could not match up gridded nitrate"):
            oceanval.matchup(
                sim_dir="data/example", start=2000, end=2000, ask=False, cores=1
            )

        shouted = capsys.readouterr().out
        assert "!!!" in shouted
        assert "COULD NOT MATCH UP" in shouted


class TestRetryPrompt:
    def test_declining_records_the_failure_and_moves_on(self, monkeypatch):
        session_info["out_dir"] = ""
        session_info["failed_gridded"] = [
            {"variable": "nitrate", "source": "WOA23", "error": "ConnectionError: x"}
        ]
        monkeypatch.setattr(builtins, "input", answer_with(["no"]))

        gridded.retry_failed_gridded(ask=True)

        assert "nitrate" in " ".join(session_info["end_messages"])

    def test_the_answer_is_read_from_its_first_letter(self, monkeypatch):
        session_info["out_dir"] = ""
        session_info["failed_gridded"] = [
            {"variable": "nitrate", "source": "WOA23", "error": "ConnectionError: x"}
        ]
        tried = []

        def succeeds(var_choice=None, **kwargs):
            tried.append(list(var_choice))
            session_info["failed_gridded"] = []

        monkeypatch.setattr(gridded, "gridded_matchup", succeeds)
        # "yeah" is a yes, and only the failed source is retried
        monkeypatch.setattr(builtins, "input", answer_with(["yeah", "1"]))

        gridded.retry_failed_gridded(ask=True)

        assert tried == [[("nitrate", "WOA23")]]

    def test_a_junk_answer_is_asked_again(self, monkeypatch):
        session_info["out_dir"] = ""
        session_info["failed_gridded"] = [
            {"variable": "nitrate", "source": "WOA23", "error": "ConnectionError: x"}
        ]
        monkeypatch.setattr(builtins, "input", answer_with(["maybe", "", "n"]))

        gridded.retry_failed_gridded(ask=True)

        assert "nitrate" in " ".join(session_info["end_messages"])

    def test_retrying_stops_once_the_time_given_is_up(self, monkeypatch):
        session_info["out_dir"] = ""
        session_info["failed_gridded"] = [
            {"variable": "nitrate", "source": "WOA23", "error": "ConnectionError: x"}
        ]
        attempts = []

        def keeps_failing(var_choice=None, **kwargs):
            attempts.append(list(var_choice))
            session_info["failed_gridded"] = [
                {"variable": v, "source": source, "error": "ConnectionError: x"}
                for v, source in var_choice
            ]

        monkeypatch.setattr(gridded, "gridded_matchup", keeps_failing)
        # a tiny budget, then decline the offer to spend more time
        monkeypatch.setattr(builtins, "input", answer_with(["y", "0.02", "n"]))

        gridded.retry_failed_gridded(ask=True)

        # it kept trying within the budget, then gave up rather than looping
        assert len(attempts) >= 1
        assert "nitrate" in " ".join(session_info["end_messages"])

    def test_nothing_is_asked_when_ask_is_false(self, monkeypatch):
        session_info["out_dir"] = ""
        session_info["failed_gridded"] = [
            {"variable": "nitrate", "source": "WOA23", "error": "ConnectionError: x"}
        ]

        def no_prompting(prompt=""):
            raise AssertionError("matchup(ask=False) must not stop to ask")

        monkeypatch.setattr(builtins, "input", no_prompting)

        gridded.retry_failed_gridded(ask=False)

        assert "nitrate" in " ".join(session_info["end_messages"])


class TestThreddsRegistration:
    """add_gridded_comparison when the THREDDS server lets us down."""

    def test_an_unreachable_server_is_ignored_not_raised(self, monkeypatch, capsys):
        monkeypatch.setattr(nc, "open_thredds", boom)

        with pytest.warns(UserWarning, match="THREDDS server unavailable"):
            oceanval.add_gridded_comparison(
                name="nitrate",
                model_variable="N3_n",
                recipe={"nitrate": "woa23"},
                climatology=True,
            )

        # the variable is dropped rather than the registration blowing up
        assert getattr(oceanval.definitions, "nitrate", None) is None

        shouted = capsys.readouterr().out
        assert "THREDDS SERVER NOT AVAILABLE" in shouted
        assert "IGNORING NITRATE" in shouted
        # the variable info and the server address are both shown
        assert "N3_n" in shouted
        assert "WOA23" in shouted
        assert "https://www.ncei.noaa.gov" in shouted

    def test_a_server_that_serves_no_variables_is_ignored(self, monkeypatch, capsys):
        class ServesNothing:
            variables = []

        monkeypatch.setattr(nc, "open_thredds", lambda *a, **k: ServesNothing())

        with pytest.warns(UserWarning, match="THREDDS server unavailable"):
            oceanval.add_gridded_comparison(
                name="nitrate",
                model_variable="N3_n",
                recipe={"nitrate": "woa23"},
                climatology=True,
            )

        # opening worked, so the old code called this a missing obs_variable
        assert getattr(oceanval.definitions, "nitrate", None) is None
        assert "served no variables" in capsys.readouterr().out

    def test_the_ignored_variable_is_reported_at_the_end(self, monkeypatch):
        monkeypatch.setattr(nc, "open_thredds", boom)

        with pytest.warns(UserWarning):
            oceanval.add_gridded_comparison(
                name="nitrate",
                model_variable="N3_n",
                recipe={"nitrate": "woa23"},
                climatology=True,
            )

        assert "nitrate was not registered" in " ".join(session_info["end_messages"])

    def test_other_variables_still_register(self, monkeypatch):
        monkeypatch.setattr(nc, "open_thredds", boom)

        with pytest.warns(UserWarning):
            oceanval.add_gridded_comparison(
                name="nitrate",
                model_variable="N3_n",
                recipe={"nitrate": "woa23"},
                climatology=True,
            )
        oceanval.add_gridded_comparison(
            name="temperature",
            obs_path="data/evaldata/gridded/nws/temperature",
            source="foo",
            model_variable="votemper",
            obs_variable="votemper",
            climatology=True,
            obs_adder=273.15,
        )

        assert getattr(oceanval.definitions, "nitrate", None) is None
        assert getattr(oceanval.definitions, "temperature", None) is not None

    def test_a_local_file_still_raises(self):
        # only a server can be "unavailable" - a local path that is wrong is
        # the user's to fix, so it must not be quietly skipped
        with pytest.raises(ValueError):
            oceanval.add_gridded_comparison(
                name="temperature",
                obs_path="data/evaldata/gridded/nws/temperature/nope.nc",
                source="foo",
                model_variable="votemper",
                obs_variable="votemper",
                climatology=True,
            )

    def test_file_check_false_does_not_contact_the_server(self, monkeypatch):
        def must_not_be_called(*args, **kwargs):
            raise AssertionError("file_check=False must not contact the server")

        monkeypatch.setattr(nc, "open_thredds", must_not_be_called)

        oceanval.add_gridded_comparison(
            name="nitrate",
            model_variable="N3_n",
            recipe={"nitrate": "woa23"},
            climatology=True,
            file_check=False,
        )

        # registering while a server is down, to match up once it is back
        assert getattr(oceanval.definitions, "nitrate", None) is not None
