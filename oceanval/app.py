"""The oceanval command: OceanVal in a window in your web browser.

Run ``oceanval`` (or ``OceanVal``) in a terminal, in the directory to work
in, and a page opens in your web browser that takes you through:

1. choosing to match up new data and validate it, to match up only, or to
   validate matchups made earlier;
2. the simulation to match up, which create_recipes then reads - or, to
   validate only, the options for validate();
3. the create_recipes window, whose button then starts the matchup rather
   than only writing the script;
4. the run: the script create_recipes wrote, or validate(), in a process of
   its own (see oceanval.app_child). The page shows its output as it comes,
   which is printed in the terminal too, and asks any question it asks.

Like the create_recipes window (see oceanval.recipes_gui), the page is
served only on 127.0.0.1, only to requests carrying the random token in its
link, and loads nothing from anywhere else.
"""

import argparse
import codecs
import contextlib
import glob
import io
import itertools
import json
import os
import queue
import random
import secrets
import signal
import subprocess
import sys
import threading
import traceback
import urllib.parse

import oceanval
from oceanval import prompts, recipes_gui
from oceanval.app_child import QUESTION_MARKER
from oceanval import own_data, units
from oceanval.create_recipes import (
    DOMAIN_REGIONS,
    _literal,
    create_recipes,
    simulation_paths,
    simulation_years,
)

# what the first step offers
ACTIONS = ("matchup_validate", "matchup", "validate")

# the depths the simulation step looks for output files at, when there are
# none where it was told to look
_SEARCH_DEPTHS = range(4)

# the folder browser lists at most this many folders, and counts the rest
_MOST_FOLDERS = 2000

# the sample of a simulation's files lists at most this many, and counts the rest
_MOST_FILES = 500


def default_setup_form():
    """The simulation step's boxes, as they start."""
    return {
        "simdir": "",
        "ndown": "",
        "domain": "global",
        "start": "",
        "end": "",
        "exclude": "",
        "require": "",
        "out": "matchup.py",
    }


def default_validate_form():
    """The report options step's boxes, as they start."""
    return {
        "data_dir": "",
        "out_dir": "",
        "lon_min": "",
        "lon_max": "",
        "lat_min": "",
        "lat_max": "",
        "subregions": "",
        "subregions_file": "",
        "fixed_scale": False,
        "pdf": False,
        "word": False,
        "zip": False,
    }


def _path(text, cwd):
    """A path typed into the page, which is relative to the directory the
    app works in."""
    return os.path.normpath(os.path.join(cwd, os.path.expanduser(text)))


def _shown(path, cwd):
    """A path as the page shows it: relative, if it is inside cwd."""
    relative = os.path.relpath(path, cwd)
    return path if relative.startswith("..") else relative


def _form(form, defaults):
    """What the page sent for a step, limited to its own boxes."""
    form = form if isinstance(form, dict) else {}
    return {
        name: (
            bool(form.get(name, value))
            if isinstance(value, bool)
            else str(form.get(name, value) or "").strip()
        )
        for name, value in defaults.items()
    }


def check_setup(form, cwd):
    """Turn the simulation step's boxes into create_recipes arguments.

    Returns (arguments, errors), where errors maps each box that cannot be
    used to the reason.
    """
    form = _form(form, default_setup_form())
    arguments, errors = {}, {}

    if not form["simdir"]:
        errors["simdir"] = "Enter the directory the model output is in."
    elif not os.path.isdir(_path(form["simdir"], cwd)):
        errors["simdir"] = "There is no directory at this path."
    else:
        arguments["simdir"] = _path(form["simdir"], cwd)
    try:
        arguments["ndown"] = int(form["ndown"])
        if arguments["ndown"] < 0:
            raise ValueError
    except ValueError:
        arguments.pop("ndown", None)
        errors["ndown"] = "This must be a whole number, 0 or more."
    if form["domain"] in DOMAIN_REGIONS:
        arguments["domain"] = form["domain"]
    else:
        errors["domain"] = "Choose one of the domains."
    for name in ("start", "end"):
        try:
            arguments[name] = int(form[name])
        except ValueError:
            errors[name] = f"{name.title()} must be a year, e.g. 2011."
    if (
        "start" in arguments
        and "end" in arguments
        and arguments["end"] < arguments["start"]
    ):
        errors["end"] = "End must not be before start."
    # the file filters, as words separated by spaces
    arguments["exclude"] = form["exclude"].split() or None
    arguments["require"] = form["require"].split() or None
    if not form["out"]:
        errors["out"] = "Enter the file to write the script to."
    elif os.path.isdir(_path(form["out"], cwd)):
        errors["out"] = "This is a directory. Add the name of the script."
    else:
        arguments["out"] = _path(form["out"], cwd)
    return arguments, errors


