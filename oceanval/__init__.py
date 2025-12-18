import pandas as pd
import shutil
import glob
import subprocess
import warnings
import nctoolkit as nc

nc.session_info["stamp"] = nc.session_info["stamp"] + "_ecoval_output_"
import copy
from oceanval.matchall import matchup
from oceanval.summarize import summarize
import dill

# from oceanval.fixers import tidy_name
from oceanval.session import session_info
import webbrowser
from oceanval.chunkers import add_chunks
import os
import re
from oceanval.fvcom import fvcom_preprocess
import importlib

from oceanval.parsers import Validator, definitions, Summary, summaries


def reset():
    # add docstring
    """
    Reset the matchup definitions to their default state.
    This function resets the matchup definitions used in oceanval to their default state.
    """
    # reset session_info["short_title"] to empty dict
    session_info["short_title"] = dict()
    definitions.reset()
    summaries.reset()


notebook_dict = dict()


add_point_comparison = definitions.add_point_comparison
add_gridded_comparison = definitions.add_gridded_comparison
add_summary = summaries.add_summary


def fix_toc(concise=True, data_dir=None, out_dir=None, info = False):
    short_titles = dill.load(
        open(f"{data_dir}/oceanval_matchups/short_titles.pkl", "rb")
    )
    paths = glob.glob(f"{out_dir}/oceanval_report/notebooks/*.ipynb")
    variables = dill.load(
        open(f"{data_dir}/oceanval_matchups/variables_matched.pkl", "rb")
    )
    variables.sort()

    vv_dict = dict()
    for vv in variables:
        vv_paths = [os.path.basename(x) for x in paths if f"_{vv}.ip" in x]
        if len(vv_paths) > 0:
            vv_dict[vv] = vv_paths
    # get summary docs
    ss_paths = [os.path.basename(x) for x in paths if "summary" in x]

    out = f"{out_dir}/oceanval_report/_toc.yml"

    # write line by line to out
    i_chapter = 1
    with open(out, "w") as f:
        # "format: jb-book"
        x = f.write("format: jb-book\n")
        x = f.write("root: intro\n")
        x = f.write("parts:\n")

        x = f.write(f"- caption: Summaries\n")
        x = f.write("  chapters:\n")

        x = f.write(f"  - file: notebooks/001_methods.ipynb\n")

        # open notebook and replace book_chapter with i_chapter

        # open notebook and replace book_chapter with i_chapter
        with open(
            f"{out_dir}/oceanval_report/notebooks/001_methods.ipynb", "r"
        ) as file:
            filedata = file.read()

        # Replace the target string
        filedata = filedata.replace("book_chapter", str(i_chapter))
        if info:
            filedata = filedata.replace("info_text", "Simulation information and validation metrics summary")
        else:
            filedata = filedata.replace("info_text", "Validation metrics summary")

        with open(
            f"{out_dir}/oceanval_report/notebooks/001_methods.ipynb", "w"
        ) as file:
            file.write(filedata)
        i_chapter += 1
        for ff in ss_paths:
            x = f.write(f"  - file: notebooks/{ff}\n")
            # open notebook and replace book_chapter with i_chapter
            with open(f"{out_dir}/oceanval_report/notebooks/{ff}", "r") as file:
                filedata = file.read()

            filedata = filedata.replace("book_chapter", str(i_chapter))

            # Replace the target string
            # Write the file out again
            with open(f"{out_dir}/oceanval_report/notebooks/{ff}", "w") as file:
                file.write(filedata)
            i_chapter += 1

        # loop over variables in each vv_dict
        # value is the file in the chapter section
        # key is the variable name, so is the section
        for vv in vv_dict.keys():
            # capitalize if not ph
            vv_out = short_titles[vv]

            x = f.write(f"- caption: {vv_out}\n")
            x = f.write("  chapters:\n")
            for ff in vv_dict[vv]:
                x = f.write(f"  - file: notebooks/{ff}\n")

                # open notebook and replace book_chapter with i_chapter
                with open(f"{out_dir}/oceanval_report/notebooks/{ff}", "r") as file:
                    filedata = file.read()

                # Replace the target string
                filedata = filedata.replace("book_chapter", str(i_chapter))

                # Write the file out again

                with open(f"{out_dir}/oceanval_report/notebooks/{ff}", "w") as file:
                    file.write(filedata)
                i_chapter += 1


