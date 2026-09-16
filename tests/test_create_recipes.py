import ast
import os

import numpy as np
import pytest
import xarray as xr

import oceanval
from oceanval.create_recipes import (
    RECIPE_CATALOGUE,
    RECIPE_VARIABLES,
    build_recipe_script,
    extract_recipe_variable_mapping,
    generate_recipe_mapping,
    simulation_files,
    simulation_years,
)


def write_netcdf(path, variables, nz=5):
    """A model output file, with one long_name per variable.

    A long_name prefixed "SURF:" is written as a surface field, which is how
    a model reports fluxes and other two dimensional diagnostics.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    dataset = xr.Dataset()
    for name, long_name in variables.items():
        surface = long_name.startswith("SURF:")
        attributes = {"long_name": long_name.replace("SURF:", ""), "units": "1"}
        if surface:
            values = np.random.rand(1, 4, 4).astype("f4")
            dims = ("time", "y", "x")
        else:
            values = np.random.rand(1, nz, 4, 4).astype("f4")
            dims = ("time", "deptht", "y", "x")
        dataset[name] = xr.DataArray(values, dims=dims, attrs=attributes)
    dataset["time"] = ("time", np.array([0.0]))
    dataset.time.attrs = {"units": "days since 2011-01-01", "calendar": "standard"}
    dataset.to_netcdf(path)


GRID_VARIABLES = {
    "thetao": "sea water potential temperature",
    "tair": "SURF:air temperature at 2m",
    "so": "sea water salinity",
}

TRACER_VARIABLES = {
    "P1_Chl": "diatoms chlorophyll",
    "P2_Chl": "nanophytoplankton chlorophyll",
    "Chl_tot": "total chlorophyll",
    "O2_o": "oxygen",
    "O2_sat": "oxygen saturation",
    "O2_flux": "SURF:air-sea oxygen flux",
    "Y2_o": "benthic oxygen",
    "N3_n": "nitrate nitrogen",
    "N4_n": "ammonium nitrogen",
    "N1_p": "phosphate phosphorus",
    "N5_s": "silicate silicate",
    "O3_pH": "pH",
    "ben_pH": "benthic pH",
    "O3_TA": "total alkalinity",
    "xEPS": "attenuation coefficient",
    "R1_n": "river nitrate nitrogen",
}


@pytest.fixture
def simulation(tmp_path):
    """A two year simulation, filed as sim/<year>/<month>/<files>."""
    root = tmp_path / "sim"
    for year, month in (("2011", "01"), ("2012", "06")):
        stem = f"nemo_1m_{year}{month}01_{year}{month}28"
        write_netcdf(str(root / year / month / f"{stem}_grid_T.nc"), GRID_VARIABLES)
        write_netcdf(str(root / year / month / f"{stem}_ptrc_T.nc"), TRACER_VARIABLES)
    return str(root)


class TestArguments:
    @pytest.mark.parametrize(
        "kwargs, message",
        [
            ({}, "Please provide simdir"),
            ({"simdir": "."}, "Please provide ndown"),
            ({"simdir": ".", "ndown": 1}, "Please provide out"),
            (
                {"simdir": ".", "ndown": 1, "out": "x"},
                "Please provide domain",
            ),
        ],
    )
    def test_every_argument_is_required(self, kwargs, message):
        with pytest.raises(ValueError, match=message):
            oceanval.create_recipes(**kwargs)

    def test_ndown_must_be_an_integer(self, tmp_path):
        with pytest.raises(TypeError, match="ndown must be an integer"):
            oceanval.create_recipes(
                simdir=str(tmp_path),
                ndown="2",
                out=str(tmp_path / "out.py"),
                domain="global",
            )

    def test_ndown_must_not_be_negative(self, tmp_path):
        with pytest.raises(ValueError, match="ndown must be a positive integer"):
            oceanval.create_recipes(
                simdir=str(tmp_path),
                ndown=-1,
                out=str(tmp_path / "out.py"),
                domain="global",
            )

    def test_simdir_must_exist(self, tmp_path):
        missing = str(tmp_path / "nope")
        with pytest.raises(ValueError, match="is not a directory"):
            oceanval.create_recipes(
                simdir=missing,
                ndown=1,
                out=str(tmp_path / "out.py"),
                domain="global",
            )

    def test_a_simulation_with_no_files_says_which_argument_to_check(self, tmp_path):
        with pytest.raises(ValueError, match="Check the ndown argument"):
            oceanval.create_recipes(
                simdir=str(tmp_path),
                ndown=2,
                out=str(tmp_path / "out.py"),
                domain="global",
            )

    def test_domain_must_be_a_string(self, tmp_path):
        with pytest.raises(TypeError, match="domain must be a string"):
            oceanval.create_recipes(
                simdir=str(tmp_path),
                ndown=1,
                out=str(tmp_path / "out.py"),
                domain=1,
            )

    @pytest.mark.parametrize("domain", ["europe", "local", "", "GLOBALLY"])
    def test_domain_must_be_global_or_nwes(self, tmp_path, domain):
        with pytest.raises(
            ValueError, match='domain must be either "global" or "nwes"'
        ):
            oceanval.create_recipes(
                simdir=str(tmp_path),
                ndown=1,
                out=str(tmp_path / "out.py"),
                domain=domain,
            )

    def test_domain_is_case_insensitive(self, tmp_path):
        write_netcdf(
            str(tmp_path / "sim" / "output.nc"),
            {"thetao": "sea water potential temperature"},
        )
        out = str(tmp_path / "out.py")

        oceanval.create_recipes(
            simdir=str(tmp_path / "sim"), ndown=0, out=out, domain="NWES"
        )

        assert 'recipe={"temperature": "nsbc"}' in open(out).read()


class TestVariableIdentification:
    def test_model_variables_are_found_from_their_long_names(self, simulation):
        mapping = extract_recipe_variable_mapping(simulation, 2)

        assert mapping["temperature"] == "thetao"
        assert mapping["salinity"] == "so"
        assert mapping["nitrate"] == "N3_n"
        assert mapping["ammonium"] == "N4_n"
        assert mapping["phosphate"] == "N1_p"
        assert mapping["silicate"] == "N5_s"
        assert mapping["alkalinity"] == "O3_TA"
        assert mapping["kd490"] == "xEPS"

    def test_decoy_variables_are_rejected(self, simulation):
        mapping = extract_recipe_variable_mapping(simulation, 2)

        # air temperature, a benthic pH, and oxygen saturation and flux are
        # all named after the quantity the recipe wants but are not it
        assert mapping["temperature"] == "thetao"
        assert mapping["ph"] == "O3_pH"
        assert mapping["oxygen"] == "O2_o"
        # a river nitrate must not outvote the water column one
        assert mapping["nitrate"] == "N3_n"

    def test_chlorophyll_sums_the_phytoplankton_types(self, simulation):
        mapping = extract_recipe_variable_mapping(simulation, 2)

        # the model reports a total as well as its types, and counting both
        # would double the chlorophyll
        assert mapping["chlorophyll"] == "P1_Chl+P2_Chl"

    def test_an_ambiguous_variable_is_left_unmatched(self, tmp_path):
        path = str(tmp_path / "sim" / "ambiguous.nc")
        write_netcdf(
            path,
            {
                "sal_a": "sea water salinity",
                "sal_b": "sea water salinity anomaly reference",
            },
        )
        mapping = generate_recipe_mapping(path)

        # there is no way to tell which one the recipe wants
        assert mapping["salinity"] is None

    def test_nemo_names_are_matched_without_a_long_name(self, tmp_path):
        path = str(tmp_path / "sim" / "nemo.nc")
        write_netcdf(path, {"votemper": "unknown", "vosaline": "unknown"})

        mapping = generate_recipe_mapping(path)

        assert mapping["temperature"] == "votemper"
        assert mapping["salinity"] == "vosaline"

    def test_a_bare_ph_variable_is_matched_by_name(self, tmp_path):
        path = str(tmp_path / "sim" / "bare.nc")
        # pH is often written with no long_name worth matching on, and the
        # one it has need not be unique
        write_netcdf(path, {"ph": "unknown", "junk": "unknown"})

        assert generate_recipe_mapping(path)["ph"] == "ph"

    def test_a_surface_only_variable_is_found_beside_3d_ones(self, tmp_path):
        path = str(tmp_path / "sim" / "mixed.nc")
        write_netcdf(
            path,
            {
                "thetao": "sea water potential temperature",
                # a model can report the light attenuation as a 2D diagnostic
                # in the same file as its 3D tracers
                "xEPS": "SURF:attenuation coefficient",
            },
        )
        mapping = generate_recipe_mapping(path)

        assert mapping["temperature"] == "thetao"
        assert mapping["kd490"] == "xEPS"

    def test_a_3d_field_wins_over_a_surface_diagnostic(self, tmp_path):
        path = str(tmp_path / "sim" / "both.nc")
        write_netcdf(
            path,
            {
                "thetao": "sea water potential temperature",
                "tos": "SURF:sea surface temperature",
            },
        )
        mapping = generate_recipe_mapping(path)

        # searching the two together would make the pair look ambiguous and
        # lose temperature altogether
        assert mapping["temperature"] == "thetao"

    def test_only_one_file_per_output_stream_is_read(self, simulation):
        files = simulation_files(simulation, 2)

        # two streams, written twice each - reading one of each is enough
        assert len(files) == 2
        assert sorted(os.path.basename(f).split("_")[-2] for f in files) == [
            "grid",
            "ptrc",
        ]

    def test_restart_files_are_ignored(self, simulation, tmp_path):
        write_netcdf(
            str(tmp_path / "sim" / "2011" / "01" / "nemo_restart.nc"),
            {"junk": "sea water salinity"},
        )

        names = [os.path.basename(f) for f in simulation_files(simulation, 2)]
        assert not [name for name in names if "restart" in name]


class TestGeneratedScript:
    def test_the_script_is_valid_python(self, simulation, tmp_path):
        out = str(tmp_path / "matchup.py")
        oceanval.create_recipes(simdir=simulation, ndown=2, out=out, domain="global")

        ast.parse(open(out).read())

    def test_matched_recipes_carry_the_model_variable(self, simulation, tmp_path):
        out = str(tmp_path / "matchup.py")
        oceanval.create_recipes(simdir=simulation, ndown=2, out=out, domain="global")
        script = open(out).read()

        assert 'model_variable="thetao"' in script
        assert 'recipe={"temperature": "cobe2"},' in script
        # and the block is live, not commented out
        assert "\noceanval.add_gridded_comparison(\n    name=\"temperature\"," in script

    def test_unmatched_recipes_are_commented_out(self, tmp_path):
        # a simulation holding nothing a recipe covers
        write_netcdf(str(tmp_path / "sim" / "empty.nc"), {"uo": "eastward velocity"})
        out = str(tmp_path / "matchup.py")
        with pytest.warns(UserWarning, match="No model variables could be identified"):
            oceanval.create_recipes(
                simdir=str(tmp_path / "sim"), ndown=0, out=out, domain="global"
            )
        script = open(out).read()

        # every recipe is still there, so nothing is silently dropped
        assert script.count("add_gridded_comparison(") == len(RECIPE_CATALOGUE)
        assert "\noceanval.add_gridded_comparison(" not in script
        assert "# No alkalinity variable was found in the model output." in script
        # the placeholder from the published example is left to be filled in
        assert '#     model_variable="talk",' in script

    def test_one_recipe_stays_live_per_observational_variable(
        self, simulation, tmp_path
    ):
        out = str(tmp_path / "matchup.py")
        oceanval.create_recipes(simdir=simulation, ndown=2, out=out, domain="global")
        script = open(out).read()

        # registering a variable twice replaces the first registration, so
        # only one block per variable can be live
        live = [
            line
            for line in script.splitlines()
            if line.startswith("    name=") and not line.startswith("#")
        ]
        assert len(live) == len(set(live))
        assert "# The Global recipe for temperature is registered instead." in script

    def test_domain_prefers_the_matching_regions_recipe(self, simulation, tmp_path):
        out = str(tmp_path / "matchup.py")
        oceanval.create_recipes(simdir=simulation, ndown=2, out=out, domain="nwes")
        script = open(out).read()

        # temperature has a recipe in both regions; nwes must win, and the
        # global ones (cobe2 and woa23) become the commented alternatives
        assert 'recipe={"temperature": "nsbc"},' in script
        assert '\noceanval.add_gridded_comparison(\n    name="temperature",' in script
        assert (
            "The Northwest European Shelf recipe for temperature is registered "
            "instead." in script
        )
        # only one live block for the variable, same as with domain="global"
        live = [
            line
            for line in script.splitlines()
            if line.startswith("    name=") and not line.startswith("#")
        ]
        assert len(live) == len(set(live))

    def test_domain_falls_back_when_the_region_has_no_recipe(
        self, simulation, tmp_path
    ):
        out = str(tmp_path / "matchup.py")
        # nitrate is identified (N3_n) but NWES has no nitrate recipe of its
        # own to prefer, so the global woa23 one stays live either way
        oceanval.create_recipes(simdir=simulation, ndown=2, out=out, domain="nwes")
        script = open(out).read()

        assert 'name="nitrate",' in script
        assert 'recipe={"nitrate": "woa23"},' in script
        assert '\noceanval.add_gridded_comparison(\n    name="nitrate",' in script

    def test_the_matchup_call_uses_the_simulation_and_its_years(
        self, simulation, tmp_path
    ):
        out = str(tmp_path / "matchup.py")
        oceanval.create_recipes(simdir=simulation, ndown=2, out=out, domain="global")
        script = open(out).read()

        assert f'sim_dir="{os.path.abspath(simulation)}",' in script
        assert "n_dirs_down=2," in script
        assert "start=2011," in script
        assert "end=2012," in script
        assert "oceanval.validate()" in script

    def test_woa23_recipes_get_the_decadal_period_covering_the_simulation(
        self, simulation, tmp_path
    ):
        out = str(tmp_path / "matchup.py")
        oceanval.create_recipes(simdir=simulation, ndown=2, out=out, domain="global")
        script = open(out).read()

        # WOA23 temperature and salinity are published per decade, and
        # find_recipe rejects a start/end that straddles two of them
        assert "start=2005, end=2014," in script

    def test_a_simulation_outside_the_woa23_periods_is_flagged(self):
        script = build_recipe_script("/sim", 2, {"salinity": "so"}, years=(1901, 1903))

        assert "# No decadal WOA23 period covers 1901-1903" in script

    def test_woa23_recipes_say_what_to_do_when_the_years_are_unknown(self):
        script = build_recipe_script("/sim", 0, {"salinity": "so"}, years=None)

        # the years are not known, so the note cannot claim no period covers them
        assert "# WOA23 publishes this per decade" in script
        assert "No decadal WOA23 period covers" not in script

    def test_unreadable_years_leave_the_matchup_years_to_be_filled_in(self):
        script = build_recipe_script("/sim", 0, {"salinity": "so"}, years=None)

        assert "set start and end on the matchup call" in script
        assert "start=1995,  # set to your simulation's years" in script

    def test_years_come_from_below_the_simulation_directory(self, tmp_path):
        # a 1999 in the path the user keeps their simulations in is not a
        # year of the simulation
        root = tmp_path / "archive1999" / "sim"
        write_netcdf(str(root / "2011" / "output.nc"), GRID_VARIABLES)

        paths = [str(root / "2011" / "output.nc")]
        assert simulation_years(str(root), paths) == (2011, 2011)

    def test_years_are_read_from_dated_file_names(self, tmp_path):
        paths = ["/sim/nemo_1m_20030101_20031231_grid_T.nc"]

        assert simulation_years("/sim", paths) == (2003, 2003)


def test_the_catalogue_matches_the_published_example():
    """The generated script offers the same recipes as the website's."""
    example = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "docs-site",
        "recipe-examples.py",
    )
    if not os.path.exists(example):
        pytest.skip("the docs-site example is not present")

    published = []
    for node in ast.walk(ast.parse(open(example).read())):
        if not isinstance(node, ast.Call):
            continue
        keywords = {kw.arg: kw.value for kw in node.keywords}
        if "recipe" not in keywords:
            continue
        recipe = keywords["recipe"]
        published.append((recipe.keys[0].value, recipe.values[0].value))

    catalogue = [(entry["variable"], entry["recipe"]) for entry in RECIPE_CATALOGUE]
    assert catalogue == published


def test_every_catalogue_variable_can_be_identified():
    """Nothing in the catalogue is a recipe the generator can never match."""
    assert set(RECIPE_VARIABLES) == {entry["variable"] for entry in RECIPE_CATALOGUE}
