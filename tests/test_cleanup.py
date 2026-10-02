"""validate() and the report's temp file cleanup only remove what oceanval made."""

import os

import pytest

import oceanval
from oceanval import leftovers


class _Stop(Exception):
    pass


def test_validate_clears_results_in_out_dir_not_cwd(tmp_path, monkeypatch):
    work = tmp_path / "work"
    out = tmp_path / "out"
    for directory in (work, out):
        (directory / "oceanval_results").mkdir(parents=True)
        (directory / "oceanval_results" / "keep.txt").write_text("x")
    monkeypatch.chdir(work)
    monkeypatch.setattr(oceanval, "_check_matchups", lambda data_dir: None)

    def stop(*args, **kwargs):
        raise _Stop

    # validate has cleared the previous results by the time it first copies a file
    monkeypatch.setattr(oceanval.shutil, "copyfile", stop)
    with pytest.raises(_Stop):
        oceanval.validate(
            data_dir=str(tmp_path), out_dir=str(out), subregions="global", test=True
        )

    assert not (out / "oceanval_results").exists()
    assert (work / "oceanval_results" / "keep.txt").exists()


# a stamp as the notebooks' kernels now make, and as older versions made it
STAMPS = [
    "nctoolkit_someone_abcdnctoolkit_oceanval_output_p999999_",
    "nctoolkit_someone_abcdnctoolkit_ecoval_output_",
]


@pytest.mark.parametrize("stamp", STAMPS)
def test_notebook_temp_files_only_removes_oceanval_files(tmp_path, monkeypatch, stamp):
    trackers = tmp_path / "notebooks" / ".trackers"
    trackers.mkdir(parents=True)
    # the notebooks name a tracker with the stamp, or with a .txt suffix
    (trackers / stamp).write_text("")
    (trackers / (stamp + ".txt")).write_text("")

    temp = tmp_path / "tmp"
    other_temp = tmp_path / "vartmp"
    temp.mkdir()
    other_temp.mkdir()
    mine = temp / f"{stamp}tmpa1.nc"
    mine.write_text("")
    # nctoolkit moves to a second temporary directory when the first is short of space
    moved = other_temp / f"{stamp}tmpa2.nc"
    moved.write_text("")
    other_session = temp / "nctoolkit_someone_zzzznctoolkit_oceanval_output_p999998_tmpb2.nc"
    other_session.write_text("")
    # the same session, but not named by nctoolkit in an oceanval session
    not_oceanval = temp / f"{stamp.split('_oceanval_output_')[0].split('_ecoval_output_')[0]}tmpc3.nc"
    not_oceanval.write_text("")
    a_directory = temp / f"{stamp}tmpdir"
    a_directory.mkdir()

    monkeypatch.setattr(leftovers, "TEMP_DIRS", (str(temp) + "/", str(other_temp) + "/"))
    oceanval._remove_notebook_temp_files(str(tmp_path))

    assert not mine.exists()
    assert not moved.exists()
    assert other_session.exists()
    assert not_oceanval.exists()
    assert a_directory.exists()
    assert os.path.exists(trackers / stamp)


def test_a_failed_build_still_removes_the_notebooks_temp_files(tmp_path, monkeypatch):
    stamp = STAMPS[0]
    trackers = tmp_path / "notebooks" / ".trackers"
    trackers.mkdir(parents=True)
    (trackers / stamp).write_text("")
    leftover = tmp_path / f"{stamp}tmpa1.nc"
    leftover.write_text("")
    monkeypatch.setattr(leftovers, "TEMP_DIRS", (str(tmp_path) + "/",))

    def fail(*args, **kwargs):
        raise _Stop

    monkeypatch.setattr(oceanval, "_build_book_pages", fail)
    with pytest.raises(_Stop):
        oceanval._build_book(str(tmp_path))

    assert not leftover.exists()


def test_the_stamp_names_oceanval_and_the_process():
    stamp = oceanval.nc.session_info["stamp"]

    assert stamp.endswith(f"_oceanval_output_p{os.getpid()}_")
    assert leftovers.is_oceanval_temp(f"/tmp/{stamp}tmpa1.nc")
    # files from before the name changed are still recognised
    assert leftovers.is_oceanval_temp("/tmp/nctoolkit_me_abcdnctoolkit_ecoval_output_tmpa1.nc")
    assert not leftovers.is_oceanval_temp("/tmp/nctoolkit_me_abcdnctoolkittmpa1.nc")
    assert not leftovers.is_oceanval_temp("/tmp/oceanval_output_tmpa1.nc")


def test_only_the_files_own_name_counts_not_its_directory():
    assert not leftovers.is_oceanval_temp("/tmp/nctoolkit_oceanval_output_x/data.nc")
    assert leftovers.is_oceanval_temp("/tmp/x/nctoolkit_me_abcdnctoolkit_oceanval_output_p1_tmp.nc")


def test_remove_leftovers_refuses_a_file_not_named_by_oceanval(tmp_path, monkeypatch):
    other = tmp_path / "precious.nc"
    other.write_text("")
    monkeypatch.setattr(
        leftovers,
        "find_leftovers",
        lambda: [{"path": str(other), "size": 0, "mtime": 0}],
    )

    result = leftovers.remove_leftovers([str(other)])

    assert other.exists()
    assert result == {"removed": 0, "freed_bytes": 0, "failed": [str(other)]}
