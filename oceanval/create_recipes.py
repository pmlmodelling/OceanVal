"""Write a ready-to-run matchup script for one simulation.

``create_recipes`` scans a simulation directory, works out which model
variable holds each observational variable OceanVal has a recipe for, and
writes out the script in ``docs-site/recipe-examples.py`` with those names
filled in. Recipes it could not find a model variable for are still written
out, but commented, so nothing is silently dropped.

The identification follows the approach ecoval takes in its ``matchup``:
model output rarely names its variables the way an observational dataset
does, so the match is made on the variables' ``long_name`` attributes
rather than on their names.
"""

import glob
import os
import re
import warnings

import nctoolkit as nc


# The region argument on create_recipes, keyed by the catalogue's own
# "region" label (used for the section heading each recipe is printed
# under).
DOMAIN_REGIONS = {
    "global": "Global",
    "nwes": "Northwest European Shelf",
}

# Every recipe on https://pmlmodelling.github.io/OceanVal/recipe-examples.py,
# in the order that page lists them. "arguments" are the source lines of the
# add_gridded_comparison call that follow the recipe, and "example_variable"
# is the placeholder name the page uses, kept for the commented-out blocks.
RECIPE_CATALOGUE = (
    {
        "variable": "alkalinity",
        "recipe": "glodap",
        "region": "Global",
        "example_variable": "talk",
        "notes": (
            "Alkalinity - GLODAPv2.2016b (https://www.glodap.info/)",
            "recipe: 'glodap'",
            "Annual climatology covering 1972–2013, surface-only. Reported in",
            "micromoles per kilogram. See the GLODAPv2 reference",
            "(https://doi.org/10.5194/essd-8-325-2016).",
        ),
        "arguments": ("climatology=True,",),
    },
    {
        "variable": "chlorophyll",
        "recipe": "occci",
        "region": "Global",
        "example_variable": "chl",
        "notes": (
            "Chlorophyll - Ocean Colour CCI (https://esa-oceancolour-cci.org/)",
            "recipe: 'occci'",
            "Surface chlorophyll, reported in milligrams per cubic metre. The occci",
            "recipe also provides KD490.",
        ),
        "arguments": ("climatology=False,",),
    },
    {
        "variable": "kd490",
        "recipe": "occci",
        "region": "Global",
        "example_variable": "kd490",
        "notes": (
            "KD490 - Ocean Colour CCI (https://esa-oceancolour-cci.org/)",
            "recipe: 'occci'",
            "Diffuse attenuation coefficient at 490 nm, reported in inverse metres.",
        ),
        "arguments": ("climatology=False,",),
    },
    {
        "variable": "nitrate",
        "recipe": "woa23",
        "region": "Global",
        "example_variable": "no3",
        "notes": (
            "Nitrate - World Ocean Atlas 2023 "
            "(https://www.ncei.noaa.gov/products/world-ocean-atlas)",
            "recipe: 'woa23'",
            "Vertically resolved to ~800 m. WOA23 nutrients use a single long-term",
            "climatology — see the WOA23 note below for temperature/salinity decadal",
            "periods.",
        ),
        "arguments": (
            "climatology=True,",
            "vertical=False,  # set True to validate the full water column",
        ),
    },
    {
        "variable": "oxygen",
        "recipe": "woa23",
        "region": "Global",
        "example_variable": "o2",
        "notes": (
            "Oxygen - World Ocean Atlas 2023 "
            "(https://www.ncei.noaa.gov/products/world-ocean-atlas)",
            "recipe: 'woa23'",
            "Vertically resolved to ~800 m.",
        ),
        "arguments": (
            "climatology=True,",
            "vertical=False,  # set True to validate the full water column",
        ),
    },
    {
        "variable": "ph",
        "recipe": "glodap",
        "region": "Global",
        "example_variable": "ph",
        "notes": (
            "pH - GLODAPv2.2016b (https://www.glodap.info/)",
            "recipe: 'glodap'",
            "Annual climatology, 1972–2013, surface-only. Reported on the total scale.",
        ),
        "arguments": ("climatology=True,",),
    },
    {
        "variable": "phosphate",
        "recipe": "woa23",
        "region": "Global",
        "example_variable": "po4",
        "notes": (
            "Phosphate - World Ocean Atlas 2023 "
            "(https://www.ncei.noaa.gov/products/world-ocean-atlas)",
            "recipe: 'woa23'",
            "Vertically resolved to ~800 m.",
        ),
        "arguments": (
            "climatology=True,",
            "vertical=False,  # set True to validate the full water column",
        ),
    },
    {
        "variable": "salinity",
        "recipe": "woa23",
        "region": "Global",
        "example_variable": "so",
        "decadal": True,
        "notes": (
            "Salinity - World Ocean Atlas 2023 "
            "(https://www.ncei.noaa.gov/products/world-ocean-atlas)",
            "recipe: 'woa23'",
            "Uses a decadal climatology — start/end must fall within one supported",
            "period (see below).",
        ),
        "arguments": (
            "climatology=True,",
            "vertical=False,  # set True to validate the full water column",
        ),
    },
    {
        "variable": "silicate",
        "recipe": "woa23",
        "region": "Global",
        "example_variable": "si",
        "notes": (
            "Silicate - World Ocean Atlas 2023 "
            "(https://www.ncei.noaa.gov/products/world-ocean-atlas)",
            "recipe: 'woa23'",
            "Vertically resolved to ~800 m.",
        ),
        "arguments": (
            "climatology=True,",
            "vertical=False,  # set True to validate the full water column",
        ),
    },
    {
        "variable": "temperature",
        "recipe": "cobe2",
        "region": "Global",
        "example_variable": "thetao",
        "notes": (
            "Temperature - COBE-SST 2 (https://psl.noaa.gov/data/gridded/data.cobe2.html)",
            "recipe: 'cobe2'",
            "Monthly sea surface temperature, useful for validating against a full time",
            "series rather than a climatology.",
        ),
        "arguments": ("climatology=False,",),
    },
    {
        "variable": "temperature",
        "recipe": "woa23",
        "region": "Global",
        "example_variable": "thetao",
        "decadal": True,
        "notes": (
            "Temperature - World Ocean Atlas 2023 "
            "(https://www.ncei.noaa.gov/products/world-ocean-atlas)",
            "recipe: 'woa23'",
            "Uses a decadal climatology, vertically resolved to ~800 m. start/end must",
            "fall within one supported period (see below).",
        ),
        "arguments": (
            "climatology=True,",
            "vertical=False,  # set True to validate the full water column",
        ),
    },
)

