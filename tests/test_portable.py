"""Portable mode: a "tippy-data" folder next to the program keeps all of Tippy's files on the USB stick."""
from pathlib import Path

from backend import config


def test_a_tippy_data_folder_next_to_the_windows_program_is_used(tmp_path):
    exe = tmp_path / "Tippy" / "Tippy.exe"
    exe.parent.mkdir()
    assert config.portable_dir(exe, "win32") is None                       # no folder: the normal user folder
    (exe.parent / "tippy-data").mkdir()
    assert config.portable_dir(exe, "win32") == exe.parent / "tippy-data"


def test_on_a_mac_the_folder_sits_next_to_the_app(tmp_path):
    exe = tmp_path / "Tippy.app" / "Contents" / "MacOS" / "Tippy"
    exe.parent.mkdir(parents=True)
    (tmp_path / "tippy-data").mkdir()
    assert config.portable_dir(exe, "darwin") == tmp_path / "tippy-data"


def test_a_file_with_that_name_is_not_a_portable_folder(tmp_path):
    exe = tmp_path / "Tippy.exe"
    (tmp_path / "tippy-data").write_text("")
    assert config.portable_dir(Path(exe), "win32") is None