def check_validate(form, cwd):
    """Turn the report options step's boxes into validate() arguments.

    Returns (arguments, errors), as check_setup does. validate's own checks
    of the matchups and of a regions file are made here, so that what they
    find is shown beside the box rather than after the run has started.
    """
    form = _form(form, default_validate_form())
    errors = {}

    def text(name):
        # a regions file is relative to the directory worked in, too
        if name == "subregions_file" and form[name]:
            return _path(form[name], cwd)
        return form[name]

    arguments = {
        "data_dir": _path(form["data_dir"] or ".", cwd),
        "out_dir": _path(form["out_dir"] or ".", cwd),
    }
    try:
        oceanval._check_matchups(arguments["data_dir"])
    except ValueError as error:
        errors["data_dir"] = str(error)
    if os.path.isfile(arguments["out_dir"]):
        errors["out_dir"] = "This is a file, not a directory."
    limits = recipes_gui.check_limits(text, errors)
    if limits is not None:
        arguments["lon_lim"], arguments["lat_lim"] = limits
    subregions = recipes_gui.check_subregions(text, errors)
    if subregions not in (None, "nwes", "global"):
        try:
            oceanval._check_region_file(subregions)
        except ValueError as error:
            errors["subregions_file"] = str(error)
    if subregions is not None:
        arguments["subregions"] = subregions
    for name in ("fixed_scale", "pdf", "word", "zip"):
        if form[name]:
            arguments[name] = True
    return arguments, errors


def _validate_call(arguments, cwd):
    """How a validate run is shown: the call it makes."""
    shown = {
        name: _shown(value, cwd) if name in ("data_dir", "out_dir") else value
        for name, value in arguments.items()
    }
    listed = ", ".join(f"{name}={_literal(value)}" for name, value in shown.items())
    return f"oceanval.validate({listed})"


def _partial_marker(text):
    """How much of the end of text could be the start of a question."""
    for size in range(min(len(text), len(QUESTION_MARKER) - 1), 0, -1):
        if QUESTION_MARKER.startswith(text[-size:]):
            return size
    return 0


class Console:
    """What has been printed, which the page reads in pieces as it comes.

    Everything is also written to the terminal oceanval was started from.
    Only the last LIMIT characters are kept. clear() starts afresh, for the
    next run, which the page finds out from epoch.
    """

    LIMIT = 5_000_000

    def __init__(self, changed):
        self._changed = changed
        self._lock = threading.Lock()
        self._chunks = []
        self._size = 0
        self._last = 0
        self.epoch = 1
        self.dropped = False

    def write(self, text):
        if not text:
            return
        with self._lock:
            self._last += 1
            self._chunks.append((self._last, text))
            self._size += len(text)
            while self._size > self.LIMIT and len(self._chunks) > 1:
                _, old = self._chunks.pop(0)
                self._size -= len(old)
                self.dropped = True
        self.note(text)
        self._changed()

    def empty(self):
        with self._lock:
            return not self._chunks

    def note(self, text):
        """Write text to the terminal only."""
        try:
            sys.__stdout__.write(text)
            sys.__stdout__.flush()
        except (AttributeError, OSError, ValueError):
            # no terminal to write to
            pass

    def clear(self):
        with self._lock:
            self._chunks = []
            self._size = 0
            self.epoch += 1
            self.dropped = False
        self._changed()

    def since(self, after, epoch):
        """The text printed since chunk number after of epoch, for the page.

        "reset" says the page should start its copy afresh: it is from
        another epoch, or has missed chunks dropped to keep within LIMIT.
        """
        with self._lock:
            reset = epoch != self.epoch or (
                bool(self._chunks) and self._chunks[0][0] > after + 1
            )
            if reset:
                after = 0
            return {
                "epoch": self.epoch,
                "text": "".join(
                    text for number, text in self._chunks if number > after
                ),
                "last": self._last,
                "reset": reset,
                "dropped": self.dropped,
            }


class _ConsoleStream(io.TextIOBase):
    """Stands in for sys.stdout and sys.stderr while create_recipes runs, so
    that what it prints reaches the page too."""

    def __init__(self, console):
        self._console = console

    def writable(self):
        return True

    def write(self, text):
        self._console.write(text)
        return len(text)


class Question:
    """A question put in the page, and what to do with its answer."""

    _numbers = itertools.count(1)

    def __init__(self, text, choices, respond):
        self.id = next(Question._numbers)
        self.text = text
        self.choices = list(choices) if choices else None
        self.respond = respond

    def as_dict(self):
        return {"id": self.id, "text": self.text, "choices": self.choices}