_SHELF_RECIPES = (
    ("ammonium", "Ammonium"),
    ("chlorophyll", "Chlorophyll"),
    ("nitrate", "Nitrate"),
    ("oxygen", "Oxygen"),
    ("phosphate", "Phosphate"),
    ("salinity", "Salinity"),
    ("silicate", "Silicate"),
    ("temperature", "Temperature"),
)

RECIPE_CATALOGUE = RECIPE_CATALOGUE + tuple(
    {
        "variable": variable,
        "recipe": "nsbc",
        "region": "Northwest European Shelf",
        "example_variable": variable,
        "notes": (
            f"{title} - North Sea Biogeochemical Climatology",
            "recipe: 'nsbc'",
        ),
        "arguments": (
            "climatology=True,",
            "vertical=False,  # set True to validate the full water column",
        ),
    }
    for variable, title in _SHELF_RECIPES
)

# the observational variables the catalogue can match a model variable to
RECIPE_VARIABLES = tuple(dict.fromkeys(entry["variable"] for entry in RECIPE_CATALOGUE))

# the decadal periods WOA23 publishes temperature and salinity for, as
# find_recipe() understands them
_WOA23_PERIODS = (
    (1955, 1964),
    (1965, 1974),
    (1975, 1984),
    (1985, 1994),
    (1995, 2004),
    (2005, 2014),
    (2015, 2022),
)


def _long_names(contents):
    return [str(name) for name in contents.long_name]


def _matching_variables(contents, long_names):
    """The model variables whose long_name is one of long_names."""
    matched = contents.loc[[name in long_names for name in _long_names(contents)]]
    return list(dict.fromkeys(matched.variable))


