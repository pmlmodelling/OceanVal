import warnings
from oceanval.parsers import Validator
from oceanval.session import session_info


def ignore_warning(x):
    """
    Parameters
    -------------
    x: str
        Warning message

        Returns
        -------------
        True if the warning should be ignored
        False if the warning should not be ignored
    """
    if "Adding a time series with the same number of time steps" in x:
        return True
    # did not have valid years
    if "did not have valid years" in x:
        return True
    if "There is only file in the dataset. No need to merge" in x:
        return True
    if "warning (find_time_vars): time variable >time< not found" in x:
        return True
    if "time bounds unsupporte" in x:
        return True
    if "deflate" in x:
        return True
    if "None of the points are contained" in x:
        return True
    if "inconsistent variable" in x:
        return True
    if "inconsistent data" in x:
        return True
    if "0 as the fill value" in x:
        return True
    if "found more than one time variabl" in x:
        return True
    if "coordinates variable time" in x and "be assigned" in x:
        return True
    if "time bounds unsupported by this operator" in x:
        return True
    return False



def tidy_warnings(w):
    # A function to tidy up the warnings
    out_warnings = []
    for x in w:
        x_message = str(x.message)
        bad = True
        bad = ignore_warning(x_message) is False
        if bad:
            out_warnings.append(x_message)
    for ww in out_warnings:
        if "months were missing" not in ww:
            warnings.warn(ww)