class Run:
    """matchup or validate, running in a process of its own.

    args are oceanval.app_child's. Its output goes to console, each question
    it asks to ask(question, choices, respond), and finished(run) is called
    once it has stopped.
    """

    def __init__(self, args, cwd, console, ask, finished):
        self.args = list(args)
        self.cwd = cwd
        self.console = console
        self._ask = ask
        self._finished = finished
        self.process = None
        self.returncode = None
        self.stopped = False
        self._reader = None

    def start(self):
        # the same oceanval as this process, wherever that was imported from,
        # rather than whichever the directory worked in would give
        root = os.path.dirname(os.path.dirname(os.path.abspath(oceanval.__file__)))
        code = (
            f"import sys; sys.path.insert(0, {root!r}); "
            "from oceanval.app_child import main; main()"
        )
        self.process = subprocess.Popen(
            [sys.executable, "-u", "-c", code, *self.args],
            cwd=self.cwd,
            env=dict(os.environ, PYTHONUNBUFFERED="1"),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            # in the order it was printed, as a terminal shows it
            stderr=subprocess.STDOUT,
            # a process group of its own, so that Stop reaches everything it
            # starts, and Ctrl+C in the terminal reaches oceanval first
            start_new_session=True,
        )
        self._reader = threading.Thread(
            target=self._read, name="oceanval-run-output", daemon=True
        )
        self._reader.start()
        threading.Thread(target=self._wait, name="oceanval-run", daemon=True).start()

    def _read(self):
        decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        pending = ""
        stream = self.process.stdout.fileno()
        while True:
            try:
                data = os.read(stream, 65536)
            except OSError:
                break
            if not data:
                break
            pending = self._take(pending + decoder.decode(data))
        self.console.write(pending + decoder.decode(b"", final=True))

    def _take(self, text):
        """Pass text on to the console, and questions to ask. Returns what
        is left over: an unfinished question, or what might start one."""
        while True:
            start = text.find(QUESTION_MARKER)
            if start < 0:
                keep = _partial_marker(text)
                self.console.write(text[: len(text) - keep])
                return text[len(text) - keep :]
            self.console.write(text[:start])
            end = text.find("\n", start)
            if end < 0:
                return text[start:]
            try:
                question = json.loads(text[start + len(QUESTION_MARKER) : end])
                self._ask(question["question"], question.get("choices"), self.answer)
            except (ValueError, KeyError, TypeError):
                # printed by something else, then
                self.console.write(text[start : end + 1])
            text = text[end + 1 :]

    def answer(self, text):
        try:
            self.process.stdin.write((text + "\n").encode("utf-8"))
            self.process.stdin.flush()
        except (OSError, ValueError):
            # it has already stopped
            pass

    def _wait(self):
        self.returncode = self.process.wait()
        # something it started can hold its output open after it has gone,
        # so that is not waited for forever
        self._reader.join(timeout=5)
        with contextlib.suppress(OSError, ValueError):
            self.process.stdin.close()
        self._finished(self)

    def running(self):
        return self.process is not None and self.process.poll() is None

    def stop(self):
        """Stop the run, and everything it has started."""
        if not self.running():
            return
        self.stopped = True
        self._signal(signal.SIGTERM)
        threading.Thread(target=self._kill_later, daemon=True).start()

    def _kill_later(self):
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self._signal(signal.SIGKILL)

    def _signal(self, number):
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(self.process.pid, number)

    def join(self, timeout=None):
        if self.process is not None:
            with contextlib.suppress(subprocess.TimeoutExpired):
                self.process.wait(timeout=timeout)