def _candidate_long_names(variable, contents):
    """The long_names in a file that describe one observational variable.

    This is ecoval's generate_mapping, narrowed to the variables OceanVal
    has recipes for. Each rule leans on how the long_name is worded, and
    rules out the benthic and riverine variables that are named after the
    same quantity.
    """
    names = _long_names(contents)

    def plain(term, *excluded):
        return [
            name
            for name in names
            if term in name.lower()
            and not any(word in name.lower() for word in ("benthic", "river"))
            and not any(word in name.lower() for word in excluded)
        ]

    if variable == "temperature":
        # air temperature is stored alongside sea temperature in coupled runs
        return plain("temperature", "air")

    if variable == "oxygen":
        return plain("oxygen", "saturation", "util", "flux")

    if variable == "silicate":
        # some models name it after the silicic acid rather than the salt
        matches = plain("silicate")
        return matches + [name for name in plain("silicic") if name not in matches]

    if variable == "ph":
        # ecoval's own rule reads ("pH" in x) or (" ph " in x) and ..., which
        # binds so that a benthic pH slips through; the exclusions belong to
        # both spellings
        return [
            name
            for name in names
            if ("pH" in name or " ph " in name.lower())
            and not any(word in name.lower() for word in ("benthic", "river"))
        ]

    if variable == "kd490":
        return [
            name
            for name in names
            if "atten" in name.lower() and "coeff" in name.lower()
        ]

    if variable == "chlorophyll":
        matches = plain("chlorophyll")
        if len(matches) > 1:
            # a model reporting a total as well as its phytoplankton types
            # would otherwise double count
            matches = [name for name in matches if "total" not in name.lower()]
        return matches

    return plain(variable)


def _nitrate_fallback(contents, mapping):
    """Use a single nitrogen nutrient variable when nitrate is not named."""
    if mapping.get("nitrate") is not None or mapping.get("ammonium") is not None:
        return None
    nitrogen = contents.loc[
        [
            "nitrogen" in name.lower() and "nutrient" in name.lower()
            for name in _long_names(contents)
        ]
    ]
    if len(nitrogen) != 1:
        return None
    warnings.warn("No nitrate variable found, using the nitrogen nutrient variable")
    return list(nitrogen.variable)[0]


def generate_recipe_mapping(path):
    """Map each recipe variable to the model variable holding it in one file.

    Returns a dict keyed by the observational variable name. Variables the
    file does not hold, and ones it describes ambiguously, map to None.
    """
    contents = nc.open_data(path, checks=False).contents
    contents = contents.assign(long_name=[str(x) for x in contents.long_name])

    surface_contents = contents.query("nlevels == 1").reset_index(drop=True)
    depth_contents = contents.query("nlevels > 1").reset_index(drop=True)
    # the water column is searched first: a model reporting both a 3D field
    # and a surface diagnostic of the same quantity means the 3D one, and
    # searching the two together would only make the pair look ambiguous
    searches = [depth_contents, surface_contents]

    mapping = {}
    for variable in RECIPE_VARIABLES:
        mapping[variable] = None
        for search in searches:
            if len(search) == 0:
                continue
            model_variables = _matching_variables(
                search, _candidate_long_names(variable, search)
            )
            if len(model_variables) > 1 and variable != "chlorophyll":
                # no way to tell which of them the recipe wants
                break
            if model_variables:
                mapping[variable] = "+".join(model_variables)
                break

    nitrogen_source = depth_contents if len(depth_contents) > 0 else surface_contents
    fallback = _nitrate_fallback(nitrogen_source, mapping)
    if fallback is not None:
        mapping["nitrate"] = fallback

    # these carry no long_name worth matching on, so they go by name
    variables = list(contents.variable)
    for variable, model_variable in (
        ("temperature", "votemper"),
        ("salinity", "vosaline"),
        ("ph", "ph"),
    ):
        if mapping.get(variable) is None and model_variable in variables:
            mapping[variable] = model_variable

    return mapping


def _file_pattern(path):
    """A file name with its dates blanked out, so one stream groups together."""
    name = os.path.basename(path)
    name = re.sub(r"\d{4,}", "**", name)
    return re.sub(r"\d{2,}", "**", name)


