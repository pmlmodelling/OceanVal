import nctoolkit as nc
import re
import pandas as pd
import os
import glob
import warnings
from oceanval.session import session_info

#session_info["keys"] = []

recipe_list = [
    {"chlorophyll": "occci"},
    {"oxygen": "woa23"},
    {"temperature": "cobe2"},
    {"salinity": "woa23"},
    {"nitrate": "woa23"},
    {"ammonium": "nsbc"},
    {"phosphate": "woa23"},
    {"silicate": "woa23"},
    {"kd490": "occci"},
    {"ph": "glodap"},
    {"alkalinity": "glodap"},
    # nsbc
    {"chlorophyll": "nsbc"},
    {"oxygen": "nsbc"},
    {"temperature": "nsbc"},
    {"salinity": "nsbc"},
    {"nitrate": "nsbc"},
    {"ammonium": "nsbc"},
    {"phosphate": "nsbc"},
    {"silicate": "nsbc"}

]

def find_recipe(x, start = None, end = None):
    output = dict()
    # check if there is only one key and one value
    if len(x.keys()) != 1:
        raise ValueError("Recipe dictionary must have exactly one key") 
    
    valid_recipes = dict()
    valid_recipes["nitrate"] = "nsbc"

    output["vertical"] = None

    name = x.keys()
    # first key
    name = list(name)[0]
    value = x[name]
    # add a suitable short name
    if name == "chlorophyll":
        output["short_name"] = "chlorophyll concentration"
    if name == "oxygen":
        output["short_name"] = "dissolved oxygen"
    if name == "temperature":
        output["short_name"] = "sea temperature"
    if name == "salinity":
        output["short_name"] = "salinity"
    if name == "nitrate":
        output["short_name"] = "nitrate concentration"
    if name == "ammonium":
        output["short_name"] = "ammonium concentration"
    if name == "phosphate":
        output["short_name"] = "phosphate concentration"
    if name == "silicate":
        output["short_name"] = "silicate concentration"
    # add a long name
    if name == "chlorophyll":
        output["long_name"] = "chlorophyll a concentration"
    if name == "oxygen":
        output["long_name"] = "dissolved oxygen concentration"
    if name == "temperature":
        output["long_name"] = "sea water temperature"
    if name == "salinity":
        output["long_name"] = "sea water salinity"
    if name == "nitrate":
        output["long_name"] = "nitrate concentration"
    if name == "ammonium":
        output["long_name"] = "ammonium concentration"
    if name == "phosphate":
        output["long_name"] = "phosphate concentration"
    if name == "silicate":
        output["long_name"] = "silicate concentration"
    # add title
    if name == "chlorophyll":
        output["short_title"] = "Chlorophyll"
    if name == "oxygen":
        output["short_title"] = "Oxygen"
    if name == "temperature":
        output["short_title"] = "Temperature"
    if name == "salinity":
        output["short_title"] = "Salinity"
    if name == "nitrate":
        output["short_title"] = "Nitrate"
    if name == "ammonium":
        output["short_title"] = "Ammonium"
    if name == "phosphate":
        output["short_title"] = "Phosphate"
    if name == "silicate":
        output["short_title"] = "Silicate"

    if name == "kd490":
        output["short_name"] = "KD490"
        output["short_title"] = "KD490"
        output["long_name"] = "diffuse attenuation coefficient at 490 nm"
    # COBE2 temperature options

    if name.lower() == "ph":
        output["short_name"] = "pH"
        output["long_name"] = "sea water pH"
        output["short_title"] = "pH"
    if name.lower() == "alkalinity":
        output["short_name"] = "total alkalinity"
        output["long_name"] = "sea water total alkalinity"
        output["short_title"] = "Total Alkalinity"
    
    if value.lower() == "glodap":
        if name.lower() == "ph":
            output["obs_path"]=  "https://www.ncei.noaa.gov/data/oceans/archive/arc0221/0286118/1.1/data/0-data/GLODAPv2.2016b_MappedClimatologies/GLODAPv2.2016b.pHtsinsitutp.nc"
            output["source"] = "GLODAPv2.2016b"
            output["source_info"] = "Lauvset, S. K., Key, R. M., Olsen, A., van Heuven, S., Velo, A., Lin, X., Schirnick, C., Kozyr, A., Tanhua, T., Hoppema, M., Jutterström, S., Steinfeldt, R., Jeansson, E., Ishii, M., Perez, F. F., Suzuki, T., and Watelet, S.: A new global interior ocean mapped climatology: the 1° ×  1° GLODAP version 2, Earth Syst. Sci. Data, 8, 325–340, https://doi.org/10.5194/essd-8-325-2016, 2016."
            output["name"] = name
            output["thredds"] = False
            output["climatology"] = True
            output["thredds"] = True
            output["obs_variable"] = 'pHtsinsitutp'
            return output
        if name.lower() == "alkalinity":
            output["obs_path"]=  "https://www.ncei.noaa.gov/data/oceans/archive/arc0221/0286118/1.1/data/0-data/GLODAPv2.2016b_MappedClimatologies/GLODAPv2.2016b.TAlk.nc"
            output["source"] = "GLODAPv2.2016b"
            output["source_info"] = "Lauvset, S. K., Key, R. M., Olsen, A., van Heuven, S., Velo, A., Lin, X., Schirnick, C., Kozyr, A., Tanhua, T., Hoppema, M., Jutterström, S., Steinfeldt, R., Jeansson, E., Ishii, M., Perez, F. F., Suzuki, T., and Watelet, S.: A new global interior ocean mapped climatology: the 1° ×  1° GLODAP version 2, Earth Syst. Sci. Data, 8, 325–340, https://doi.org/10.5194/essd-8-325-2016, 2016."
            output["name"] = name
            output["thredds"] = False
            output["climatology"] = True
            output["thredds"] = True
            output["obs_variable"] = 'TAlk'
            return output

    
    if value.lower() == "cobe2":
        if name.lower() == "temperature": 
            url = f"https://psl.noaa.gov/thredds/dodsC/Datasets/COBE2/sst.mon.mean.nc"
            output["obs_path"] = url
            output["source"] = "COBE2"
            output["source_info"] = "COBE-SST 2 and Sea Ice data provided by the NOAA PSL, Boulder, Colorado, USA, from their website at https://psl.noaa.gov/data/gridded/data.cobe2.html."
            output["name"] = name
            output["thredds"] = True
            output["climatology"] = False
            output["vertical"] = False
            output["obs_variable"] = "sst"

            return output 

    if value.lower() == "woa23":
        output["source"] = "WOA23"
        output["source_info"] = " Garcia, H.E., C. Bouchard, S.L. Cross, C.R. Paver, Z. Wang, J.R. Reagan, T.P. Boyer, R.A. Locarnini, A.V. Mishonov, O. Baranova, D. Seidov, and D. Dukhovskoy. World Ocean Atlas 2023, Volume 4: Dissolved Inorganic Nutrients (phosphate, nitrate, silicate). A. Mishonov, Tech. Ed. NOAA Atlas NESDIS 92, doi.org/10.25923/39qw-7j08"
        output["climatology"] = True
        output["name"] = name
        output["thredds"] = True

        if name.lower() == "nitrate":
            url = []
            for month in range(1,13):
                # format month to two digits
                month_str = f"{month:02d}"
                url.append(f"https://www.ncei.noaa.gov/thredds-ocean/dodsC/woa23/DATA/nitrate/netcdf/all/1.00/woa23_all_n{month_str}_01.nc")
            output["obs_path"] = url
            output["obs_variable"] = "n_an"
            return output

        # now do oxygen

        if name.lower() == "oxygen":
            url = []
            for month in range(1,13):
                # format month to two digits
                month_str = f"{month:02d}"
                #https://www.ncei.noaa.gov/thredds-ocean/dodsC/woa23/DATA/oxygen/netcdf/all/1.00/woa23_all_o01_01.nc.html
                url.append(f"https://www.ncei.noaa.gov/thredds-ocean/dodsC/woa23/DATA/oxygen/netcdf/all/1.00/woa23_all_o{month_str}_01.nc")
            output["obs_path"] = url
            output["name"] = name
            output["obs_variable"] = "o_an"
            return output
        # phosphate
        if name.lower() == "phosphate":
            output["obs_variable"] = "p_an"
            url = []
            for month in range(1,13):
                # format month to two digits
                month_str = f"{month:02d}"
                url.append(f"https://www.ncei.noaa.gov/thredds-ocean/dodsC/woa23/DATA/phosphate/netcdf/all/1.00/woa23_all_p{month_str}_01.nc")
            output["obs_path"] = url
            return output
        
        # silicate
        if name.lower() == "silicate":
            output["obs_variable"] = "i_an"
            url = []
            for month in range(1,13):
                # format month to two digits
                month_str = f"{month:02d}"
                url.append(f"https://www.ncei.noaa.gov/thredds-ocean/dodsC/woa23/DATA/silicate/netcdf/all/1.00/woa23_all_i{month_str}_01.nc")
            output["obs_path"] = url
            return output
        # temperature/salinity
        if name.lower() in ["salinity", "temperature"]:
            # check if start and end are provided
            if start is None or end is None:

                valid_periods = [""]
                raise ValueError("Start and end depth must be provided for salinity and temperature WOA23 recipes")
            # valid time period are
            # 1955-1964
            # 1965-1974
            # 1975-1984
            # 1985-1994
            # 1995-2004
            # 2005-2014
            # 2015-2022
            # start and end must fall into one of these time periods
            # first check if they are more than 9 years apart
            if end - start > 9:
                raise ValueError("Start and end depth must fall within a single WOA23 climatological period (10 year periods)")
            # identify the period it is in based on start year
            if start >= 1955 and end <= 1964:
                period = "5564"
            elif start >= 1965 and end <= 1974:
                period = "6574"
            elif start >= 1975 and end <= 1984:
                period = "7584"
            elif start >= 1985 and end <= 1994:
                period = "8594"
            elif start >= 1995 and end <= 2004:
                period = "95A4"
            elif start >= 2005 and end <= 2014:
                period = "A5B4"
            elif start >= 2015 and end <= 2022:
                period = "B5C2"
            if end > 2022:
                raise ValueError("End year cannot be greater than 2022 for WOA23 recipes")

                #https://www.ncei.noaa.gov/thredds-ocean/dodsC/woa23/DATA/temperature/netcdf/5564/1.00/woa23_5564_t00_01.nc.html
            #url = f"https://www.ncei.noaa.gov/thredds-ocean/dodsC/woa23/DATA/{name.lower()}/netcdf/{period.replace('-', '')}/1.00/woa23_{period.replace('-', '')}_{name[0].lower()}00_01.nc"
            urls = []
            for month in range(1,13):
                month_str = f"{month:02d}"
                #https://www.ncei.noaa.gov/thredds-ocean/dodsC/woa23/DATA/temperature/netcdf/5564/1.00/woa23_5564_t00_01.nc.html
                urls.append(f"https://www.ncei.noaa.gov/thredds-ocean/dodsC/woa23/DATA/{name.lower()}/netcdf/{period}/1.00/woa23_{period}_{name[0].lower()}{month_str}_01.nc")
                #urls.append(url)

            output["obs_path"] = urls
            output["name"] = name
            if name.lower() == "salinity":
                output["obs_variable"] = "s_an"
            if name.lower() == "temperature":
                output["obs_variable"] = "t_an"
            return output

    if value == "occci":
        urls = []
        if name == "chlorophyll":
            for yy in range(1998, 2025):
                for month in range(1, 13):
                    month_str = f"{month:02d}"
                    url = f"https://www.oceancolour.org/thredds/dodsC/cci/v6.0-release/geographic/monthly/chlor_a/{yy}/ESACCI-OC-L3S-CHLOR_A-MERGED-1M_MONTHLY_4km_GEO_PML_OCx-{yy}{month_str}-fv6.0.nc"
                    urls.append(url)
            output["obs_path"] = urls
            output["source"] = "OCCCI"
            output["source_info"] = "Sathyendranath, S, Brewin, RJW, Brockmann, C, Brotas, V, Calton, B, Chuprin, A, Cipollini, P, Couto, AB, Dingle, J, Doerffer, R, Donlon, C, Dowell, M, Farman, A, Grant, M, Groom, S, Horseman, A, Jackson, T, Krasemann, H, Lavender, S, Martinez-Vicente, V, Mazeran, C, Mélin, F, Moore, TS, Müller, D, Regner, P, Roy, S, Steele, CJ, Steinmetz, F, Swinton, J, Taberner, M, Thompson, A, Valente, A, Zühlke, M, Brando, VE, Feng, H, Feldman, G, Franz, BA, Frouin, R, Gould, Jr., RW, Hooker, SB, Kahru, M, Kratzer, S, Mitchell, BG, Muller-Karger, F, Sosik, HM, Voss, KJ, Werdell, J, and Platt, T (2019) An ocean-colour time series for use in climate studies: the experience of the Ocean-Colour Climate Change Initiative (OC-CCI). Sensors: 19, 4285. doi:10.3390/s19194285."
            # short name
            output["short_name"] = "chlorophyll concentration"
            output["name"] = name
            output["obs_variable"] = "chlor_a"
            output["thredds"] = True
            output["climatology"] = False
            return output

    # kd490
    if name == "kd490":
        for yy in range(1998, 2025):
            for month in range(1, 13):
                month_str = f"{month:02d}"
                #https://www.oceancolour.org/thredds/dodsC/cci/v6.0-release/geographic/monthly/kd/1997/ESACCI-OC-L3S-K_490-MERGED-1M_MONTHLY_4km_GEO_PML_KD490_Lee-199709-fv6.0.nc.html
                url = f"https://www.oceancolour.org/thredds/dodsC/cci/v6.0-release/geographic/monthly/kd/{yy}/ESACCI-OC-L3S-K_490-MERGED-1M_MONTHLY_4km_GEO_PML_KD490_Lee-{yy}{month_str}-fv6.0.nc"
                urls.append(url)
        output["obs_path"] = urls
        output["source"] = "OCCCI"
        output["source_info"] = "Sathyendranath, S, Brewin, RJW, Brockmann, C, Brotas, V, Calton, B, Chuprin, A, Cipollini, P, Couto, AB, Dingle, J, Doerffer, R, Donlon, C, Dowell, M, Farman, A, Grant, M, Groom, S, Horseman, A, Jackson, T, Krasemann, H, Lavender, S, Martinez-Vicente, V, Mazeran, C, Mélin, F, Moore, TS, Müller, D, Regner, P, Roy, S, Steele, CJ, Steinmetz, F, Swinton, J, Taberner, M, Thompson, A, Valente, A, Zühlke, M, Brando, VE, Feng, H, Feldman, G, Franz, BA, Frouin, R, Gould, Jr., RW, Hooker, SB, Kahru, M, Kratzer, S, Mitchell, BG, Muller-Karger, F, Sosik, HM, Voss, KJ, Werdell, J, and Platt, T (2019) An ocean-colour time series for use in climate studies: the experience of the Ocean-Colour Climate Change Initiative (OC-CCI). Sensors: 19, 4285. doi:10.3390/s19194285."
        output["name"] = name
        output["obs_variable"] = "kd_490"
        output["thredds"] = True
        output["climatology"] = False
        return output

    if value.lower() == "nsbc":
        if name.lower() in ["ammonium", "nitrate", "phosphate", "silicate", "chlorophyll", "oxygen", "temperature", "salinity"]:
            if name.lower() == "chlorophyll":
                url = f"https://icdc.cen.uni-hamburg.de/thredds/dodsC/ftpthredds/nsbc/level_3/climatological_monthly_mean/NSBC_Level3_{'chlorophyll_a'}__UHAM_ICDC__v1.1__0.25x0.25deg__OAN_1960_2014.nc"
            else:
                url = f"https://icdc.cen.uni-hamburg.de/thredds/dodsC/ftpthredds/nsbc/level_3/climatological_monthly_mean/NSBC_Level3_{name}__UHAM_ICDC__v1.1__0.25x0.25deg__OAN_1960_2014.nc"
            output["obs_path"] = url
            output["source"] = "NSBC"
            output["source_info"] = "Hinrichs, Iris; Gouretski, Viktor; Paetsch, Johannes; Emeis, Kay; Stammer, Detlef (2017). North Sea Biogeochemical Climatology (Version 1.1)."
            output["name"] = name
            output["thredds"] = True
            output["climatology"] = True
            if name.lower() == "ammonium":
                output["obs_variable"] = "ammonium_mean"
            if name.lower() == "nitrate":
                output["obs_variable"] = "nitrate_mean"
            if name.lower() == "phosphate":
                output["obs_variable"] = "phosphate_mean"
            if name.lower() == "silicate":
                output["obs_variable"] = "silicate_mean"
            if name.lower() == "chlorophyll":
                output["obs_variable"] = "chlorophyll_a_mean"
            if name.lower() == "oxygen":
                output["obs_variable"] = "oxygen_mean"
            if name.lower() == "temperature":
                output["obs_variable"] = "temperature_mean"
            if name.lower() == "salinity":
                output["obs_variable"] = "salinity_mean"

            return output

    raise ValueError(f"Recipe value {value} is not valid for recipe name {name}")

    return x


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
                               recipe = None,
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

        if recipe is not None:
            recipe_info = find_recipe(recipe, start = start, end = end)
            obs_path = recipe_info["obs_path"]
            source = recipe_info["source"]
            if source == "GLODAPv2.2016b": 
                # no need to check file
                file_check = False
            source_info = recipe_info["source_info"]
            thredds = recipe_info["thredds"]
            climatology = recipe_info["climatology"]
            name = recipe_info["name"]
            short_name = recipe_info["short_name"]
            long_name = recipe_info["long_name"]
            short_title = recipe_info["short_title"]
            # vertical is not None
            if recipe_info["vertical"] is not None:
                vertical = recipe_info["vertical"]
            obs_variable = recipe_info["obs_variable"]
            recipe = True
        else:
            recipe = False

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
        self[name].recipe = recipe
        
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
            df = pd.read_csv(vv, nrows=1)
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
            self[name].recipe = None 
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