def fix_toc_comparison():
    book_dir = "oceanval_comparison"

    out = f"{book_dir}/compare/_toc.yml"
    # write line by line to out
    with open(out, "w") as f:
        # "format: jb-book"
        x = f.write("format: jb-book\n")
        x = f.write("root: intro\n")
        x = f.write("parts:\n")
        x = f.write(f"- caption: Comparisons with gridded surface observations\n")
        x = f.write("  chapters:\n")
        x = f.write(f"  - file: notebooks/comparison_bias.ipynb\n")
        x = f.write(f"  - file: notebooks/comparison_spatial.ipynb\n")
        x = f.write(f"  - file: notebooks/comparison_seasonal.ipynb\n")
        x = f.write(f"  - file: notebooks/comparison_regional.ipynb\n")
        x = f.write(f"- caption: Comparisons with point observations\n")
        x = f.write("  chapters:\n")
        x = f.write(f"  - file: notebooks/comparison_point_surface.ipynb\n")


def validate(
    lon_lim=None,
    lat_lim=None,
    concise=True,
    variables="all",
    fixed_scale=False,
    region=None,
    data_dir=".",
    out_dir=".",
    zip=False,
    view=True,
    test=False,
    sim_info = None 
):
    # docstring
    """
    Run the model evaluation for all of the available datasets, and generate a validation report.

    Parameters
    ----------
    lon_lim : list or None
        The longitude limits for the validation. Default is None
    lat_lim : list or None
        The latitude limits for the validation. Default is None
    variables : str or list
        The variables to run the model evaluation for. Default is "all"
    fixed_scale : bool
        Whether to use a fixed scale for the seasonal plots. Default is False. If True, the minimum and maximum values are capped to cover the 2nd and 98th percentiles of both model and observations.
    region : str or None
        The region being validated. Must be either "nwes" (northwest European Shelf) or "global". Default is None.
    view : bool
        Default is True. Open the validation report in a web browser after it is generated.
    test : bool
        Default is False. Ignore, unless you are testing oceanval.
    sim_info : dict or None
        A dictionary containing simulation information to be added to the report. Default is None.




    Returns
    -------
    None
    """

    # if lon_lim  is not None, make sure it's a list
    if lon_lim is not None:
        if isinstance(lon_lim, list) == False:
            raise ValueError("lon_lim must be a list")
        else:
            if len(lon_lim) != 2:
                raise ValueError("lon_lim must be a list of length 2")
    if lat_lim is not None:
        if isinstance(lat_lim, list) == False:
            raise ValueError("lat_lim must be a list")
        else:
            if len(lat_lim) != 2:
                raise ValueError("lat_lim must be a list of length 2")

    # concise must be boolean
    if isinstance(concise, bool) == False:
        raise ValueError("concise must be a boolean")
    # check variables is either "all" or a list of strings or a string
    if variables != "all":
        if isinstance(variables, str):
            pass
        elif isinstance(variables, list):
            for vv in variables:
                if isinstance(vv, str) == False:
                    raise ValueError("variables must be a list of strings")
        else:
            raise ValueError("variables must be either 'all' or a list of strings")
    # some coercise
    if variables != "all":
        if isinstance(variables, str):
            variables = [variables]
    if len(variables) == 0:
        raise ValueError("variables list is empty")

    # checked fixed_scale is bool
    if isinstance(fixed_scale, bool) == False:
        raise ValueError("fixed_scale must be a boolean")

    # convert data_dir to absolute path
    data_dir = os.path.expanduser(data_dir)
    data_dir = os.path.abspath(data_dir)
    #  regioncan only be nwes or global
    if region is not None:
        if region not in ["nwes", "global"]:
            raise ValueError("region must be either 'nwes' or 'global'")
    # ensure proper handling of ~
    out_dir = os.path.expanduser(out_dir)
    out_dir = os.path.abspath(out_dir)

    book_dir = os.path.join(out_dir, "oceanval_report")
    # if it doesn't exist, create it
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    

    # check zip is boolean
    if isinstance(zip, bool) == False:
        raise ValueError("zip must be a boolean")

    # test view is boolean

    if isinstance(view, bool) == False:
        raise ValueError("view must be a boolean")

    path_df = []

    fast_plot = False

    empty = True

    # book directory is book, book1, book2, book10 etc.

    # create a new name if one already exists
    i = 0

    if os.path.exists(book_dir):
        # get user input to decide if it should be removed
        while True:
            files = glob.glob(f"{book_dir}/**/**/**", recursive=True)
            # list all files in book, recursively
            for ff in files:
                if ff.startswith(f"{book_dir}/"):
                    try:
                        os.remove(ff)
                    except:
                        pass
            files = glob.glob(f"{book_dir}/**/**/**", recursive=True)
            # only list files
            files = [x for x in files if os.path.isfile(x)]
            if len(files) == 0:
                break



    # remove the results directory
    x_path = "oceanval_results"
    if os.path.exists(x_path):
        if x_path == "oceanval_results":
            shutil.rmtree(x_path)

    if empty:
        from shutil import copyfile
        # store the sim_info dict if provided in the book_dir

        if not os.path.exists(book_dir):
            os.mkdir(book_dir)
        if not os.path.exists(f"{book_dir}/notebooks"):
            os.mkdir(f"{book_dir}/notebooks")

        if sim_info is not None:
            dill.dump(
                sim_info,
                open(f"{book_dir}/sim_info.pkl", "wb"),
            )

        data_path = importlib.resources.files(__name__).joinpath(
            "data/001_methods.ipynb"
        )
        if not os.path.exists(f"{book_dir}/notebooks/001_methods.ipynb"):
            copyfile(data_path, f"{book_dir}/notebooks/001_methods.ipynb")
        # open this file and replace model_name with model

        data_path = importlib.resources.files(__name__).joinpath("data/_toc.yml")

        out = f"{book_dir}/" + os.path.basename(data_path)
        copyfile(data_path, out)

        data_path = importlib.resources.files(__name__).joinpath(
            "data/requirements.txt"
        )
        out = f"{book_dir}/" + os.path.basename(data_path)
        copyfile(data_path, out)

        data_path = importlib.resources.files(__name__).joinpath("data/intro.md")
        out = f"{book_dir}/" + os.path.basename(data_path)
        copyfile(data_path, out)

        # copy config

        data_path = importlib.resources.files(__name__).joinpath("data/_config.yml")
        out = f"{book_dir}/" + os.path.basename(data_path)

        with open(data_path, "r") as file:
            filedata = file.read()

        # Write the file out again
        with open(out, "w") as file:
            file.write(filedata)

        # copyfile(data_path, out)

        path_df = []

        # loop through the point matchups and generate notebooks

        point_paths = glob.glob(f"{data_dir}/oceanval_matchups/point/**/**/**/**.csv")
        point_paths = [x for x in point_paths if "unit" not in os.path.basename(x)]
        # loop through the paths
        for pp in point_paths:
            ff_def = pp.replace(".csv", "_definitions.pkl")
            definitions = dill.load(open(ff_def, "rb"))
            vv = os.path.basename(pp).split("_")[2].replace(".csv", "")
            if variables != "all":
                if True:
                    if vv not in variables:
                        continue
            source = os.path.basename(pp).split("_")[0]
            variable = vv
            layer = os.path.basename(pp).split("_")[1].replace(".csv", "")
            Variable = definitions[variable].short_name

            vv_file = pp
            vv_file_find = pp.replace("../../", "")

            if os.path.exists(vv_file_find):
                if (
                    len(
                        glob.glob(
                            f"{book_dir}/notebooks/*point_{layer}_{variable}.ipynb"
                        )
                    )
                    == 0
                ):
                    file1 = importlib.resources.files(__name__).joinpath(
                        "data/point_template.ipynb"
                    )
                    with open(file1, "r") as file:
                        filedata = file.read()

                    if layer in ["all", "surface"]:
                        filedata = filedata.replace(
                            "chunk_point_surface", "chunk_point"
                        )
                    else:
                        filedata = filedata.replace("chunk_point_surface", "")
                    if layer in ["bottom", "all"]:
                        if vv.lower() not in ["pco2"]:
                            filedata = filedata.replace(
                                "chunk_point_bottom", "chunk_point"
                            )
                        else:
                            filedata = filedata.replace("chunk_point_bottom", "")
                    else:
                        filedata = filedata.replace("chunk_point_bottom", "")

                    # Replace the target string
                    out = f"{book_dir}/notebooks/{source}_{layer}_{variable}.ipynb"
                    filedata = filedata.replace("point_variable", variable)
                    n_levels = definitions[variable].n_levels
                    if layer != "all":
                        if n_levels > 1:
                            filedata = filedata.replace(
                                "Validation of point_layer", f"Validation of {layer}"
                            )
                        else:
                            filedata = filedata.replace(
                                "Validation of point_layer", f"Validation of "
                            )
                    else:
                        filedata = filedata.replace(
                            "Validation of point_layer", f"Validation of "
                        )

                    filedata = filedata.replace("point_layer", layer)
                    filedata = filedata.replace("point_obs_source", source)
                    filedata = filedata.replace("template_title", Variable)
                    filedata = filedata.replace("data_dir_value", data_dir)
                    filedata = filedata.replace("out_dir_value", out_dir)

                    # Write the file out again
                    with open(out, "w") as file:
                        file.write(filedata)

                    path_df.append(
                        pd.DataFrame(
                            {
                                "variable": [variable],
                                "path": out,
                            }
                        )
                    )

        # Loop through the gridded matchups and generate notebooks
        # identify gridded variables in matched data
        gridded_paths = glob.glob(f"{data_dir}/oceanval_matchups/gridded/**/**.nc")

        if len(gridded_paths) > 0:
            for vv in [
                os.path.basename(x).split("_")[1].replace(".nc", "")
                for x in gridded_paths
            ]:
                for source in [
                    os.path.basename(x).split("_")[0]
                    for x in glob.glob(
                        f"{data_dir}/oceanval_matchups/gridded/**/**_{vv}_**.nc"
                    )
                ]:

                    variable = vv
                    if variables != "all":
                        if vv not in variables:
                            continue
                    if not os.path.exists(
                        f"{book_dir}/notebooks/{source}_{variable}.ipynb"
                    ):
                        ff_def = glob.glob(
                            f"{data_dir}/oceanval_matchups/gridded/{variable}/{source}_*definitions*.pkl"
                        )[0]
                        definitions = dill.load(open(ff_def, "rb"))
                        Variable = definitions[variable].short_name
                        ff_nc = glob.glob(
                            f"{data_dir}/oceanval_matchups/gridded/{variable}/{source}_*surface*.nc"
                        )[0]
                        ds = nc.open_data(ff_nc, checks=False)
                        try:
                            n_months = len(ds.months)
                        except:
                            n_months = 12
                        seasonal = n_months >= 12

                        file1 = importlib.resources.files(__name__).joinpath(
                            "data/gridded_template.ipynb"
                        )
                        if (
                            len(
                                glob.glob(
                                    f"{book_dir}/notebooks/*{source}_{variable}.ipynb"
                                )
                            )
                            == 0
                        ):
                            with open(file1, "r") as file:
                                filedata = file.read()

                            # Replace the target string
                            filedata = filedata.replace("template_variable", variable)
                            filedata = filedata.replace("template_title", Variable)
                            filedata = filedata.replace("data_dir_value", data_dir)
                            filedata = filedata.replace("source_name", source)
                            if region == "nwes":
                                filedata = filedata.replace("zonal_height", "6000")
                            else:
                                filedata = filedata.replace("zonal_height", "2000")
                            # make every letter a capital
                            source_capital = source.upper()
                            filedata = filedata.replace("source_title", source_capital)
                            if seasonal is False:
                                filedata = filedata.replace("chunk_seasonal", "")
                            # change sub_regions_value to region
                            if region is not None:
                                filedata = filedata.replace(
                                    "sub_regions_value", str(region)
                                )

                            # Write the file out again
                            with open(
                                f"{book_dir}/notebooks/{source}_{variable}.ipynb", "w"
                            ) as file:
                                file.write(filedata)

                            variable = vv
                            path_df.append(
                                pd.DataFrame(
                                    {
                                        "variable": [variable],
                                        "path": [
                                            f"{book_dir}/notebooks/{source}_{variable}.ipynb"
                                        ],
                                    }
                                )
                            )

        # need to start by figuring out whether anything has already been run...

        i = 0

        for ff in [
            x for x in glob.glob("{book_dir}/notebooks/*.ipynb") if "info" not in x
        ]:
            try:
                i_ff = int(os.path.basename(ff).split("_")[0])
                if i_ff > i:
                    i = i_ff
            except:
                pass

        i_orig = i

        if len(path_df) > 0:
            path_df = pd.concat(path_df)
            path_df = path_df.sort_values("variable").reset_index(drop=True)

        for i in range(len(path_df)):
            file1 = path_df.path.values[i]
            # pad i with zeros using zfill
            i_pad = str(i + 1).zfill(3)
            new_file = (
                os.path.dirname(file1) + "/" + i_pad + "_" + os.path.basename(file1)
            )
            os.rename(file1, new_file)
            # print(key, value)

        # copy the summary.ipynb notebook and add i_pad to the name

        i = i + 2
        i_pad = str(i).zfill(3)

        file1 = importlib.resources.files(__name__).joinpath("data/summary.ipynb")
        if len(glob.glob(f"{book_dir}/notebooks/*summary.ipynb")) == 0:
            copyfile(file1, f"{book_dir}/notebooks/{i_pad}_summary.ipynb")

        # change domain_title to "Full domain"

        with open(f"{book_dir}/notebooks/{i_pad}_summary.ipynb", "r") as file:
            filedata = file.read()

        # Replace the target string
        filedata = filedata.replace("domain_title", "Full domain")
        filedata = filedata.replace("data_dir_value", data_dir)
        filedata = filedata.replace("out_dir_value", out_dir)

        # Write the file out again
        with open(f"{book_dir}/notebooks/{i_pad}_summary.ipynb", "w") as file:
            file.write(filedata)

        # pair the notebooks using jupyter text

        os.system(
            f"jupytext --set-formats ipynb,py:percent {book_dir}/notebooks/*.ipynb"
        )

        # add the chunks
        add_chunks(out_dir)

        # loop through the notebooks and set r warnings options
        for ff in glob.glob(f"{book_dir}/notebooks/*.py"):
            with open(ff, "r") as file:
                filedata = file.read()

            # loop through line by line, and rewrite the original file
            lines = filedata.split("\n")
            new_lines = []
            for line in lines:
                if "%%R" in line:
                    new_lines.append(line)
                    new_lines.append("options(warn=-1)")
                else:
                    new_lines.append(line)
            # loop through all lines in lines and replace the_test_status with True
            for i in range(len(new_lines)):
                new_lines[i] = new_lines[i].replace("latexpagebreak", "")
                if "the_test_status" in new_lines[i]:
                    if test:
                        new_lines[i] = new_lines[i].replace("the_test_status", "True")
                    else:
                        new_lines[i] = new_lines[i].replace("the_test_status", "False")
                if '"gam"' in new_lines[i]:
                    new_lines[i] = new_lines[i].replace('"gam"', '"lm"')

                new_lines[i] = new_lines[i].replace("the_lon_lim", str(lon_lim))
                new_lines[i] = new_lines[i].replace("the_lat_lim", str(lat_lim))
                new_lines[i] = new_lines[i].replace(
                    "fixed_scale_value", str(fixed_scale)
                )
                # replace concice_value with concice
                if "concise_value" in new_lines[i]:
                    if concise:
                        new_lines[i] = new_lines[i].replace("concise_value", "True")
                    else:
                        new_lines[i] = new_lines[i].replace("concise_value", "False")

            # write the new lines to the file
            with open(ff, "w") as file:
                for line in new_lines:
                    file.write(line + "\n")

        # sync the notebooks
        #
        os.system(f"jupytext --sync {book_dir}/notebooks/*.ipynb")

    # loop through notebooks and change fast_plot_value to fast_plot

    for ff in glob.glob(f"{book_dir}/notebooks/*.ipynb"):
        with open(ff, "r") as file:
            filedata = file.read()

        # Replace the target string
        filedata = filedata.replace("fast_plot_value", str(fast_plot))
        filedata = filedata.replace("data_dir_value", data_dir)
        filedata = filedata.replace("out_dir_value", out_dir)

        # Write the file out again
        with open(ff, "w") as file:
            file.write(filedata)

    # fix the toc using the function

    fix_toc(concise=concise, data_dir=data_dir, out_dir=out_dir, info = isinstance(sim_info, dict))

    for ff in glob.glob(f"{book_dir}/notebooks/*.ipynb"):
        ff_clean = ff.replace(".ipynb", ".py")
        if os.path.exists(ff_clean):
            os.remove(ff_clean)

    # move pml_logo to book directory

    shutil.copyfile(
        importlib.resources.files(__name__).joinpath("data/pml_logo.jpg"),
        f"{book_dir}/pml_logo.jpg",
    )

    os.system(f"jupyter-book build  {book_dir}/")

    stamps = [
        os.path.basename(x) for x in glob.glob(f"{book_dir}/notebooks/.trackers/*")
    ]
    stamps.append("nctoolkit_rwi_uhosarcenctoolkittmp")

    delete = []
    for x in stamps:
        delete += glob.glob("/tmp/*" + x + "*")

    for ff in delete:
        if os.path.exists(ff):
            if "nctoolkit" in x:
                os.remove(ff)

    out_ff = f"{book_dir}/_build/html/index.html"

    # create a symlink to the html file
    if os.path.exists(f"{out_dir}/oceanval_report.html"):
        os.remove(f"{out_dir}/oceanval_report.html")
    # os.symlink(f"{book_dir}/_build/html/index.html", f"{out_dir}/oceanval_report.html")
    # create a symlink with relative directory
    os.symlink(os.path.relpath(out_ff, out_dir), f"{out_dir}/oceanval_report.html")
    if view:
        webbrowser.open(
            "file://" + os.path.abspath(f"{book_dir}/_build/html/index.html")
        )
    if zip:
        # zip html only
        shutil.make_archive(
            f"{out_dir}/oceanval_html", "zip", f"{book_dir}/_build/html"
        )


