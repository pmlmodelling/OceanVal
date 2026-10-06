"""The boxes of the oceanval window's pages for registering recipes of your
own (see oceanval.user_recipes), and what is made of them.

default_form gives a page's boxes as they start. check_names says what is
wrong with the names in them, and where the recipe would be saved, as they
are typed; check_data looks at the data they point at (oceanval.recipe_checks);
and check_save does both, as the recipe is saved, and returns the recipe to
write to the file.
"""

import os

from oceanval import own_data, recipe_checks, user_recipes

KINDS = ("point", "gridded")

# each kind's boxes
_COMMON = (
    "variable",
    "source",
    "source_info",
    "long_name",
    "short_name",
    "short_title",
    "units",
    "where",
    "obs_path",
)
BOXES = {
    "point": _COMMON,
    "gridded": _COMMON + ("location", "obs_variable", "climatology"),
}

# what the window asks for, with the box it is asked in
REQUIRED = {
    "variable": "This is needed.",
    "source": "This is needed.",
    "source_info": "Say where the observations are from: it is shown in the report.",
    "units": "Give the units of the observations, e.g. mg m-3.",
    "where": "Choose where to save it.",
}


def default_form(kind):
    """The boxes of one kind's page, as they start."""
    form = {name: "" for name in BOXES[kind]}
    if kind == "gridded":
        form["location"] = "disk"
    return form


def clean(kind, form):
    """What a page sent, limited to its own boxes, as stripped text."""
    form = form if isinstance(form, dict) else {}
    defaults = default_form(kind)
    return {
        name: str(form.get(name, default) if form.get(name, default) is not None else "").strip()
        for name, default in defaults.items()
    }


def _location(kind, form):
    return "disk" if kind == "point" else form["location"]


def signature(kind, form, cwd=None):
    """What the data of a form is, as one thing that can be compared, or None
    if there is not enough in the boxes to tell."""
    location = _location(kind, form)
    if not form["obs_path"]:
        return None
    if location == "disk":
        return ["disk", recipe_checks.resolve(form["obs_path"], cwd)]
    return [location, recipe_checks.addresses(form["obs_path"])]


def is_remote(kind, form):
    return kind == "gridded" and form["location"] in ("thredds", "url")


def check_names(kind, form, cwd=None, strict=False):
    """What is wrong with the names and where a recipe is to be saved: the
    variable, the source and where. Returns (errors, warnings, info). While
    a form is being filled in (not strict), only what has been typed is
    looked at. info has the "key" and "recipe" the recipe would be used as,
    whether the variable is "known" (OceanVal has recipes for it, or you have
    registered some) and, if so, the "labels" it has in the report."""
    form = clean(kind, form)
    info = {"key": None, "recipe": None, "known": False, "labels": None}
    errors, warnings = {}, []
    if strict:
        for name, message in REQUIRED.items():
            if not form[name]:
                errors[name] = message
    variable, source, where = form["variable"], form["source"], form["where"]
    if variable:
        info["labels"] = user_recipes.labels(variable, cwd)
        info["known"] = info["labels"] is not None
    if variable and source:
        info["key"] = user_recipes.key_of(source)
        info["recipe"] = f'recipe={{"{variable.lower()}": "{info["key"]}"}}'
    if where:
        asked = {"variable": variable, "source": source, "kind": kind}
        found, notes = user_recipes.problems(asked, where, cwd)
        if not strict:
            # a blank box is for the box to say, when it is time
            found = {
                name: text
                for name, text in found.items()
                if name != "variable" or variable
                if name != "source" or source
            }
    else:
        found = user_recipes.name_problems(variable, source, strict=False)
        notes = []
    for name, text in found.items():
        errors.setdefault(name, text)
    return errors, (notes if not errors else []), info


def check_data(kind, form, cwd=None):
    """Look at the data of a form that is on this machine. Returns
    {"ok": True, "found": ...} with what recipe_checks found, or {"ok":
    False, "error": ...}. Data on a server is looked at by RemoteCheck."""
    form = clean(kind, form)
    if not form["obs_path"]:
        return {"ok": False, "error": ""}
    try:
        if kind == "point":
            return {"ok": True, "found": recipe_checks.inspect_point(form["obs_path"], cwd)}
        return {
            "ok": True,
            "found": recipe_checks.inspect_gridded("disk", form["obs_path"], cwd),
        }
    except recipe_checks.CheckFailed as error:
        return {"ok": False, "error": str(error)}
    except Exception as error:
        return {"ok": False, "error": recipe_checks._short(error)}