class SummaryVariable:
    """Class to hold metadata for summary variables"""
    def __init__(self):
        self.name = None
        self.model_variable = None
        self.long_name = None
        self.short_name = None
        self.units = None
        self.vertical_integration = False
        self.vertical_merage = False
        self.horizontal_average = False
        
    def __str__(self):
        attrs = vars(self)
        return '\n'.join("%s: %s" % item for item in attrs.items())
    
    def __repr__(self):
        attrs = vars(self)
        return '\n'.join("%s: %s" % item for item in attrs.items())


class Summary:
    """
    Summary class for defining variables to be summarized from model output.
    
    This class allows you to specify how variables should be processed for summaries,
    including vertical integration, vertical averaging, horizontal averaging, etc.
    """
    
    keys = []
    
    def __delattr__(self, name):
        """Remove variable from keys list when deleted"""
        if name != "keys":
            if name in self.keys:
                self.keys.remove(name)
        super().__delattr__(name)
    
    def remove(self, name):
        """Remove a variable from the summary definitions"""
        if name != "keys":
            if name in self.keys:
                self.keys.remove(name)
        super().__delattr__(name)
    
    def reset(self):
        """Reset all summary definitions"""
        for key in self.keys:
            super().__delattr__(key)
        self.keys = []
    
    def __setattr__(self, name, value):
        """Add variable name to keys list when set"""
        if name != "keys":
            if name not in self.keys:
                self.keys.append(name)
        super().__setattr__(name, value)
    
    def __getitem__(self, key):
        """Allow dictionary-style access to variables"""
        return getattr(self, key, None)
    
    def add_summary(
        self,
        name=None,
        start = None,
        end = None,
        model_variable=None,
        long_name=None,
        short_name=None,
        short_title=None,   
        trends = None, 
        vertical_integration=False,
        vertical_mean =False,
        climatology_years = None,
        robust = False
    ):
        """
        Add a variable to be summarized from model output.
        
        Parameters
        ----------
        name : str
            Name identifier for the variable. Must contain only letters and numbers.
        model_variable : str
            Name of the variable in the model output files.
        long_name : str, optional
            Long descriptive name for the variable.
        short_name : str, optional
            Short name for the variable. Defaults to name if not provided.
        trends : dict
            Dictionary specifying trend calculation parameters with keys:
            'period' (list of two ints): Start and end years for trend calculation.
            'window' (int): Window size in years for trend smoothing.
        vertical_integration : bool, default False
            Whether to vertically integrate the variable.
        vertical_mean : bool, default False
            Whether to vertically average the variable.
        robust : bool, default False
            Whether to use a robust plot for climatologies 
        
        Returns
        -------
        None
        
        Raises
        ------
        ValueError
            If name is not provided, contains invalid characters, or if both
            vertical_integration and vertical_mean are True.
        
        Examples
        --------
        >>> summary = Summary()
        >>> summary.add_summary(
        ...     name="temperature",
        ...     model_variable="temp",
        ...     long_name="Sea Water Temperature",
        ...     vertical_mean=True,
        ... )
        """
        if start is None:
            raise ValueError("start year must be provided")
        if end is None:
            raise ValueError("end year must be provided")

        # climatology_years must be a list of two integers if provided
        if climatology_years is None:
            raise ValueError("climatology_years must be provided as [start_year, end_year]")
        if climatology_years is not None:
            if not isinstance(climatology_years, (list, tuple)):
                raise ValueError("climatology_years must be a list or tuple of two integers [start_year, end_year]")
            if len(climatology_years) != 2:
                raise ValueError("climatology_years must contain exactly 2 values [start_year, end_year]")
            try:
                start_year = int(climatology_years[0])
                end_year = int(climatology_years[1])
                if start_year > end_year:
                    raise ValueError("start_year must be less than end_year in climatology_years")
            except (TypeError, ValueError) as e:
                raise ValueError("climatology_years values must be integers")
        
        # check robust is boolean
        if not isinstance(robust, bool):
            raise ValueError("robust must be a boolean value")
        
        # Validate required parameters
        if name is None:
            raise ValueError("Name must be provided")
        
        # Validate name contains only letters and numbers
        if not re.match("^[A-Za-z0-9]+$", name):
            raise ValueError("Name can only contain letters and numbers")
        
        if model_variable is None:
            raise ValueError("Model variable must be provided")
        
        # check trends is a dict with period and window
        if trends is not None:
            if not isinstance(trends, dict):
                raise ValueError("trends must be a dictionary with keys 'period' and 'window'")
            if "period" not in trends or "window" not in trends:
                raise ValueError("trends dictionary must contain 'period' and 'window' keys")
       # if short_name doesn't exist, set to name
        if short_name is None:
            short_name = name 
        if long_name is None:
            long_name = short_name  
        
        # if short_title is not provided, take it from short_name and capitalize
        if short_title is None:
            if short_name is not None:
                short_title = short_name.title()
            else:
                short_title = name.title()
        
        # Create variable if it doesn't exist, or get existing one
        if getattr(self, name, None) is None:
            var = SummaryVariable()
            setattr(self, name, var)
        else:
            var = self[name]
        
        var.trends = trends
        var.robust = robust 
        # Set attributes
        var.name = name
        var.start = start
        var.end = end
        var.model_variable = model_variable
        var.climatology_years = climatology_years
        var.short_title = short_title
        
        # Set optional attributes with defaults
        if long_name is not None:
            var.long_name = long_name
        else:
            var.long_name = name if var.long_name is None else var.long_name
        
        if short_name is not None:
            var.short_name = short_name
        else:
            var.short_name = name if var.short_name is None else var.short_name
        
        var.vertical_integration = vertical_integration
        var.vertical_mean= vertical_mean
        if var.vertical_integration or var.vertical_mean:
            var.vertical = True
        else:
            var.vertical = False


summaries = Summary()


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

def generate_mapping_summary(ds):
    """
    Generate mapping of model and observational variables
    """

    model_dict = {}
    try:
        candidate_variables = summaries.keys
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
        variables = summaries[vv].model_variable.split("+")
        include = True
        for var in variables:
            if var not in ds_contents.variable.values:
                include = False
        if include:
            model_dict[vv] = summaries[vv].model_variable
            n_levels = ds_contents.query("variable in @variables")["nlevels"].max()
            continue

    return model_dict