def rebuild(data_dir="."):
    """
    Rebuild the validation report after modifying notebooks.
    Use this if you have modified the notebooks generated and want to create a new validation report.

    Parameters
    ----------
    data_dir : str
        The directory where the oceanval_report directory is located. Default is current directory.
    """
    # check data_dir exists
    if not os.path.exists(data_dir):
        raise ValueError(f"data_dir {data_dir} does not exist")
    # add a deprecation notice
    data_dir = os.path.expanduser(data_dir)
    data_dir = os.path.abspath(data_dir)

    os.system(f"jupyter-book build {data_dir}/oceanval_report/")

    webbrowser.open(
        "file://"
        + os.path.abspath(f"{data_dir}/oceanval_report/_build/html/index.html")
    )


try:
    from importlib.metadata import version as _version
except ImportError:
    from importlib_metadata import version as _version

try:
    __version__ = _version("oceanval")
except Exception:
    __version__ = "999"


def compare(model_dict=None, view=True, ask = True):
    """
    Compare pre-validated simulations.
    This function will compare the validation output from two simulations.

    Parameters
    ----------
    model_dict : dict
        A dictionary of model names and the paths to the validation output. Default is None.
        Example: {"model1": "/path/to/model1", "model2": "/path/to/model2"}
        If the models have different grids, put the model with the smallest grid first.
    view : bool
        Default is True. Open the comparison report in a web browser after it is generated.
    ask : bool
        Default is True. If the oceanval_comparison directory already exists, ask the user if

    """

    for key in model_dict.keys():
        # check that the path exists
        if not os.path.exists(model_dict[key]):
            raise ValueError(f"Path {model_dict[key]} does not exist")
        # convert to an absolute path
        model_dict[key] = os.path.abspath(model_dict[key])

    if os.path.exists("oceanval_comparison"):
        # get user input to decide if it should be removed
        if ask:
            user_input = input(
                "oceanval_comparison directory already exists. This will be emptied and replaced. Do you want to proceed? (y/n): "
            )
            if user_input.lower() != "y":
                print("Exiting")
                return None

        while True:
                files = glob.glob("oceanval_comparison/**/**/**", recursive=True)
                # list all files in oceanval_comparison, recursively
                for ff in files:
                    if ff.startswith("oceanval_comparison"):
                        try:
                            os.remove(ff)
                        except:
                            pass
                files = glob.glob("oceanval_comparison/**/**/**", recursive=True)
                # only list files
                files = [x for x in files if os.path.isfile(x)]
                if len(files) == 0:
                    break
        else:
            print("Exiting")
            return None

    if not os.path.exists("oceanval_comparison/compare"):
        # create directory recursively
        os.makedirs("oceanval_comparison/compare")

    # copy the pml logo
    shutil.copyfile(
        importlib.resources.files(__name__).joinpath("data/pml_logo.jpg"),
        "oceanval_comparison/pml_logo.jpg",
    )

    # move toc etc to oceanval_comparison/compare

    data_path = importlib.resources.files(__name__).joinpath("data/_toc.yml")

    out = "oceanval_comparison/compare/" + os.path.basename(data_path)
    shutil.copyfile(data_path, out)

    fix_toc_comparison()

    data_path = importlib.resources.files(__name__).joinpath("data/requirements.txt")

    out = "oceanval_comparison/compare/" + os.path.basename(data_path)

    shutil.copyfile(data_path, out)

    data_path = importlib.resources.files(__name__).joinpath("data/intro.md")

    out = "oceanval_comparison/compare/" + os.path.basename(data_path)

    shutil.copyfile(data_path, out)

    # copy config

    data_path = importlib.resources.files(__name__).joinpath("data/_config.yml")

    out = "oceanval_comparison/compare/" + os.path.basename(data_path)

    shutil.copyfile(data_path, out)
    # read in out and change some values
    with open(out, "r") as file:
        filedata = file.read()
    # Replace the target string
    filedata = filedata.replace("oceanval_report", "../oceanval_comparison")
    # Write the file out again
    with open(out, "w") as file:
        file.write(filedata)

    # copy the comparison_seasonal notebook

    # make sure the directory exists

    if not os.path.exists("oceanval_comparison/compare/notebooks"):
        # create directory recursively
        os.makedirs("oceanval_comparison/compare/notebooks")

    file1 = importlib.resources.files(__name__).joinpath(
        "data/comparison_seasonal.ipynb"
    )
    if (
        len(
            glob.glob(
                "oceanval_comparison/compare/notebooks/*comparison_seasonal.ipynb"
            )
        )
        == 0
    ):
        shutil.copyfile(
            file1, "oceanval_comparison/compare/notebooks/comparison_seasonal.ipynb"
        )

    model_dict_str = str(model_dict)

    with open(
        "oceanval_comparison/compare/notebooks/comparison_seasonal.ipynb", "r"
    ) as file:
        filedata = file.read()

    # Replace the target string
    filedata = filedata.replace("model_dict_str", model_dict_str)

    # Write the file out again

    with open(
        "oceanval_comparison/compare/notebooks/comparison_seasonal.ipynb", "w"
    ) as file:
        file.write(filedata)

    # now sort out the comparison_spatial notebook

    file1 = importlib.resources.files(__name__).joinpath(
        "data/comparison_spatial.ipynb"
    )
    if (
        len(
            glob.glob("oceanval_comparison/compare/notebooks/*comparison_spatial.ipynb")
        )
        == 0
    ):
        shutil.copyfile(
            file1, "oceanval_comparison/compare/notebooks/comparison_spatial.ipynb"
        )

    model_dict_str = str(model_dict)

    with open(
        "oceanval_comparison/compare/notebooks/comparison_spatial.ipynb", "r"
    ) as file:
        filedata = file.read()

    # Replace the target string
    filedata = filedata.replace("model_dict_str", model_dict_str)

    # Write the file out again

    with open(
        "oceanval_comparison/compare/notebooks/comparison_spatial.ipynb", "w"
    ) as file:
        file.write(filedata)

    # move the regional book

    file1 = importlib.resources.files(__name__).joinpath(
        "data/comparison_regional.ipynb"
    )
    if (
        len(
            glob.glob(
                "oceanval_comparison/compare/notebooks/*comparison_regional.ipynb"
            )
        )
        == 0
    ):
        shutil.copyfile(
            file1, "oceanval_comparison/compare/notebooks/comparison_regional.ipynb"
        )

    model_dict_str = str(model_dict)

    with open(
        "oceanval_comparison/compare/notebooks/comparison_regional.ipynb", "r"
    ) as file:
        filedata = file.read()

    # Replace the target string
    filedata = filedata.replace("model_dict_str", model_dict_str)

    # Write the file out again

    with open(
        "oceanval_comparison/compare/notebooks/comparison_regional.ipynb", "w"
    ) as file:
        file.write(filedata)

    # now to comparison_bias

    file1 = importlib.resources.files(__name__).joinpath("data/comparison_bias.ipynb")

    if (
        len(glob.glob("oceanval_comparison/compare/notebooks/*comparison_bias.ipynb"))
        == 0
    ):
        shutil.copyfile(
            file1, "oceanval_comparison/compare/notebooks/comparison_bias.ipynb"
        )

    model_dict_str = str(model_dict)

    with open(
        "oceanval_comparison/compare/notebooks/comparison_bias.ipynb", "r"
    ) as file:
        filedata = file.read()

    # Replace the target string
    filedata = filedata.replace("model_dict_str", model_dict_str)

    # Write the file out again

    with open(
        "oceanval_comparison/compare/notebooks/comparison_bias.ipynb", "w"
    ) as file:
        file.write(filedata)

    # figure out if both simulations have point data

    i = 0

    if i == 0:
        for ss in ["surface"]:
            file1 = importlib.resources.files(__name__).joinpath(
                "data/comparison_point.ipynb"
            )

            if (
                len(
                    glob.glob(
                        f"oceanval_comparison/compare/notebooks/*comparison_point_{ss}.ipynb"
                    )
                )
                == 0
            ):
                shutil.copyfile(
                    file1,
                    f"oceanval_comparison/compare/notebooks/comparison_point_{ss}.ipynb",
                )

            model_dict_str = str(model_dict)

            with open(
                f"oceanval_comparison/compare/notebooks/comparison_point_{ss}.ipynb",
                "r",
            ) as file:
                filedata = file.read()

            # Replace the target string
            filedata = filedata.replace("model_dict_str", model_dict_str)

            # Write the file out again

            with open(
                f"oceanval_comparison/compare/notebooks/comparison_point_{ss}.ipynb",
                "w",
            ) as file:
                file.write(filedata)
            # replace layer in the notebook with ss
            with open(
                f"oceanval_comparison/compare/notebooks/comparison_point_{ss}.ipynb",
                "r",
            ) as file:
                filedata = file.read()

            # Replace the target string
            filedata = filedata.replace("layer", ss)

            # Write the file out again

            with open(
                f"oceanval_comparison/compare/notebooks/comparison_point_{ss}.ipynb",
                "w",
            ) as file:
                file.write(filedata)

    # sync the notebooks

    os.system(
        "jupytext --set-formats ipynb,py:percent oceanval_comparison/compare/notebooks/*.ipynb"
    )

    add_chunks()

    # replace the test status in the notebooks
    books = glob.glob("oceanval_comparison/compare/notebooks/*.py")
    for book in books:
        with open(book, "r") as file:
            filedata = file.read()

        # Replace the target string
        filedata = filedata.replace("the_test_status", "False")

        # Write the file out again
        with open(book, "w") as file:
            file.write(filedata)

    # fix the chunks
    os.system("jupytext --sync oceanval_comparison/compare/notebooks/*.ipynb")

    # loop through notebooks and change fast_plot_value to fast_plot

    for ff in glob.glob("oceanval_comparison/compare/notebooks/*.ipynb"):
        with open(ff, "r") as file:
            filedata = file.read()

        # Replace the target string
        filedata = filedata.replace("fast_plot_value", "False")

        # Write the file out again
        with open(ff, "w") as file:
            file.write(filedata)

    os.system("jupyter-book build oceanval_comparison/compare/")
    import webbrowser

    if view:
        webbrowser.open(
            "file://"
            + os.path.abspath("oceanval_comparison/compare/_build/html/index.html")
        )


import tempfile


def temp_check():
    """
    Function to check temp files
    """

    mylist = [f for f in glob.glob("/tmp/*")]
    mylist = mylist + [f for f in glob.glob("/var/tmp/*")]
    mylist = mylist + [f for f in glob.glob("/usr/tmp/*")]
    mylist = [f for f in mylist if "nctoolkit" in f]

    mylist = [x for x in mylist if "ecoval_output" in x]

    session_info["old_files"] = mylist

    if len(mylist) > 0:
        if len(mylist) == 1:
            print(
                f"{len(mylist)} temporary file was created by oceanval in prior or current "
                f"sessions. Consider running oceanval.deep_clean!"
            )
        else:
            print(
                f"{len(mylist)} temporary files were created by oceanval in prior or current"
                f" sessions. Consider running oceanval.deep_clean!"
            )


temp_check()


def deep_clean():
    """
    Deep temp file cleaner.
    Remove all temporary files ever created by oceanval
    across all previous and current sesions
    """

    candidates = session_info["old_files"]

    mylist = [f for f in candidates if "nctoolkit" in f and "ecoval_output" in f]
    for ff in mylist:
        if ff in session_info["old_files"]:
            if "nctoolkit" in ff and "ecoval_output" in ff:
                os.remove(ff)
