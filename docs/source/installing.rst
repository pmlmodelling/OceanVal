Installation and a quick example
============

**System requirements** You will need to run this on a Linux system.

You will need to use Conda to use oceanVal. The first step is to create a new environment::

   $ conda env create --name oceanval -f https://raw.githubusercontent.com/pmlmodelling/oceanval/main/oceanval.yml
   $ conda activate oceanval

Once you have done that, install the development version from GitHub::

   $ pip install git+https://github.com/pmlmodelling/oceanval.git


A short example
-------------------

If you want to quickly understand what oceanVal can do, you can run the following example in a Python script or Jupyter notebook. It should take a couple of minutes to run. 

Note: you should run this from an empty directory.


.. code:: ipython3

   import os
   import oceanval

   url = "http://noresg.nird.sigma2.no/thredds/fileServer/esg_dataroot/cmor/CMIP6/CMIP/NCC/NorESM2-LM/historical/r3i1p1f1/Omon/tos/gn/v20190920/tos_Omon_NorESM2-LM_historical_r3i1p1f1_gn_201001-201412.nc"

   # download this file

   out = os.path.basename(url)

   os.system(f"wget {url} -O {out}")


   oceanval.add_gridded_comparison(
      recipe = {"temperature":"cobe2"},
       model_variable = "tos"
   )

   oceanval.matchup(sim_dir = ".",
                  start = 2014, end = 2014,
                  n_dirs_down = 0,
                  cores = 1,
                  lon_lim = [-180, 180], lat_lim = [-90, 90],
                  ask = False
                  )
   
   oceanval.validate(concise = False, region = "global")



This quick example will compare sea surface temperature for 2014 from a global climate model simulation with an observational dataset.
An html page should open in your browser showing how the two compare.
In this case a built-in recipe is used for downloading the COBE2 sea surface temperature dataset [https://psl.noaa.gov/data/gridded/data.cobe2.html].

Note: this is just an example of the use of oceanVal, not a rigorous way to validate a climate model.