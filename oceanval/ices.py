"""Download point observations from the ICES oceanographic database.

Talks to the public API behind https://ocean.ices.dk: an export job is
queued, polled until it finishes, and its zipped ODV-style csv is read
straight into a dataframe in oceanval's point format.
"""

import io
import time
import zipfile

import pandas as pd
import requests

API_BASE = "https://ocean.ices.dk/api"
POLL_INTERVAL = 5
TIMEOUT = 1800

DEPTH_CODE = "ADEPZZ01"
TIME_COLUMN = "yyyy-mm-ddThh:mm:ss.sss"
LON_COLUMN = "Longitude [degrees_east]"
LAT_COLUMN = "Latitude [degrees_north]"
POINT_COLUMNS = ["lon", "lat", "year", "month", "day", "depth", "observation"]


def _start_job(session, criteria):
    resp = session.post(
        f"{API_BASE}/Download/GetStationData",
        json={"criteria": criteria, "emailAddress": None},
        timeout=60,
    )
    resp.raise_for_status()
    job_id = resp.json().get("id")
    if not job_id:
        raise RuntimeError(f"The ICES API did not return a job id: {resp.text}")
    return job_id


def _wait_for_job(session, job_id):
    """Poll until the job finishes. Returns True if it produced a file, and
    False if ICES found no data for the criteria (status "NotFound")."""
    deadline = time.monotonic() + TIMEOUT
    while time.monotonic() < deadline:
        resp = session.get(f"{API_BASE}/Download/GetStationDataStatus/{job_id}", timeout=60)
        resp.raise_for_status()
        body = resp.json()
        status = (body.get("status") or "").lower()
        if status == "completed":
            return True
        if status == "notfound":
            return False
        if status == "failed":
            raise RuntimeError(f"ICES export job {job_id} failed: {body.get('message', body)}")
        time.sleep(POLL_INTERVAL)
    raise RuntimeError(f"Timed out after {TIMEOUT}s waiting for ICES export job {job_id}")


def _read_export(zip_bytes):
    """The data csv from an ICES export zip, which also holds criteria and
    disclaimer files. The csv opens with a block of "//" comment lines."""
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        member = [x for x in zf.namelist() if x.lower().endswith(".csv")][0]
        lines = zf.read(member).decode("utf-8", errors="replace").splitlines()
    lines = [x for x in lines if not x.startswith("//")]
    if len(lines) == 0:
        return pd.DataFrame()
    return pd.read_csv(io.StringIO("\n".join(lines)), low_memory=False)


def _value_and_flag(raw, code):
    """Value column and its ODV quality flag column for an ICES parameter code.

    Headers look like "Temperature (TEMPPR01_UPAA) [degC]", with the flag in
    "QV:ODV:Temperature (TEMPPR01_UPAA) [degC]". The unit code after the
    parameter code can vary, so only the parameter code is matched.
    """
    matches = [x for x in raw.columns if f"({code}_" in x]
    values = [x for x in matches if not x.startswith("QV:")]
    if len(values) != 1:
        raise ValueError(f"Expected one ICES column for {code}, found {values}")
    value = values[0]
    flag = f"QV:ODV:{value}"
    if flag not in raw.columns:
        raise ValueError(f"No quality flag column found for {value}")
    return value, flag


def to_oceanval_format(raw, parameter_code):
    """Convert an ICES export to oceanval point columns, keeping only rows
    where both the observation and depth quality flags are 0 (good).

    Many ICES analytes are split across several method-specific parameter
    codes (filtered/unfiltered, autoanalyser/manual, ...), so a dataset can
    genuinely have no column for one particular code even though it has
    data for that analyte under a different one. That's treated as "no
    observations", not an error - unlike an entirely missing depth column,
    which would point to something actually wrong with the export.
    """
    if len(raw) == 0:
        return pd.DataFrame(columns=POINT_COLUMNS)

    if not any(f"({parameter_code}_" in x for x in raw.columns):
        return pd.DataFrame(columns=POINT_COLUMNS)

    value, value_flag = _value_and_flag(raw, parameter_code)
    depth, depth_flag = _value_and_flag(raw, DEPTH_CODE)

    df = raw.loc[(raw[value_flag] == 0) & (raw[depth_flag] == 0)]
    df = df.dropna(subset=[value, depth])
    # ICES exports mix timestamps with different UTC offsets (and some with
    # none at all) in the same file, which pandas otherwise refuses to
    # parse into one column.
    times = pd.to_datetime(df[TIME_COLUMN], format="ISO8601", utc=True)

    return pd.DataFrame(
        {
            "lon": df[LON_COLUMN].astype(float),
            "lat": df[LAT_COLUMN].astype(float),
            "year": times.dt.year,
            "month": times.dt.month,
            "day": times.dt.day,
            "depth": df[depth].astype(float),
            "observation": df[value].astype(float),
        }
    ).reset_index(drop=True)


def download_point_data(recipe, start_year, end_year, lon_lim, lat_lim):
    """Download an ICES recipe's observations for the given years and box.

    recipe is the dict stored by add_point_comparison, with the ICES
    "parameter" code and "dataset" code to request.
    """
    # the comparison's start/end can fall outside the simulation's years
    if start_year > end_year:
        return pd.DataFrame(columns=POINT_COLUMNS)
    criteria = {
        "dataset": recipe["dataset"],
        "dateFrom": f"{int(start_year)}-01-01",
        "dateTo": f"{int(end_year)}-12-31",
        "longitudeWest": float(lon_lim[0]),
        "longitudeEast": float(lon_lim[1]),
        "latitudeSouth": float(lat_lim[0]),
        "latitudeNorth": float(lat_lim[1]),
        "delimiter": ",",
        "useCompactFormat": False,
        "useISO8601": True,
        "includeOriginalVariables": False,
    }
    print(
        f"Downloading ICES {recipe['dataset']} data ({recipe['parameter']}) for "
        f"{int(start_year)}-{int(end_year)}, lon {lon_lim}, lat {lat_lim}"
    )
    with requests.Session() as session:
        job_id = _start_job(session, criteria)
        if not _wait_for_job(session, job_id):
            print("ICES has no data for these years and this area")
            return pd.DataFrame(columns=POINT_COLUMNS)
        resp = session.get(f"{API_BASE}/Download/GetStationDataFile/{job_id}", timeout=600)
        resp.raise_for_status()

    df = to_oceanval_format(_read_export(resp.content), recipe["parameter"])
    print(f"Downloaded {len(df)} ICES observations that passed quality control")
    return df