def simulation_paths(simdir, ndown):
    """Every output file ndown directories below simdir."""
    pattern = os.path.join(simdir, *(["*"] * ndown), "*.nc")
    return [
        path
        for path in sorted(glob.glob(pattern))
        if "restart" not in os.path.basename(path)
    ]


def simulation_files(simdir, ndown):
    """One example file per output stream, ndown directories below simdir.

    A simulation holds one file per stream per time step, and every step
    writes the same variables, so only one file per stream has to be read.
    """
    examples = {}
    for path in simulation_paths(simdir, ndown):
        examples.setdefault(_file_pattern(path), path)
    return list(examples.values())


def extract_recipe_variable_mapping(simdir, ndown):
    """Work out which model variable holds each recipe variable.

    Scans one file per output stream and keeps the model variable that the
    most streams agree on, so a diagnostic file holding a stray copy of a
    variable cannot outvote the stream that is actually reporting it.
    """
    paths = simulation_files(simdir, ndown)
    if not paths:
        raise ValueError(
            f"No netCDF files were found {ndown} directories below {simdir}. "
            "Check the ndown argument and the simulation directory structure."
        )

    votes = {variable: {} for variable in RECIPE_VARIABLES}
    for path in paths:
        try:
            mapping = generate_recipe_mapping(path)
        except Exception:
            # a stream OceanVal cannot read is not a reason to give up on
            # the rest of the simulation
            continue
        for variable, model_variable in mapping.items():
            if model_variable is None:
                continue
            counts = votes[variable]
            counts[model_variable] = counts.get(model_variable, 0) + 1

    mapping = {}
    for variable, counts in votes.items():
        if not counts:
            continue
        # most streams first, then alphabetically, so the result is the same
        # every time the generator is run over the same simulation
        mapping[variable] = sorted(counts, key=lambda name: (-counts[name], name))[0]
    return mapping


def _years_in(text):
    """The years named in one path, whether on their own or inside a date."""
    for match in re.findall(r"(?<!\d)(\d{4})(?!\d)", text):
        yield int(match)
    # NEMO and friends name files by yyyymmdd rather than filing them by year
    for match in re.findall(r"(?<!\d)(\d{4})(\d{2})(\d{2})(?!\d)", text):
        year, month, day = (int(part) for part in match)
        if 1 <= month <= 12 and 1 <= day <= 31:
            yield year


def simulation_years(simdir, paths):
    """The first and last year named in a simulation's paths, if any.

    Model output is almost always filed under a year, or names one, and the
    matchup needs a start and an end year to run at all. Only the part of
    each path below simdir is read, so a year in the directory the user
    happens to keep their simulations in cannot be mistaken for one.
    """
    years = {
        year
        for path in paths
        for year in _years_in(os.path.relpath(path, simdir))
        if 1900 <= year <= 2100
    }
    if not years:
        return None
    return min(years), max(years)


def _woa23_period(years):
    """The WOA23 decadal period covering a simulation, if one does."""
    if years is None:
        return None
    start, end = years
    for period_start, period_end in _WOA23_PERIODS:
        if start >= period_start and end <= period_end:
            return period_start, period_end
    return None


def _comment(lines):
    return [f"# {line}".rstrip() for line in lines]