def _variable(found, name):
    for variable in found["variables"]:
        if variable["name"] == name:
            return variable
    return None


def check_save(kind, form, cwd=None, remote=None):
    """Everything about a form, before it is saved. remote is the reply of
    the check of data on a server (see check_data), which must have been
    made for the form's data. Returns (recipe, errors, warnings, data):
    recipe is what to write to the file, or None if there are errors, which
    map each box that cannot be used to the reason, with "" for one about
    the recipe as a whole; and data is what was found in the data."""
    form = clean(kind, form)
    errors, warnings, info = check_names(kind, form, cwd, strict=True)
    if kind == "gridded":
        if form["location"] not in recipe_checks.LOCATIONS:
            errors["location"] = "Choose where the data is."
        if not form["obs_variable"]:
            errors["obs_variable"] = "Choose the variable in the data to compare with."
        if form["climatology"] not in ("yes", "no"):
            errors["climatology"] = "Choose yes or no."
    if not form["obs_path"]:
        errors["obs_path"] = "This is needed."
    if errors:
        return None, errors, warnings, None

    data = None
    if is_remote(kind, form):
        wanted = signature(kind, form, cwd)
        if remote is None or remote.get("signature") != wanted:
            errors["obs_path"] = "Check the data first, with the button below."
        elif not remote.get("ok"):
            errors["obs_path"] = remote.get("error") or "The data could not be checked."
        else:
            data = remote["found"]
    else:
        reply = check_data(kind, form, cwd)
        if reply["ok"]:
            data = reply["found"]
        else:
            errors["obs_path"] = reply["error"]
    if errors:
        return None, errors, warnings, None

    recipe = {
        "variable": form["variable"].lower(),
        "kind": kind,
        "source": form["source"],
        "source_info": form["source_info"],
        "units": form["units"],
        "obs_path": data["obs_path"],
    }
    if kind == "point":
        recipe["depth_resolved"] = bool(data["depth"])
    else:
        chosen = _variable(data, form["obs_variable"])
        if chosen is None:
            errors["obs_variable"] = (
                f"{form['obs_variable']} is not in the data. It holds: "
                + ", ".join(variable["name"] for variable in data["variables"])
                + "."
            )
            return None, errors, warnings, data
        years = data.get("years")
        if form["climatology"] == "yes" and years and years[0] < years[1]:
            errors["climatology"] = (
                f"The data covers {years[0]} to {years[1]}, so it is not a climatology, "
                "which has one value for each month. Choose no."
            )
            return None, errors, warnings, data
        recipe.update(
            location=form["location"],
            obs_variable=form["obs_variable"],
            climatology=form["climatology"] == "yes",
            depth_resolved=chosen["nlevels"] > 1,
        )
    if not info["known"]:
        # a variable of the user's own is named for the report
        variable = form["variable"]
        recipe.update(
            long_name=form["long_name"] or variable,
            short_name=form["short_name"] or variable,
            short_title=form["short_title"] or variable.title(),
        )

    errors, warnings = user_recipes.problems(dict(recipe, **{"variable": form["variable"]}), form["where"], cwd)
    if errors:
        return None, errors, warnings, data

    if not is_remote(kind, form):
        # the calls that will register it say whether they can
        entry = {
            "name": form["variable"],
            "source": form["source"],
            "model_variable": "model",
            "obs_path": data["obs_path"],
        }
        if kind == "gridded":
            entry.update(
                obs_variable=form["obs_variable"], climatology=form["climatology"]
            )
        _, refused = own_data.check_entry(kind, entry, (), cwd or os.getcwd())
        refused = {
            name: text
            for name, text in refused.items()
            if name in ("", "obs_path", "obs_variable")
        }
        if refused:
            return None, refused, warnings, data
    return recipe, {}, warnings, data
