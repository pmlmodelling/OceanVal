"""validate() and the report's temp file cleanup only remove what oceanval made."""

import os

import pytest

import oceanval


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


def test_notebook_temp_files_only_removes_oceanval_files(tmp_path, monkeypatch):
    stamp = "nctoolkit_someone_abcdnctoolkit_ecoval_output_"
    trackers = tmp_path / "notebooks" / ".trackers"
    trackers.mkdir(parents=True)
    # the notebooks name a tracker with the stamp, or with a .txt suffix
    (trackers / stamp).write_text("")
    (trackers / (stamp + ".txt")).write_text("")

    temp = tmp_path / "tmp"
    temp.mkdir()
    mine = temp / f"{stamp}tmpa1.nc"
    mine.write_text("")
    other_session = temp / "nctoolkit_someone_zzzznctoolkit_ecoval_output_tmpb2.nc"
    other_session.write_text("")
    not_oceanval = temp / f"{stamp[: -len('_ecoval_output_')]}tmpc3.nc"
    not_oceanval.write_text("")
    a_directory = temp / f"{stamp}tmpdir"
    a_directory.mkdir()

    real_glob = oceanval.glob.glob
    monkeypatch.setattr(
        oceanval.glob,
        "glob",
        lambda pattern, *a, **k: real_glob(
            str(temp) + pattern[len("/tmp") :] if pattern.startswith("/tmp/*") else pattern,
            *a,
            **k,
        ),
    )
    oceanval._remove_notebook_temp_files(str(tmp_path))

    assert not mine.exists()
    assert other_session.exists()
    assert not_oceanval.exists()
    assert a_directory.exists()
    assert os.path.exists(trackers / stamp)