class App:
    """What the oceanval window shows, and the server showing it.

    view is the step the page is on: "start", then "setup", "own_data" (whether
    there are observations of your own), "point_data" and "gridded_data" (adding
    them), "preparing" (while create_recipes reads the simulation) and
    "recipes" (its window) to match up, then "units_check" (whether the model's
    and the observations' units match up) and "units_table" (their units, and
    a conversion for each), or "validate" for the report options, and then
    "running" and "finished". Everything the page does goes through the methods here,
    which the server's threads call.
    """

    def __init__(self, cwd=None):
        self.cwd = os.path.abspath(cwd or os.getcwd())
        self.token = secrets.token_urlsafe(24)
        self.url = None
        self.port = None
        self.closed = threading.Event()
        self._lock = threading.RLock()
        self._changed = threading.Condition(self._lock)
        self.version = 0
        self.console = Console(self._notify)
        self.view = "start"
        self.action = None
        self.setup_form = default_setup_form()
        self.setup_error = None
        self.setup_arguments = None
        # the user's own observations, as the arguments of the calls to
        # register them
        self.own_data = {"point": [], "gridded": []}
        self.validate_form = default_validate_form()
        self.question = None
        self.recipes_page = None
        # the matchups' units, while the units step is being shown, and the
        # recipes window's choices, which the step can add conversions to
        self.units_rows = None
        self.units_choices = None
        self.units_model_units = None
        self._units_done = threading.Event()
        self._units_conversions = None
        self.run = None
        self.run_label = None
        self.status = None
        self.returncode = None
        self.results_dir = None
        self._server = None

    # ---- state ----

    def _notify(self):
        with self._changed:
            self.version += 1
            self._changed.notify_all()

    def authorised(self, token):
        return secrets.compare_digest(
            str(token).encode("utf-8"), self.token.encode("utf-8")
        )

    def state(self, after=0, epoch=None, version=None, timeout=20, console=True):
        """What the page shows, and what has been printed since it last
        asked. Given the version the page has, waits up to timeout seconds
        for something to change first. Without console, what has been
        printed is left for the page to ask for."""
        with self._changed:
            if version is not None:
                self._changed.wait_for(
                    lambda: self.version != version or self.closed.is_set(), timeout
                )
            report = None
            if self.action in ("matchup_validate", "validate") and self.results_dir:
                report = os.path.join(self.results_dir, "oceanval_report.html")
            return {
                "version": self.version,
                "closed": self.closed.is_set(),
                "view": self.view,
                "action": self.action,
                "cwd": self.cwd,
                "setup": {"form": self.setup_form, "error": self.setup_error},
                "validate": {"form": self.validate_form},
                "own": {
                    "entries": self.own_data,
                    "fields": own_data.FIELDS,
                },
                "units": {"rows": self.units_rows},
                "question": self.question.as_dict() if self.question else None,
                "run": {
                    "label": self.run_label,
                    "status": self.status,
                    "returncode": self.returncode,
                    "results": self.results_dir,
                    "matchups": (
                        os.path.join(self.results_dir, "oceanval_matchups")
                        if self.results_dir
                        else None
                    ),
                    "report": report,
                    "report_exists": bool(report and os.path.exists(report)),
                },
                "console": (
                    self.console.since(after, epoch)
                    if console
                    else {
                        "epoch": None,
                        "text": "",
                        "last": 0,
                        "reset": True,
                        "dropped": False,
                    }
                ),
            }

    def html(self):
        return recipes_gui.render_page(
            "oceanval_app.html",
            {
                "token": self.token,
                "domains": [[key, region] for key, region in DOMAIN_REGIONS.items()],
                # what has been printed can be long, so the page asks for it
                "state": self.state(console=False),
            },
        )

    # ---- the steps ----

    def choose(self, action, data_dir=None):
        """Take the first step: match up and validate, match up only, or
        validate. data_dir fills in the matchups to validate."""
        with self._lock:
            if action not in ACTIONS or self.view not in ("start", "finished"):
                return False
            self.action = action
            self.question = None
            if action == "validate":
                if data_dir:
                    self.validate_form["data_dir"] = _shown(data_dir, self.cwd)
                self.view = "validate"
            else:
                self.setup_error = None
                self.view = "setup"
            self._notify()
            return True

    def back(self):
        with self._lock:
            earlier = {
                "setup": "start",
                "validate": "start",
                "own_data": "setup",
                "point_data": "own_data",
                "gridded_data": "point_data",
                "units_table": "units_check",
            }
            if self.view not in earlier:
                return False
            self.view = earlier[self.view]
            self._notify()
            return True

    def restart(self):
        with self._lock:
            if self.view != "finished":
                return False
            self.view = "start"
            self.action = None
            self._notify()
            return True

    def setup(self, form):
        """Read the simulation with create_recipes, from the simulation step's
        boxes. Returns the HTTP status and the reply for the page."""
        with self._lock:
            if self.view != "setup":
                return 409, {"ok": False, "error": "This step is over."}
            self.setup_form = _form(form, default_setup_form())
            arguments, errors = check_setup(self.setup_form, self.cwd)
            if errors:
                self._notify()
                return 400, {"ok": False, "errors": errors}
            self.setup_error = None
            self.setup_arguments = arguments
            self.view = "own_data"
            self._notify()
        return 200, {"ok": True}

    # ---- the user's own observations ----

    def has_own_data(self, answer):
        """Answer whether there are observations of your own to add. If not,
        the recipes are next."""
        with self._lock:
            if self.view != "own_data":
                return False
            if answer:
                self.view = "point_data"
                self._notify()
                return True
            self.own_data = {"point": [], "gridded": []}
        self._begin_prepare()
        return True

    def add_own_data(self, kind, form):
        """Add one entry of point or gridded data. Returns the HTTP status
        and the reply for the page."""
        with self._lock:
            if kind not in own_data.KINDS or self.view != f"{kind}_data":
                return 409, {"ok": False, "error": "This step is over."}
            existing = [
                (other, arguments)
                for other in own_data.KINDS
                for arguments in self.own_data[other]
            ]
        # outside the lock: it can open files
        arguments, errors = own_data.check_entry(kind, form, existing, self.cwd)
        if errors:
            return 400, {"ok": False, "errors": errors}
        with self._lock:
            if self.view != f"{kind}_data":
                return 409, {"ok": False, "error": "This step is over."}
            self.own_data[kind].append(arguments)
            self._notify()
        return 200, {"ok": True}

    def remove_own_data(self, kind, index):
        with self._lock:
            if (
                kind not in own_data.KINDS
                or self.view != f"{kind}_data"
                or isinstance(index, bool)
                or not isinstance(index, int)
                or not 0 <= index < len(self.own_data[kind])
            ):
                return False
            del self.own_data[kind][index]
            self._notify()
            return True

    def next_own_data(self):
        """Move on from the point data step, to the gridded data step, and
        from that to the recipes."""
        with self._lock:
            if self.view == "point_data":
                self.view = "gridded_data"
                self._notify()
                return True
            if self.view != "gridded_data":
                return False
        self._begin_prepare()
        return True

    def _before_recipes(self):
        """The step Back from the recipes goes to: the last of the steps
        for the user's own observations, if they were used."""
        return "gridded_data" if any(self.own_data.values()) else "own_data"

    def _begin_prepare(self):
        with self._lock:
            arguments = self.setup_arguments
            self.status = None
            self.view = "preparing"
            self.console.clear()
            self._notify()
        threading.Thread(
            target=self._prepare,
            args=(arguments,),
            name="oceanval-recipes",
            daemon=True,
        ).start()

    def _prepare(self, arguments):
        stream = _ConsoleStream(self.console)
        try:
            with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
                with prompts.answered_by(self._ask_in_window), recipes_gui.hosted_by(
                    self
                ):
                    out = create_recipes(
                        **arguments,
                        ask=True,
                        gui=True,
                        validate=self.action == "matchup_validate",
                        own_data=self.own_data,
                    )
        except Exception as error:
            # create_recipes' own checks say what to change; anything else
            # is worth seeing in full
            if not isinstance(error, (ValueError, TypeError)):
                self.console.write(traceback.format_exc())
            with self._lock:
                self.setup_error = str(error)
                self.view = "setup"
                self._notify()
            return
        if out is None or self.closed.is_set():
            # Back, in the recipes window
            with self._lock:
                if self.view in ("preparing", "recipes") and not self.closed.is_set():
                    self.view = self._before_recipes()
                    self._notify()
            return
        self.start_run(["script", out], f"python {_shown(out, self.cwd)}")

    def show_recipes(self, page):
        """Show the create_recipes window as the recipes step, and wait for
        it to be finished with (see recipes_gui.hosted_by)."""
        page.token = self.token
        page.context["app"] = {"action": self.action}
        with self._lock:
            if self.closed.is_set():
                return None
            self.recipes_page = page
            self.view = "recipes"
            self._notify()
        result = page.wait()
        with self._lock:
            self.recipes_page = None
            if result is None:
                self.view = self._before_recipes()
                self._notify()
                return result
            # the matchups, and the report, go where the settings say
            self.results_dir = _path(result[2].get("out_dir") or ".", self.cwd)
            self.units_choices = result
            self.units_rows = None
            self.units_model_units = None
            self._units_conversions = None
            self._units_done.clear()
            self.view = "units_check"
            self._notify()
        while not self._units_done.wait(0.25):
            if self.closed.is_set():
                return result
        with self._lock:
            conversions = self._units_conversions
            result = self.units_choices
        if conversions:
            result = self._convert_units(page, result, conversions)
        with self._lock:
            self.units_choices = None
            self.view = "running"
            self.status = "starting"
            self._notify()
        return result

    def _convert_units(self, page, result, conversions):
        """Write the script again with the conversions chosen in the units
        step, and return the recipes window's choices with them added."""
        mapping, selection, settings, point_options, gridded_options = result
        gridded_options = {key: dict(value) for key, value in gridded_options.items()}
        point_options = {key: dict(value) for key, value in point_options.items()}
        units.apply_conversions(
            conversions, gridded_options, self.own_data, point_options
        )
        page.write(mapping, selection, settings, point_options, gridded_options)
        return mapping, selection, settings, point_options, gridded_options

    # ---- the units step ----

    def units_answer(self, match):
        """Answer whether the model's and the observations' units match up.
        If they do, carry on; if not, show their units."""
        with self._lock:
            if self.view != "units_check":
                return False
            if match:
                self._units_done.set()
                return True
            mapping, selection, settings, point_options, gridded_options = (
                self.units_choices
            )
            simdir, ndown = self.setup_arguments["simdir"], self.setup_arguments["ndown"]
            names = units.model_variables(mapping, selection, self.own_data)
        # reads the simulation's files, so not with the lock held
        model_units = units.model_units(
            simdir,
            ndown,
            names,
            # the window can change the file filters along with the rest
            exclude=settings.get("exclude"),
            require=settings.get("require"),
        )
        rows = units.matchups(
            mapping,
            selection,
            gridded_options,
            point_options,
            self.own_data,
            model_units,
            self.cwd,
        )
        with self._lock:
            if self.view != "units_check":
                return False
            self.units_rows = rows
            self.view = "units_table"
            self._notify()
        return True

    def units_continue(self, sent):
        """Carry on from the units table, with the conversions its boxes
        hold. Returns the HTTP status and the reply for the page."""
        with self._lock:
            if self.view != "units_table":
                return 409, {"ok": False, "error": "That cannot be done now."}
            keys = {row["key"] for row in self.units_rows or []}
        conversions, errors = units.check_conversions(sent)
        errors.update({key: "This matchup is not in the table." for key in conversions if key not in keys})
        if errors:
            return 400, {"ok": False, "errors": errors}
        # only what differs from what the script already has
        changed = {}
        for row in self.units_rows:
            chosen = conversions.get(row["key"])
            if chosen and chosen != (row["obs_multiplier"], row["obs_adder"]):
                changed[row["key"]] = chosen
        with self._lock:
            if self.view != "units_table":
                return 409, {"ok": False, "error": "That cannot be done now."}
            self._units_conversions = changed
            self._units_done.set()
        return 200, {"ok": True}

    def validate(self, form):
        """Build the report, from the report options step's boxes."""
        with self._lock:
            if self.view != "validate":
                return 409, {"ok": False, "error": "This step is over."}
            self.validate_form = _form(form, default_validate_form())
            form = dict(self.validate_form)
        # outside the lock: reading a regions file can take a moment
        arguments, errors = check_validate(form, self.cwd)
        if errors:
            return 400, {"ok": False, "errors": errors}
        with self._lock:
            if self.view != "validate":
                return 409, {"ok": False, "error": "This step is over."}
            # so that a second click does not start a second run
            self.view = "running"
            self.status = "starting"
            self.results_dir = arguments["out_dir"]
            self.console.clear()
        self.start_run(
            ["validate", json.dumps(arguments)], _validate_call(arguments, self.cwd)
        )
        return 200, {"ok": True}

    def probe(self, simdir, ndown, out, exclude="", require=""):
        """What the simulation step says about the simulation as it is typed
        in: whether the directory is there, how many output files are ndown
        directories below it that pass the file filters (exclude and
        require, as words separated by spaces) - and how many there are
        without them - the years their names cover, and, if there are none
        there at all, a depth that has some."""
        filters = {
            "exclude": exclude.split() or None,
            "require": require.split() or None,
        }
        filtered = bool(filters["exclude"] or filters["require"])
        found = {
            "directory": "empty",
            "ndown": None,
            "files": None,
            "all_files": None,
            "years": None,
            "suggestion": None,
        }
        found["out_exists"] = bool(out.strip()) and os.path.isfile(
            _path(out.strip(), self.cwd)
        )
        if not simdir.strip():
            return found
        path = _path(simdir.strip(), self.cwd)
        if not os.path.isdir(path):
            found["directory"] = "missing"
            return found
        found["directory"] = "found"
        try:
            depth = int(ndown)
            if depth < 0:
                raise ValueError
        except ValueError:
            depth = None
        found["ndown"] = depth
        if depth is not None:
            paths = simulation_paths(path, depth, **filters)
            found["files"] = len(paths)
            found["all_files"] = (
                len(simulation_paths(path, depth)) if filtered else len(paths)
            )
            if paths:
                years = simulation_years(path, paths)
                found["years"] = list(years) if years else None
                return found
            if found["all_files"]:
                # the depth is right, and the filters leave out every file
                return found
        for other in _SEARCH_DEPTHS:
            if other == depth:
                continue
            paths = simulation_paths(path, other, **filters)
            if paths:
                years = simulation_years(path, paths)
                found["suggestion"] = {
                    "ndown": other,
                    "files": len(paths),
                    "years": list(years) if years else None,
                }
                break
        return found

    def sample_files(self, simdir, ndown, avoid=""):
        """The netCDF files in one directory of the simulation, chosen at
        random from those ndown directories below simdir that hold any, for
        the page to show what the file names look like - the names the file
        filters are made of. avoid is a directory not to choose again, if
        there is another.

        Every file is listed, whatever the file filters say, and none is left
        out for being a restart file, so the page can show what there is to
        filter.
        """
        found = {
            "directory": "empty",
            "ndown": None,
            "path": None,
            "directories": 0,
            "files": [],
            "more": 0,
        }
        if not simdir.strip():
            return found
        path = _path(simdir.strip(), self.cwd)
        if not os.path.isdir(path):
            found["directory"] = "missing"
            return found
        found["directory"] = "found"
        try:
            depth = int(ndown)
            if depth < 0:
                raise ValueError
        except ValueError:
            return found
        found["ndown"] = depth
        pattern = os.path.join(path, *(["*"] * depth), "*.nc")
        directories = sorted({os.path.dirname(file) for file in glob.glob(pattern)})
        found["directories"] = len(directories)
        if not directories:
            return found
        avoided = _path(avoid, self.cwd) if avoid.strip() else None
        chosen = random.choice(
            [directory for directory in directories if directory != avoided]
            or directories
        )
        files = sorted(
            (name for name in os.listdir(chosen) if name.endswith(".nc")),
            key=lambda name: (name.lower(), name),
        )
        found["path"] = _shown(chosen, self.cwd)
        found["files"] = files[:_MOST_FILES]
        found["more"] = max(0, len(files) - _MOST_FILES)
        return found

    def browse(self, path):
        """What one directory holds, for the page's folder browser and the
        folders it suggests as a path is typed: its folders, how many netCDF
        files are directly in it, and whether it has matchups.

        path is as typed, relative to the working directory. If it is not a
        directory, the nearest one above it is listed instead, and exact is
        False. The listing is of the machine oceanval runs on, which the
        browser need not be on, so it cannot use a folder picker of its own.
        """
        requested = _path(path.strip() or ".", self.cwd)
        directory = requested
        while not os.path.isdir(directory) and os.path.dirname(directory) != directory:
            directory = os.path.dirname(directory)
        parent = os.path.dirname(directory)
        found = {
            "path": directory,
            "shown": _shown(directory, self.cwd),
            "parent": None if parent == directory else parent,
            "exact": directory == requested,
            "folders": [],
            "more": 0,
            "nc_files": 0,
            "example": None,
            "has_matchups": False,
            "error": None,
            "places": [
                {"label": "Working directory", "path": self.cwd},
                {"label": "Home", "path": os.path.expanduser("~")},
            ],
        }
        folders, files = [], []
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    try:
                        if entry.is_dir():
                            if not entry.name.startswith("."):
                                folders.append(entry.name)
                        elif entry.name.endswith(".nc"):
                            files.append(entry.name)
                    except OSError:
                        # e.g. a link to something that has gone
                        continue
        except PermissionError:
            found["error"] = "You do not have permission to open this directory."
            return found
        except OSError as error:
            found["error"] = (
                f"This directory cannot be opened: {error.strerror or error}."
            )
            return found
        folders.sort(key=lambda name: (name.lower(), name))
        found["folders"] = [
            {"name": name, "path": os.path.join(directory, name)}
            for name in folders[:_MOST_FOLDERS]
        ]
        found["more"] = max(0, len(folders) - _MOST_FOLDERS)
        found["nc_files"] = len(files)
        found["example"] = min(files) if files else None
        found["has_matchups"] = "oceanval_matchups" in folders
        return found

    # ---- the run ----

    def start_run(self, args, label):
        run = Run(args, self.cwd, self.console, self._put_question, self._run_finished)
        with self._lock:
            if self.closed.is_set():
                return
            self.run = run
            self.run_label = label
            self.status = "running"
            self.returncode = None
            self.question = None
            self.view = "running"
            self._notify()
        # set apart from what create_recipes printed before it
        separator = "" if self.console.empty() else "\n"
        self.console.write(f"{separator}$ {label}\n")
        try:
            run.start()
        except OSError as error:
            self.console.write(f"The run could not be started: {error}\n")
            run.returncode = -1
            self._run_finished(run)

    def _run_finished(self, run):
        with self._lock:
            if run is not self.run:
                return
            if run.stopped:
                self.status = "stopped"
            else:
                self.status = "finished" if run.returncode == 0 else "failed"
            self.returncode = run.returncode
            self.question = None
            self.view = "finished"
            self._notify()
        self.console.note(
            "\nOceanVal: the run has "
            + {"stopped": "been stopped", "finished": "finished", "failed": "failed"}[
                self.status
            ]
            + ". Start again or quit in the window, or press Ctrl+C to quit.\n"
        )

    def stop(self):
        with self._lock:
            run = self.run if self.view == "running" else None
        if run is None:
            return False
        run.stop()
        return True

    # ---- questions ----

    def _put_question(self, text, choices, respond):
        with self._lock:
            self.question = Question(text, choices, respond)
            self._notify()
        # as a terminal shows a question: at the end of the output, which the
        # answer then follows
        self.console.write(text)
        self.console.note("(answer this in the OceanVal window) ")

    def _ask_in_window(self, text, choices):
        """Ask a question in the page, for prompts.answered_by."""
        answers = queue.Queue()
        self._put_question(text, choices, answers.put)
        while True:
            try:
                return answers.get(timeout=0.25)
            except queue.Empty:
                if self.closed.is_set():
                    raise EOFError(
                        "OceanVal was closed before the question was answered"
                    )

    def answer(self, number, text):
        """Answer the question numbered number, if it is still being asked."""
        # one line, as typed at a terminal
        text = str(text).replace("\r", " ").replace("\n", " ")
        with self._lock:
            question = self.question
            if question is None or question.id != number:
                return False
            self.question = None
            self._notify()
        self.console.write(text + "\n")
        question.respond(text)
        return True

    # ---- the server ----

    def start(self, port=0):
        """Serve the page, and return its link."""
        handler = type("Handler", (_Handler,), {"app": self})
        self._server = recipes_gui._Server(("127.0.0.1", port), handler)
        self.port = self._server.server_address[1]
        self.url = f"http://127.0.0.1:{self.port}/?token={self.token}"
        threading.Thread(
            target=self._server.serve_forever, name="oceanval-window", daemon=True
        ).start()
        return self.url

    def quit(self):
        """Stop whatever is running, and let main() return."""
        with self._lock:
            if self.closed.is_set():
                return
            self.closed.set()
            run, page = self.run, self.recipes_page
            self._notify()
        if run is not None:
            run.stop()
        if page is not None:
            page.cancel()
            page.finish()

    def close(self):
        self.quit()
        if self.run is not None:
            self.run.join(timeout=6)
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None


