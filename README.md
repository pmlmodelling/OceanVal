<p align="center">
  <img src="docs-site/assets/img/oceanval_wordmark.svg" alt="OceanVal" width="380">
</p>

> [!TIP]
> 📖 **New here?** The full documentation — installing, quickstart, recipes, the API reference, and more — lives at **[pmlmodelling.github.io/OceanVal](https://pmlmodelling.github.io/OceanVal/)**.

[![Documentation Status](https://readthedocs.org/projects/oceanval/badge/?version=latest)](https://oceanval.readthedocs.io/en/latest/?badge=latest)
[![Conda Badge](https://anaconda.org/conda-forge/oceanval/badges/version.svg)](https://anaconda.org/channels/conda-forge/packages/oceanval/overview)
![GitHub Testing](https://github.com/pmlmodelling/oceanVal/actions/workflows/python-app.yml/badge.svg)





# OceanVal 

Ocean model validation made easy in Python.

To learn more about the package, visit the [OceanVal website](https://pmlmodelling.github.io/OceanVal/). The

OceanVal is designed for the automated creation of validation reports. You provide the model and validation data. OceanVal does the rest. A short example of what the report looks like can be found [here](https://pmlmodelling.github.io/oceanval_example/index.html). 

## Using built-in recipes

You can register a standard observation climatology without manually listing all metadata:

```python
import oceanval

oceanval.add_gridded_comparison(
    name="temperature",
    source="WOA23",
    model_variable="temp",
    recipe={"temperature": "woa23"},
    start=2005,
    end=2014,
    climatology=True,
)
```

This uses the v0.2.0 recipe system for datasets such as WOA23, NSBC, OCCCI and GLODAP.

### Generating a matchup script

`create_recipes` writes the script for you. It scans your model output,
works out which model variable holds each observational variable — matching
on the netCDF `long_name` attributes, so your variables need not be named
after the observations — and writes out every built-in recipe. Recipes it
found a model variable for are live, with that variable filled in; the rest
are commented out for you to complete by hand. Where a variable has a
recipe in more than one region (e.g. temperature), `domain` picks which one
is left live — `"global"` or `"nwes"` (Northwest European Shelf) — and a
variable with a recipe only outside that domain still gets that one.

```python
import oceanval

oceanval.create_recipes(
    simdir="/path/to/model/output",
    ndown=2,   # how many directories down the output files sit
    out="matchup.py",
    domain="global",
    start=2005,   # passed straight through to matchup()
    end=2014,
)
```

## Comparing multiple validation outputs

To compare validation reports from multiple simulations:

```python
import oceanval

oceanval.compare(
    model_dict={
        "model_a": "/path/to/model_a",
        "model_b": "/path/to/model_b",
    },
    view=True,
    ask=True,
)
```

This recreates the v0.2.0 comparison workflow and writes the shared comparison report to `oceanval_comparison/compare/_build/html/index.html`.

# Installation 

OceanVal should be used with Python versions 3.10-3.13.

You can install the latest release OceanVal from conda-forge as follows:

```sh
conda install conda-forge::oceanval
```

You can install the development version of OceanVal from GitHub using the following steps.

First, clone this directory:

```sh
git clone https://github.com/pmlmodelling/oceanval.git
```

Then move to this directory.

```sh
cd oceanval
```


Second, set up a conda environment. If you want the envionment to called something other than `oceanval`, you can change the name in the oceanval.yml file. 

```sh
conda env create -f oceanval.yml
```



Activate this environment.

```sh
conda activate oceanval
```

Now, sometimes R package installs go wrong in conda. Run the following command to ensure Rcpp is installed correctly.

```sh
Rscript -e "install.packages('Rcpp', repos = 'https://cloud.r-project.org/')"
```

Now, install the package.

```sh
pip install .

```sh
conda activate oceanval
```


Now, install the package.

```sh
pip install .

```
Alternatively, install the conda environment and package using the following commands:

```sh
    conda env create --name oceanval -f https://raw.githubusercontent.com/pmlmodelling/oceanval/main/oceanval.yml
    conda activate oceanval​
    pip install git+https://github.com/pmlmodelling/oceanval.git​
```