def _recipe_block(entry, model_variable, period, years=None, live_region=None):
    """The source lines for one recipe.

    A recipe is commented out when no model variable was found for it, and
    when another recipe has already registered the same variable - which,
    depending on the requested domain, can print either before or after
    this block, so the message names the region rather than a position.
    """
    superseded = live_region is not None
    lines = list(_comment(entry["notes"]))

    arguments = list(entry["arguments"])
    if entry.get("decadal"):
        if period is None:
            if years is None:
                note = [
                    "WOA23 publishes this per decade, and start and end must sit",
                    "inside one period - set them to your simulation's years.",
                ]
            else:
                note = [
                    f"No decadal WOA23 period covers {years[0]}-{years[1]} - set start",
                    "and end below to a range inside one of the periods WOA23",
                    "publishes.",
                ]
            lines.extend(_comment(note))
            decadal = "start=2005, end=2014,"
        else:
            decadal = f"start={period[0]}, end={period[1]},"
        arguments.insert(0, decadal)

    call = [
        "oceanval.add_gridded_comparison(",
        f'    name="{entry["variable"]}",',
        f'    model_variable="{model_variable or entry["example_variable"]}",',
        f'    recipe={{"{entry["variable"]}": "{entry["recipe"]}"}},',
        *[f"    {argument}" for argument in arguments],
        ")",
    ]

    if model_variable is None:
        lines.extend(
            _comment(
                [
                    f"No {entry['variable']} variable was found in the model output.",
                    "Set model_variable to the name your model uses, then uncomment",
                    "this block.",
                ]
            )
        )
        lines.extend(_comment(call))
    elif superseded:
        lines.extend(
            _comment(
                [
                    f"The {live_region} recipe for {entry['variable']} is registered instead.",
                    "Registering a second one would replace it, so to validate against",
                    "this source, comment out the other recipe and uncomment this one.",
                ]
            )
        )
        lines.extend(_comment(call))
    else:
        lines.extend(call)
    return lines


def _header(simdir, ndown, mapping, years, domain):
    found = ", ".join(sorted(mapping)) if mapping else "none"
    lines = [
        '"""OceanVal matchup script, generated by oceanval.create_recipes.',
        "",
        f"Simulation directory: {simdir}",
        f"Output files found {ndown} director{'y' if ndown == 1 else 'ies'} down.",
        f"Model variables identified: {found}.",
        f"Domain: {domain}.",
        "",
        "Every recipe OceanVal ships with is below. The ones a model variable",
        "was found for are live; the rest are commented out, with the model",
        "variable left as a placeholder for you to fill in.",
        "",
        "Registering one observational variable twice replaces the first",
        "registration, so where a variable has a recipe in more than one",
        f"region only the {domain} one is left live and the others are",
        "commented out as alternatives.",
        "",
        "See https://pmlmodelling.github.io/OceanVal/recipes.html",
        '"""',
        "",
        "import oceanval",
        "",
    ]
    if years is None:
        lines.extend(
            [
                "",
                "# The years this simulation covers could not be read from the file",
                "# names - set start and end on the matchup call at the bottom.",
            ]
        )
    return lines


def _section(title):
    rule = "=" * 74
    return ["", f"# {rule}", f"# {title}", f"# {rule}", ""]


def _footer(simdir, ndown, years):
    start, end = years if years is not None else (1995, 2004)
    suffix = "" if years is not None else "  # set to your simulation's years"
    return [
        "# Pair the registered observations with your model output, then build the",
        "# report. start and end must match the years your simulation covers - and",
        "# for the World Ocean Atlas temperature and salinity recipes they must sit",
        "# inside a single decadal period.",
        "#",
        "# If you set vertical=True on any recipe above, matchup also needs",
        '# thickness - either "z_level" or the name of a cell thickness variable.',
        "oceanval.matchup(",
        f'    sim_dir="{simdir}",',
        f"    start={start},{suffix}",
        f"    end={end},{suffix}",
        f"    n_dirs_down={ndown},",
        ")",
        "",
        "# word=True and pdf=True also write Word and PDF versions of the report.",
        "oceanval.validate()",
        "",
    ]


def _preferred_entries(mapping, domain):
    """The one catalogue entry to leave live for each matched variable.

    A variable with a matched model variable in more than one region (e.g.
    temperature, which both the Global and NWES recipes cover) has one
    entry preferred: the one for the requested domain if it has a match,
    the first matched entry otherwise - so asking for "nwes" falls back to
    the Global recipe for a variable NWES has none for.
    """
    wanted_region = DOMAIN_REGIONS[domain]
    preferred = {}
    for entry in RECIPE_CATALOGUE:
        variable = entry["variable"]
        if mapping.get(variable) is None:
            continue
        current = preferred.get(variable)
        if current is None or (
            entry["region"] == wanted_region and current["region"] != wanted_region
        ):
            preferred[variable] = entry
    return preferred


