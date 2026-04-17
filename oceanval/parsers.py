import nctoolkit as nc
import re
import pandas as pd
import os
import glob
import warnings
from oceanval.session import session_info


def read_point(ff, nrows = None):
    try:
        df = pd.read_csv(ff, nrows=nrows)   
        return df
    except:
        pass 
    compressions = ['infer', 'gzip', 'bz2', 'zip', 'xz']
    for compression in compressions: 
        try:
            df = pd.read_csv(ff, compression = compression, nrows=nrows)   
            return df
        except:
            pass
    raise ValueError(f"Could not read file {ff} with any of the following compression types: {compressions}. Error: {e}")


# create a validator class
# create a variable class to hold metadata
class Variable:
    def __str__(self):
    # add a print method for each atrribute
        attrs = vars(self)
        return '\n'.join("%s: %s" % item for item in attrs.items())  
    # add a repr method
    def __repr__(self):
        attrs = vars(self)
        return '\n'.join("%s: %s" % item for item in attrs.items()) 


class Validator:

    #keys = session_info["keys"]
    keys = [] 
    # add a deleter that removes from keys list
    def __delattr__(self, name):
        if name != "keys":
            if name in self.keys:
                self.keys.remove(name)
        super().__delattr__(name)
    # add remove method
    def remove(self, name):
        if name != "keys":
            if name in self.keys:
                self.keys.remove(name)
        super().__delattr__(name)

    # add reset method
    def reset(self):
        for key in self.keys:
            super().__delattr__(key)
        self.keys = []

    # ensure self.x = y, adds x to the keys list
    def __setattr__(self, name, value):
        if name != "keys":
            if name not in self.keys:
                self.keys.append(name)
                # ensure this can be accessed via self[name]

        super().__setattr__(name, value)

    # create a [] style accessor
    # make Validator subsettable, so that validator["chlorophyll"] returns the chlorophyll variable
    def __getitem__(self, key):
        return getattr(self, key, None)
    
    
    # 
    def add_gridded_comparison(self, 
                               name = None, 
                               long_name = None, 
                               short_name = None, 
                               short_title = None, 
                               source = None, 
                               source_info = None, 
                               model_variable = None, 
                               obs_path = None, 
                               obs_variable = None, 
                               start = -1000, 
                               end = 3000, 
                               vertical = False, 
                               climatology = None, 
                               obs_multiplier = 1,
                               obs_adder = 0,
                               thredds = False,
                               file_check = True
                                   ): 
        """

        Add a gridded comparison variable to the Validator

        Parameters:

        name (str): Name of the variable

        long_name (str): Long name of the variable

        short_name (str): Short name of the variable

        short_title (str): Short title of the variable

        source (str): Source of the variable

        source_info (str): Source information of the variable

        model_variable (str): Model variable name

        obs_path (str): Directory or path of the observations

        obs_variable (str): Observation variable name

        start (int): Start depth of the variable

        end (int): End depth of the variable

        vertical (bool): Whether the variable is vertical

        climatology (bool): Whether to use climatology

        obs_multiplier (float): Multiplier for the observation

        obs_adder (float): Adder for the observation

        file_check (bool): Whether to check if the obs_path exists and variables are valid

        """

        # maybe include an averaging option: daily, monthly, annual etc.

        if name is None:
            raise ValueError("Name must be supplied for gridded comparison")
        
        # name can only have str or numbers
        if not re.match("^[A-Za-z0-9]+$", name):
            raise ValueError("Name can only contain letters and numbers")

        if source is None:
            raise ValueError("Source must be supplied")
        if model_variable is None:
            raise ValueError("Model variable must be supplied")
        # climatology must be provideded
        if climatology is None:
            raise ValueError("Climatology must be provided for gridded comparison")
        # obs_path is needed
        if obs_path is None:
            raise ValueError("obs_path must be provided for gridded comparison")
        # must be boolean
        if not isinstance(climatology, bool):
            raise ValueError("Climatology must be a boolean value")
        try:
            obs_multiplier  = float(obs_multiplier)
        except:
            raise ValueError("obs_multiplier must be a number")

        try:
            obs_adder  = float(obs_adder)
        except:
            raise ValueError("obs_adder must be a number")

        assumed = []

        if long_name is None:
            try:
                long_name = self[name].long_name
            except:
                long_name = name
                assumed.append("long_name")

        if short_name is None:
            # use it, if it already exists
            try:
                short_name = self[name].short_name
            except:
                short_name = name
                assumed.append("short_name")
        if short_title is None:
            try:
                short_title = self[name].short_title
            except:
                short_title = name.title()
                assumed.append("short_title")

        if source_info is None:
            source_info = f"Source for {source}"
            assumed.append("source_info")

        source_name = source
        source = {source: source_info}
        # ensure the sourc key does not included "_"
        if "_" in source_name: 
            raise ValueError("Source cannot contain '_'")
        if not isinstance(obs_variable, str):
            raise ValueError("obs_variable be provided")

        gridded_dir = obs_path

        if file_check:
            if gridded_dir != "auto":
                if thredds is False:
                    if not os.path.exists(gridded_dir):
                        raise ValueError(f"Gridded directory {gridded_dir} does not exist")
        # thredds must be boolean
        if not isinstance(thredds, bool):
            raise ValueError("thredds must be a boolean value")
        
        # figure out if obs_variable exists in the files
        if isinstance(obs_path, list):
            sample_file = obs_path[0]
        else:
            if obs_path.endswith(".nc"):
                sample_file = obs_path
            else:
                sample_file = nc.glob(obs_path)[0]
        try:
            if thredds is True:
                ds = nc.open_thredds(sample_file)
            else:
                ds = nc.open_data(sample_file, checks = False )
        except:
            raise ValueError(f"Could not open observation data file {sample_file}")
        ds_variables = ds.variables
        if file_check:
            if obs_variable not in ds_variables:
                raise ValueError(f"obs_variable {obs_variable} not found in observation data files")

        if name in session_info["short_title"]:
            if short_title is not None:
                if short_title != session_info["short_title"][name]:
                    raise ValueError(f"Short title for {name} already exists as {session_info['short_title'][name]}, cannot change to {short_title}")


        # Figure out if name is already 

        # figure out if self[name] exists already
        if getattr(self, name, None) is None:
            var = Variable()
            setattr(self, name, var)
            self[name].point_dir = None
            self[name].point_source = None
            self[name].sources = source 
            self[name].point_start = -1000
            self[name].point_end = 3000
            self[name].vertical_point = None
            self[name].model_variable = None
            self[name].obs_multiplier = 1
            self[name].binning = None
            self[name].climatology = None
            self[name].sources = dict()

        else:
            if self[name].model_variable != model_variable:
                raise ValueError(f"Model variable for {name} already exists as {self[name].model_variable}, cannot change to {model_variable}")
            if self[name].sources is not None:
                orig_sources = self[name].sources
            if list(source.keys())[0] in orig_sources:
                # ensure the value is the same
                if orig_sources[list(source.keys())[0]] != source[list(source.keys())[0]]:
                    raise ValueError(f"Source {list(source.keys())[0]} already exists with a different value")

        self[name].sources[source_name] = source_info
        self[name].obs_adder_gridded = obs_adder
        self[name].thredds = thredds
        self[name].climatology = climatology
        self[name].obs_multiplier_gridded = obs_multiplier
        self[name].n_levels = 1
        self[name].vertical_gridded = vertical
        self[name].gridded_start = start
        self[name].gridded_end = end
        self[name].gridded = True
        self[name].long_name = long_name
        # if this is None set to Name
        self[name].short_name = short_name
        if self[name].short_name is None:
            self[name].short_name = name
            assumed.append("short_name")    
        self[name].short_title = short_title
        if self[name].short_title is None:
            self[name].short_title = name.title()
            assumed.append("short_title")
        # check if this is c
        session_info["short_title"][name] = self[name].short_title

        self[name].sources[source_name] = source_info 
        self[name].gridded_source = list(source.keys())[0]
        self[name].model_variable = model_variable
        # add obs_variable, ensure it's a string
        self[name].obs_variable = obs_variable
        # check this exists
        gridded_dir = obs_path
        self[name].gridded_dir = gridded_dir
        
        # ensure nothing is None
        # warnings for assumptions
        if len(assumed) > 0:
            print(f"Warning: The following attributes were missing and were assumed for variable {name}: {assumed}")


    def add_point_comparison(self, 
                             name = None, 
                             long_name = None, 
                             vertical = False, 
                             short_name = None, 
                             short_title = None, 
                             source = None, 
                             source_info = None, 
                             model_variable = None, 
                             start = -1000, 
                             end = 3000, 
                             obs_path = None, 
                             obs_multiplier = 1, 
                             obs_adder = 0,
                             binning = None  ):
        """

        Add a point comparison variable to the Validator

        Parameters:

        name (str): Name of the variable

        long_name (str): Long name of the variable

        vertical (bool): Whether the variable is vertical

        short_name (str): Short name of the variable

        short_title (str): Short title of the variable

        source (str): Source of the variable

        source_info (str): Source information of the variable

        model_variable (str): Model variable name

        start (int): Start depth of the variable

        end (int): End depth of the variable

        obs_path (str): Directory of the observations

        obs_multiplier (float): Multiplier for the observation, if needed to convert units

        binning (list): Binning information [lon_resolution, lat_resolution]

        """
        if name is None:
            raise ValueError("Name must be supplied")

        # check what is supplied is valid
        # name can only have str or numbers
        if not re.match("^[A-Za-z0-9]+$", name):
            raise ValueError("Name can only contain letters and numbers")

        if source is None:
            raise ValueError("Source must be supplied")
        source_name = source
        # ensure the sourc key does not included "_"
        if "_" in source: 
            raise ValueError("Source key cannot contain '_'")


        try:
            obs_multiplier= float(obs_multiplier)
        except:
            raise ValueError("obs_multiplier must be a number")
        try:
            obs_adder = float(obs_adder)
        except:
            raise ValueError("obs_adder must be a number")
        # vertical must be a boolean
        if not isinstance(vertical, bool):
            raise ValueError("vertical must be a boolean value")

        # check these are int or can be cast to int
        try:
            start = int(start)
            end = int(end)
        except:
            raise ValueError("start and end must be integers")

        assumed = []
        if source_info is None:
            source_info = f"Source for {source}"
            assumed.append("source_info")
        source = {source_name: source_info}
        if long_name is None:
            try:
                long_name = self[name].long_name
            except:
                long_name = name
                assumed.append("long_name")
        if short_name is None:
            # use it, if it already exists
            try:
                short_name = self[name].short_name
            except:
                short_name = name
                assumed.append("short_name")
        if short_title is None:
            try:
                short_title = self[name].short_title
            except:
                short_title = name.title()
                assumed.append("short_title")

        if name in session_info["short_title"]:
            if short_title != session_info["short_title"][name]:
                raise ValueError(f"Short title for {name} already exists as {session_info['short_title'][name]}, cannot change to {short_title}")
        
        # check obs path exists
        if os.path.exists(obs_path) is False:
            raise ValueError(f"Observation path {obs_path} does not exist")

        point_files = [f for f in glob.glob(os.path.join(obs_path, "*.csv"))] 
        # if no files exists, raise error
        if len(point_files) == 0:
            raise ValueError(f"No csv files found in point directory {obs_path}")
        valid_vars = ["lon", "lat", "year", "month", "day", "depth", "observation", "source"]
        vertical_option = False
        for vv in point_files:
            # read in the first row
            df = read_point(vv, nrows=1)
            # throw error something else is in there
            bad_cols = [col for col in df.columns if col not in valid_vars]
            if len(bad_cols) > 0:
                raise ValueError(f"Invalid columns {bad_cols} found in point data file {vv}")
            if "depth" in df.columns:
                vertical_option = True
            # lon/lat/observation *must* be in df
            for req_col in ["lon", "lat", "observation"]:
                if req_col not in df.columns:
                    raise ValueError(f"Required column {req_col} not found in point data file {vv}")
        if vertical_option is False:
            if vertical:
                raise ValueError("vertical is set to True but no depth column found in point data files. You cannot vertically validate this data.")
        # if binning is supplied, ensure it is a 2 variable list
        if binning is not None:
            if not isinstance(binning, list) or len(binning) != 2:
                raise ValueError("binning must be a list of two values: [spatial_resolution, depth_resolution]")
        # ensure each element of binning is a number
            for res in binning:
                try:
                    float(res)
                except:
                    raise ValueError("Each element of binning must be a number")
        # check this exists
        point_dir = obs_path
        if point_dir != "auto":
            if not os.path.exists(point_dir):
                raise ValueError(f"Point directory {point_dir} does not exist")

        # figure out if self[name] exists already
        if getattr(self, name, None) is None:
            # add it
            var = Variable()
            setattr(self, name, var)
            self[name].gridded = False
            self[name].vertical_gridded = None 
            self[name].sources = dict() 
            self[name].gridded_source = None 
            self[name].thredds = None 
            self[name].gridded_dir = None 
            self[name].obs_variable = None 
        else:
            # ensure short title is the same
            if short_title != session_info["short_title"][name]:
                raise ValueError(f"Short title for {name} already exists as {session_info['short_title'][name]}, cannot change to {short_title}")

            if self[name].model_variable != model_variable:
                old_model_variable = self[name].model_variable
                raise ValueError(f"Model variable for {name} already exists as {old_model_variable}, cannot change to {model_variable}")
            if self[name].sources is not None:
                orig_sources = self[name].sources
            if list(source.keys())[0] in orig_sources:
                # ensure the value is the same
                if orig_sources[list(source.keys())[0]] != source[list(source.keys())[0]]:
                    raise ValueError(f"Source {list(source.keys())[0]} already exists with a different value")

        self[name].sources[source_name] = source_info
        self[name].obs_multiplier_point= obs_multiplier
        self[name].obs_adder_point = obs_adder
        self[name].n_levels = 1
        self[name].long_name = long_name
        if self[name].long_name is None:
            self[name].long_name = name
            assumed.append("long_name")

        self[name].vertical_point = vertical
        self[name].short_name = short_name
        if self[name].short_name is None:
            self[name].short_name = name
            assumed.append("short_name")

        self[name].short_title = short_title
        if self[name].short_title is None:
            self[name].short_title = name.title()
            assumed.append("short_title")
        self[name].point_start = start
        self[name].point_end = end
        # append source to the var.source
        # check if source key is in orig_source
        self[name].point_source = list(source.keys())[0]   
        self[name].model_variable = model_variable
        self[name].point_dir = obs_path

        # figure out if var.binning exists
        self[name].binning = binning 
        #  
        for vv in assumed:
            print(f"Warning: The attribute {vv} was missing and was assumed for variable {name}")
        session_info["short_title"][name] = short_title

definitions = Validator()


def generate_mapping(ds):
    """
    Generate mapping of model and observational variables
    """

    model_dict = {}
    try:
        candidate_variables = definitions.keys
        ds1 = nc.open_data(ds[0], checks=False)
        ds_contents = ds1.contents

        ds_contents["long_name"] = [str(x) for x in ds_contents["long_name"]]

        ds_contents_top = ds_contents.query("nlevels == 1").reset_index(drop=True)
        n_levels = int(ds_contents.nlevels.max())
        if n_levels > session_info["n_levels"]:
            session_info["n_levels"] = n_levels
        # number of rows in ds_contents
        if len(ds_contents) == 0:
            ds_contents = ds_contents_top
    except:
        return model_dict

    for vv in candidate_variables:
        variables = definitions[vv].model_variable.split("+")
        include = True
        for var in variables:
            if var not in ds_contents.variable.values:
                include = False
        if include:
            model_dict[vv] = definitions[vv].model_variable
            n_levels = ds_contents.query("variable in @variables")["nlevels"].max()
            if n_levels > definitions[vv].n_levels:
                definitions[vv].n_levels = n_levels 
            continue

    return model_dict
