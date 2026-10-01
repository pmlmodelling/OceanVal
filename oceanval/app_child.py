"""The process the oceanval command runs matchup and validate in.

    python -m oceanval.app_child script <path>
    python -m oceanval.app_child matchup <path>
    python -m oceanval.app_child validate <arguments as JSON>

The first runs a script create_recipes wrote, the second runs one without
its validate() call, which the window makes afterwards with the report
options chosen once the matchups are checked, and the third validate(). What
they print is shown in the oceanval window (see oceanval.app), which reads
it from this process's stdout. A question asked through oceanval.prompts is
written there as one line, QUESTION_MARKER followed by the question as JSON,
and the answer given in the window is read back from stdin.
"""

import json
import runpy
import sys
import webbrowser

QUESTION_MARKER = "\x1eoceanval-question "


def _ask_the_window(question, choices, details=None):
    # whatever was printed before the question belongs above it
    sys.stdout.flush()
    sys.stderr.flush()
    asked = {"question": question, "choices": choices}
    if details is not None:
        asked["details"] = details
    out = sys.__stdout__
    out.write(QUESTION_MARKER + json.dumps(asked))
    out.write("\n")
    out.flush()
    answer = sys.stdin.readline()
    if not answer:
        raise EOFError("The oceanval window stopped before the question was answered")
    return answer.rstrip("\r\n")


def _say_where(url, *args, **kwargs):
    """Stands in for webbrowser.open where no web browser can be opened."""
    print(f"Open this in a web browser to see it: {url}")
    return False


def _validate_later(*args, **kwargs):
    """Stands in for the script's validate(), which the window makes once
    the script has finished."""
    print("The report is built next, with the options chosen in the OceanVal window.")


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2 or argv[0] not in ("script", "matchup", "validate"):
        sys.exit(
            "usage: python -m oceanval.app_child script <path>\n"
            "       python -m oceanval.app_child matchup <path>\n"
            "       python -m oceanval.app_child validate <arguments as JSON>"
        )
    kind, argument = argv

    import oceanval
    from oceanval import prompts
    from oceanval.recipes_gui import _can_open_browser

    if not _can_open_browser():
        # validate opens the report itself, and without a display webbrowser
        # falls back on a text browser, which would wait for keys that never
        # come
        webbrowser.open = _say_where

    with prompts.answered_by(_ask_the_window):
        if kind in ("script", "matchup"):
            if kind == "matchup":
                oceanval.validate = _validate_later
            sys.argv = [argument]
            runpy.run_path(argument, run_name="__main__")
        else:
            oceanval.validate(**json.loads(argument))


if __name__ == "__main__":
    main()
