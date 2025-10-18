import os
from pathlib import Path

import pytest

from splurge_safe_io.exceptions import (
    SplurgeSafeIoFileNotFoundError,
    SplurgeSafeIoFileOperationError,
    SplurgeSafeIoFilePermissionError,
    SplurgeSafeIoOsError,
    SplurgeSafeIoParameterError,
    SplurgeSafeIoPathValidationError,
    SplurgeSafeIoUnknownError,
)
from splurge_safe_io.path_validator import PathValidator
from splurge_safe_io.safe_text_file_reader import SafeTextFileReader
from splurge_safe_io.safe_text_file_writer import SafeTextFileWriter

pytestmark = [pytest.mark.integration]


def test_validate_relative_disallowed():
    with pytest.raises(SplurgeSafeIoPathValidationError):
        PathValidator.get_validated_path("rel/path.txt", allow_relative=False)


def test_validate_base_directory_traversal(tmp_path):
    base = tmp_path / "base"
    base.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("x")
    with pytest.raises(SplurgeSafeIoPathValidationError):
        PathValidator.get_validated_path(outside, base_directory=base)


@pytest.mark.serial
def test_validate_resolve_oserror(monkeypatch, tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("x")

    def raise_os(self):
        raise OSError("boom")

    monkeypatch.setattr(Path, "resolve", raise_os)
    with pytest.raises(SplurgeSafeIoPathValidationError):
        PathValidator.get_validated_path(p)


def test_validate_must_exist_and_must_be_file(tmp_path):
    nonexist = tmp_path / "nope.txt"
    with pytest.raises(SplurgeSafeIoFileNotFoundError):
        PathValidator.get_validated_path(nonexist, must_exist=True)

    d = tmp_path / "adir"
    d.mkdir()
    with pytest.raises(SplurgeSafeIoPathValidationError):
        PathValidator.get_validated_path(d, must_be_file=True)


def test_validate_readable_writable_access(monkeypatch, tmp_path):
    f = tmp_path / "f.txt"
    f.write_text("ok")

    real_access = os.access

    def access_stub(path, mode):
        try:
            pth = Path(path)
        except Exception:
            pth = path
        if pth == f:
            return False
        return real_access(path, mode)

    monkeypatch.setattr(os, "access", access_stub)
    with pytest.raises(SplurgeSafeIoFilePermissionError):
        PathValidator.get_validated_path(f, must_be_readable=True)
    with pytest.raises(SplurgeSafeIoFilePermissionError):
        PathValidator.get_validated_path(f, must_be_writable=True)


@pytest.mark.parametrize(
    "exc, expected",
    [
        (FileNotFoundError("x"), SplurgeSafeIoFileNotFoundError),
        (PermissionError("x"), SplurgeSafeIoFilePermissionError),
        (OSError("x"), SplurgeSafeIoOsError),
        # IOError is an alias of OSError on modern Python; map to SplurgeSafeIoOsError
        (OSError("x"), SplurgeSafeIoOsError),
        (Exception("x"), SplurgeSafeIoUnknownError),
    ],
)
def test_reader_open_exception_mapping(monkeypatch, tmp_path, exc, expected):
    p = tmp_path / "r.txt"
    p.write_text("hello")
    rdr = SafeTextFileReader(p)

    def fake_open(*args, **kwargs):
        raise exc

    monkeypatch.setattr(Path, "open", fake_open)
    with pytest.raises(expected):
        rdr._read()


def test_writer_open_exception_mapping(monkeypatch, tmp_path, permit_only_target_open):
    # UnicodeEncodeError maps to SplurgeSafeIoFileEncodingError
    def fake_open_enc(*args, **kwargs):
        raise UnicodeEncodeError("ascii", "x", 0, 1, "reason")

    permit_only_target_open(str(tmp_path / "o.txt"), UnicodeEncodeError("ascii", "x", 0, 1, "reason"))
    from splurge_safe_io.exceptions import SplurgeSafeIoFileEncodingError

    with pytest.raises(SplurgeSafeIoFileEncodingError):
        SafeTextFileWriter(tmp_path / "o.txt")

    # IOError -> SplurgeSafeIoFileIoError
    def fake_open_io(*args, **kwargs):
        raise OSError("io")

    permit_only_target_open(str(tmp_path / "o2.txt"), OSError("io"))
    # In modern Python IOError is an alias of OSError and will be
    # handled by the OSError -> SplurgeSafeIoOsError mapping.
    with pytest.raises(SplurgeSafeIoOsError):
        SafeTextFileWriter(tmp_path / "o2.txt")

    # OSError on modern Python is caught as IOError; expect FileOperationError
    def fake_open_os(*args, **kwargs):
        raise OSError("os")

    permit_only_target_open(str(tmp_path / "o3.txt"), OSError("os"))
    with pytest.raises(SplurgeSafeIoFileOperationError):
        SafeTextFileWriter(tmp_path / "o3.txt")


def test_writer_write_flush_writelines_exceptions(monkeypatch, tmp_path):
    # Ensure builtins.open is left unmodified; monkeypatch restores automatically
    w = SafeTextFileWriter(tmp_path / "writeok.txt")

    # write parameter error when file_obj is None
    w._file_obj = None
    with pytest.raises(SplurgeSafeIoParameterError):
        w.write("x")

    # restore and set file_obj with fake methods
    w._file_obj = type("F", (), {})()

    def raise_io(*args, **kwargs):
        raise OSError("io")

    def raise_os(*args, **kwargs):
        raise OSError("os")

    # writelines -> IOError (alias to OSError) -> OsError
    w._file_obj.write = raise_io
    with pytest.raises(SplurgeSafeIoOsError):
        w.writelines(["a", "b"])

    # writelines -> UnicodeEncodeError
    def raise_enc(*args, **kwargs):
        raise UnicodeEncodeError("ascii", "x", 0, 1, "reason")

    w._file_obj.write = raise_enc
    from splurge_safe_io.exceptions import SplurgeSafeIoFileEncodingError

    with pytest.raises(SplurgeSafeIoFileEncodingError):
        w.writelines(["a"])  # should map to SplurgeSafeIoFileEncodingError

    # flush mapping
    w._file_obj.flush = raise_io
    # IOError/IOError alias -> OSError -> OsError
    with pytest.raises(SplurgeSafeIoOsError):
        w.flush()

    w._file_obj.flush = raise_os
    # OSError is caught by the OSError handler in flush(), so expect OsError
    with pytest.raises(SplurgeSafeIoOsError):
        w.flush()

    # provide a file_obj with a close() so close() is safe
    class Closeable:
        def close(self):
            return None

    w._file_obj = Closeable()
    # close no-op (should not raise)
    w.close()
    w.close()
