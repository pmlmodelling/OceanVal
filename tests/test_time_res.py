"""The time resolution of model output, and the check of point_time_res
against it (oceanval.time_res)."""

import pandas as pd
import pytest

from oceanval import time_res


def times(dates):
    return pd.DataFrame([{"year": y, "month": m, "day": d} for y, m, d in dates])


@pytest.mark.parametrize(
    "dates, expected",
    [
        ([(2000, m, 15) for m in range(1, 13)], "monthly"),
        # annual output and a single time are as coarse as can be told
        ([(2000 + y, 7, 1) for y in range(3)], "monthly"),
        ([(2000, 1, 1)], "monthly"),
        ([(2000, 1, d) for d in range(1, 32)], "1d"),
        # more often than daily is daily
        ([(2000, 1, d) for d in range(1, 10) for _ in range(4)], "1d"),
        ([(2000, 1, d) for d in (1, 3, 5, 7)], "2d"),
        ([(2000, m, d) for m in (1, 2) for d in range(1, 31, 5)], "5d"),
        # a 360-day calendar has a 30th of February
        ([(2000, 2, d) for d in range(1, 31)], "1d"),
    ],
)
def test_label(dates, expected):
    assert time_res.label(times(dates)) == expected


def test_finest_first():
    labels = ["monthly", "5d", "1d", "10d", None]
    assert sorted(labels, key=time_res.sort_key) == ["1d", "5d", "10d", "monthly", None]


@pytest.mark.parametrize(
    "resolution, point_time_res, expected",
    [
        ("1d", ["year", "month", "day"], False),
        ("2d", ["year", "month", "day"], True),
        ("monthly", ["year", "month", "day"], True),
        ("monthly", ["month", "day"], True),
        ("monthly", ["year", "month"], False),
        (None, ["year", "month", "day"], False),
    ],
)
def test_needs_check(resolution, point_time_res, expected):
    assert time_res.needs_check(resolution, point_time_res) is expected


ROWS = [
    {"key": "temperature/ices", "variable": "temperature", "title": "Temperature",
     "source": "ices", "time_res": "monthly", "point_time_res": ["year", "month", "day"], "own": False},
    {"key": "nitrate/ices", "variable": "nitrate", "title": "Nitrate",
     "source": "ices", "time_res": "5d", "point_time_res": ["month", "day"], "own": True},
]


def test_check_rows():
    comparisons = {("temperature", "ices"): {}, ("nitrate", "ices"): {"point_time_res": ["month", "day"]},
                   ("salinity", "ices"): {}}
    rows = time_res.check_rows(
        [("temperature", "ices"), ("nitrate", "ices"), ("salinity", "ices"), ("temperature", "ices")],
        {"temperature": "monthly", "nitrate": "5d", "salinity": "1d"},
        lambda variable, source: comparisons[(variable, source)],
        ["year", "month", "day"],
        {"temperature": "Temperature", "nitrate": "Nitrate"},
    )
    assert rows == ROWS


class Comparisons(dict):
    def __getitem__(self, name):
        return self.setdefault(name, type("D", (), {"point_comparisons": {"ices": {}}})())


def test_all_of_them_changes_matchups_and_each_one_with_its_own():
    session, definitions = {"point_time_res": ["year", "month", "day"]}, Comparisons()
    choice = time_res.clean_choice({"default": ["year", "month"]}, ROWS)
    time_res.apply(choice, ROWS, session, definitions)
    assert session["point_time_res"] == ["year", "month"]
    assert definitions["nitrate"].point_comparisons["ices"]["point_time_res"] == ["year", "month"]
    # it has none of its own, so matchup's is used
    assert "point_time_res" not in definitions["temperature"].point_comparisons["ices"]


def test_each_one():
    session, definitions = {"point_time_res": ["year", "month", "day"]}, Comparisons()
    choice = time_res.clean_choice({"datasets": {"temperature/ices": ["month"]}}, ROWS)
    said = time_res.apply(choice, ROWS, session, definitions)
    assert session["point_time_res"] == ["year", "month", "day"]
    assert definitions["temperature"].point_comparisons["ices"]["point_time_res"] == ["month"]
    assert said == ["point_time_res for Temperature (ices) is now ['month']"]


def test_keeping_them_changes_nothing():
    session, definitions = {"point_time_res": ["year", "month", "day"]}, Comparisons()
    assert time_res.apply(time_res.clean_choice(None, ROWS), ROWS, session, definitions) == []
    assert session["point_time_res"] == ["year", "month", "day"]


@pytest.mark.parametrize(
    "choice",
    [
        "year",
        {"default": ["week"]},
        {"default": []},
        {"datasets": {"temperature/ices": ["day", "day"]}},
        {"datasets": {"chlorophyll/occci": ["month"]}},
    ],
)
def test_bad_choices_are_refused(choice):
    with pytest.raises(ValueError):
        time_res.clean_choice(choice, ROWS)


def test_asked_at_a_terminal():
    answers = iter(["x", "e", "2", "9", "4"])
    choice = time_res.ask_at_terminal(ROWS, lambda question, choices: next(answers))
    assert choice == {"default": None,
                      "datasets": {"temperature/ices": ["year", "month"], "nitrate/ices": ["month"]}}
