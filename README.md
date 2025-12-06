[![Documentation Status](https://readthedocs.org/projects/oceanval/badge/?version=latest)](https://oceanval.readthedocs.io/en/latest/?badge=latest)
[![Conda Badge](https://anaconda.org/conda-forge/oceanval/badges/version.svg)](https://anaconda.org/channels/conda-forge/packages/oceanval/overview)
![GitHub Testing](https://github.com/pmlmodelling/oceanVal/actions/workflows/python-app.yml/badge.svg)
![GitHub Testing](https://github.com/pmlmodelling/oceanVal/actions/workflows/python-app-macos.yml/badge.svg)
[![codecov](https://codecov.io/gh/pmlmodelling/oceanVal/graph/badge.svg?token=RLHUN0F9W7)](https://codecov.io/gh/pmlmodelling/oceanVal)





# oceanVal 
Marine ecosystem model validation made easy in Python


# Installation 

oceanVal should be used with Python versions 3.10-3.13.

You can install the latest release oceanVal from conda-forge as follows:

```sh
conda install conda-forge::oceanval
```

You can install the development version of oceanVal from GitHub using the following steps.

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

A website and user guide is available at: https://oceanval.readthedocs.io/en/latest/.