def _number(text):
    try:
        return int(text)
    except (TypeError, ValueError):
        return None


class _Handler(recipes_gui._Handler):
    app = None  # set on the subclass each App makes

    def _redirect(self, location):
        self.send_response(303)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def do_GET(self):
        url = urllib.parse.urlsplit(self.path)
        query = {
            key: values[0] for key, values in urllib.parse.parse_qs(url.query).items()
        }
        if url.path not in (
            "/",
            "/recipes/",
            "/api/state",
            "/api/probe",
            "/api/browse",
            "/api/files",
        ):
            self._reply(404, "Not found", "text/plain; charset=utf-8")
        elif not self.app.authorised(query.get("token", "")):
            self._reply(
                403,
                "This is not the link oceanval printed.",
                "text/plain; charset=utf-8",
            )
        elif url.path == "/":
            self._reply(200, self.app.html(), "text/html; charset=utf-8")
        elif url.path == "/recipes/":
            page = self.app.recipes_page
            if page is None:
                # the recipes step is over
                self._redirect("/?token=" + urllib.parse.quote(self.app.token))
            else:
                self._reply(200, page.html(), "text/html; charset=utf-8")
        elif url.path == "/api/state":
            self._reply_json(
                200,
                self.app.state(
                    after=_number(query.get("after")) or 0,
                    epoch=_number(query.get("epoch")),
                    version=_number(query.get("version")),
                ),
            )
        elif url.path == "/api/browse":
            self._reply_json(200, self.app.browse(query.get("path", "")))
        elif url.path == "/api/files":
            self._reply_json(
                200,
                self.app.sample_files(
                    query.get("simdir", ""),
                    query.get("ndown", ""),
                    query.get("avoid", ""),
                ),
            )
        else:
            self._reply_json(
                200,
                self.app.probe(
                    query.get("simdir", ""),
                    query.get("ndown", ""),
                    query.get("out", ""),
                    query.get("exclude", ""),
                    query.get("require", ""),
                ),
            )

    def do_POST(self):
        path = urllib.parse.urlsplit(self.path).path
        if not self.app.authorised(self.headers.get("X-OceanVal-Token", "")):
            self._reply_json(403, {"ok": False, "error": "Forbidden"})
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
            payload = json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            self._reply_json(
                400, {"ok": False, "error": "The request could not be read."}
            )
            return
        payload = payload if isinstance(payload, dict) else {}

        if path in ("/recipes/write", "/recipes/cancel"):
            self._recipes(path, payload)
            return
        app = self.app
        if path == "/api/setup":
            self._reply_json(*app.setup(payload.get("form")))
            return
        if path == "/api/validate":
            self._reply_json(*app.validate(payload.get("form")))
            return
        if path == "/api/units_continue":
            self._reply_json(*app.units_continue(payload.get("conversions")))
            return
        if path == "/api/own_add":
            self._reply_json(
                *app.add_own_data(payload.get("kind"), payload.get("form"))
            )
            return
        if path == "/api/quit":
            try:
                self._reply_json(200, {"ok": True})
            finally:
                app.quit()
            return
        steps = {
            "/api/choose": lambda: app.choose(
                payload.get("action"), payload.get("data_dir")
            ),
            "/api/own_data": lambda: app.has_own_data(bool(payload.get("answer"))),
            "/api/own_remove": lambda: app.remove_own_data(
                payload.get("kind"), payload.get("index")
            ),
            "/api/own_next": app.next_own_data,
            "/api/units_answer": lambda: app.units_answer(bool(payload.get("match"))),
            "/api/back": app.back,
            "/api/restart": app.restart,
            "/api/stop": app.stop,
            "/api/answer": lambda: app.answer(
                payload.get("id"), payload.get("answer", "")
            ),
        }
        if path not in steps:
            self._reply_json(404, {"ok": False, "error": "Not found"})
        elif steps[path]():
            self._reply_json(200, {"ok": True})
        else:
            self._reply_json(409, {"ok": False, "error": "That cannot be done now."})

    def _recipes(self, path, payload):
        """The create_recipes window's own requests, as its server answers
        them."""
        page = self.app.recipes_page
        if page is None:
            self._reply_json(409, {"ok": False, "error": "The recipes step is over."})
        elif path.endswith("/write"):
            status, reply = page.submit(payload)
            try:
                self._reply_json(status, reply)
            finally:
                # only now, so the reply is sent before create_recipes returns
                if reply["ok"]:
                    page.finish()
        else:
            page.cancel()
            try:
                self._reply_json(200, {"ok": True})
            finally:
                page.finish()


