Installation and a quick example
============

**System requirements** You will need to run this on a Linux system.


OceanVal should be used with Python versions 3.10-3.13.

The best way to install OceanVal is via conda. You will need to have conda installed first. If you do not have conda installed, please follow the instructions at https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html.
Once you have conda installed, you can create a new conda environment and install OceanVal using the following command:

   $ conda install conda-forge::oceanval 


A short example
-------------------

If you want to quickly understand what OceanVal can do, you can run the following example in a Python script or Jupyter notebook. It should take a couple of minutes to run. 

This example can be viewed `here <https://pmlmodelling.github.io/oceanval_example/intro.html>`_.

Note: you should run this from an empty directory.


.. code:: ipython3

   import os
   import oceanval

   url = "http://noresg.nird.sigma2.no/thredds/fileServer/esg_dataroot/cmor/CMIP6/CMIP/NCC/NorESM2-LM/historical/r3i1p1f1/Omon/tos/gn/v20190920/tos_Omon_NorESM2-LM_historical_r3i1p1f1_gn_201001-201412.nc"

   # download this file

   out = os.path.basename(url)

   os.system(f"wget {url} -O {out}")

   oceanval.add_gridded_comparison(
           name = "temperature",
           obs_path = "https://psl.noaa.gov/thredds/dodsC/Datasets/COBE2/sst.mon.mean.nc",
           thredds = True,
           source = "COBE2",
       model_variable = "tos",
       climatology = False,
       obs_variable = "sst"
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
In this the COBE2 sea surface temperature dataset [https://psl.noaa.gov/data/gridded/data.cobe2.html] is downloaded from a thredds server.

Note: this is just an example of the use of OceanVal, not a rigorous way to validate a climate model.