def build_recipe_script(simdir, ndown, mapping, years=None, domain="global"):
    """The text of the matchup script for one simulation's variable mapping."""
    lines = _header(simdir, ndown, mapping, years, domain)
    period = _woa23_period(years)
    preferred = _preferred_entries(mapping, domain)

    region = None
    for entry in RECIPE_CATALOGUE:
        if entry["region"] != region:
            region = entry["region"]
            lines.extend(_section(region))
        variable = entry["variable"]
        model_variable = mapping.get(variable)
        live_entry = preferred.get(variable)
        live_region = (
            live_entry["region"]
            if model_variable is not None and live_entry is not entry
            else None
        )
        lines.extend(
            _recipe_block(entry, model_variable, period, years, live_region)
        )
        lines.append("")

    lines.extend(_section("Matchup and report"))
    lines.extend(_footer(simdir, ndown, years))
    return "\n".join(lines).rstrip("\n") + "\n"


def create_recipes(simdir=None, ndown=None, out=None, domain=None, start=None, end=None):
    """Write a matchup script for a simulation, with its variables filled in.

    Scans the netCDF files in simdir, identifies which model variable holds
    each observational variable OceanVal has a recipe for, and writes out a
    script registering those recipes. Recipes with no matching model
    variable are written out commented, so you can see what was missed and
    fill the variable in by hand.

    Parameters
    -------------
    simdir : str
        The directory holding the model output. Required.
    ndown : int
        How many directories below simdir the output files sit. Required.
    out : str
        Path of the Python file to write. Required.
    domain : str
        Either "global" or "nwes". Where a variable has a recipe in both
        regions (e.g. temperature), the recipe for this domain is left
        live and the other is commented out as an alternative; a variable
        with a recipe only outside this domain still gets that one.
        Required.
    start : int
        First year of the simulation to validate. Passed straight through
        to the generated script's matchup() call, and used to pick the
        WOA23 decadal period for temperature and salinity. Required.
    end : int
        Last year of the simulation to validate, passed through the same
        way as start. Required.

    Returns
    -------------
    out : str
        The path written to.
    """
    if simdir is None:
        raise ValueError("Please provide simdir, the model output directory")
    if ndown is None:
        raise ValueError(
            "Please provide ndown, the number of directories below simdir "
            "that the output files sit in"
        )
    if out is None:
        raise ValueError("Please provide out, the Python file to write")
    if domain is None:
        raise ValueError(
            'Please provide domain, either "global" or "nwes"'
        )
    if start is None:
        raise ValueError("Please provide start, the first year to validate")
    if end is None:
        raise ValueError("Please provide end, the last year to validate")

    if not isinstance(simdir, str):
        raise TypeError("simdir must be a string")
    if not isinstance(out, str):
        raise TypeError("out must be a string")
    if isinstance(ndown, bool) or not isinstance(ndown, int):
        raise TypeError("ndown must be an integer")
    if ndown < 0:
        raise ValueError("ndown must be a positive integer")
    if not isinstance(domain, str):
        raise TypeError("domain must be a string")
    if domain.lower() not in DOMAIN_REGIONS:
        raise ValueError('domain must be either "global" or "nwes"')
    domain = domain.lower()
    if isinstance(start, bool) or not isinstance(start, int):
        raise TypeError("start must be an integer")
    if isinstance(end, bool) or not isinstance(end, int):
        raise TypeError("end must be an integer")
    if end < start:
        raise ValueError("end must not be before start")
    if not os.path.isdir(simdir):
        raise ValueError(f"{simdir} is not a directory")

    mapping = extract_recipe_variable_mapping(simdir, ndown)
    years = (start, end)

    missing = [
        variable for variable in RECIPE_VARIABLES if mapping.get(variable) is None
    ]
    if not mapping:
        warnings.warn(
            "No model variables could be identified, so every recipe in "
            f"{out} is commented out."
        )

    script = build_recipe_script(
        os.path.abspath(simdir), ndown, mapping, years, domain
    )
    directory = os.path.dirname(os.path.abspath(out))
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(out, "w") as generated:
        generated.write(script)

    print(f"Wrote {out}")
    for variable in sorted(mapping):
        print(f"  {variable}: {mapping[variable]}")
    if missing:
        print(f"  commented out (no model variable found): {', '.join(missing)}")
    return out