def main(argv=None):
    """The oceanval command."""
    parser = argparse.ArgumentParser(
        prog="oceanval",
        description=(
            "Validate an ocean model in a window in your web browser: match "
            "its output up with observations, and build the validation "
            "report. Run it in the directory to work in."
        ),
    )
    parser.add_argument(
        "--port",
        type=int,
        default=0,
        help="the port to serve the window on, e.g. to forward it from a "
        "remote machine (default: any free port)",
    )
    arguments = parser.parse_args(argv)

    app = App()
    try:
        url = app.start(arguments.port)
    except OSError as error:
        parser.exit(
            1,
            f"oceanval: port {arguments.port} cannot be used ({error.strerror or error}). "
            "Choose another with --port.\n",
        )
    if recipes_gui._can_open_browser() and recipes_gui._open_browser(url):
        print(
            f"OceanVal is open in your web browser:\n  {url}\n"
            "Press Ctrl+C here to quit.",
            flush=True,
        )
    else:
        print(
            f"Open this link in a web browser to use OceanVal:\n  {url}\n"
            f"On a remote machine, forward port {app.port} to reach it (VS Code "
            "does this for you). Press Ctrl+C here to quit.",
            flush=True,
        )
    try:
        # waiting in steps, so Ctrl+C is not held up
        while not app.closed.wait(0.25):
            pass
        print("OceanVal was closed from its window.", flush=True)
    except KeyboardInterrupt:
        print("\nClosing OceanVal.", flush=True)
    finally:
        app.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
