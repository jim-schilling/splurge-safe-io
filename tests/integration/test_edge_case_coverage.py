import codecs
import pathlib
from pathlib import Path
from types import SimpleNamespace

import pytest

from splurge_safe_io.exceptions import (
    SplurgeSafeIoFileAlreadyExistsError,
    SplurgeSafeIoFileEncodingError,
    SplurgeSafeIoFilePermissionError,
    SplurgeSafeIoOsError,
    SplurgeSafeIoPathValidationError,
)
from splurge_safe_io.path_validator import PathValidator
from splurge_safe_io.safe_text_file_reader import SafeTextFileReader
from splurge_safe_io.safe_text_file_writer import SafeTextFileWriter, TextFileWriteMode

pytestmark = [pytest.mark.integration]


@pytest.mark.serial
def test_validate_path_resolve_failure(monkeypatch, tmp_path: Path):
    # Simulate Path.resolve raising OSError.
    #
    # We patch Path.resolve to force the resolve-time error branch. This
    # is a global patch but is restored automatically by the pytest
    # ``monkeypatch`` fixture at teardown; keep these tests serial if
    # running under parallel test runners.
    def _bad_resolve(self, *args, **kwargs):
        raise OSError("boom")

    # Patch Path.resolve to simulate a resolve-time error (monkeypatch will restore)
    monkeypatch.setattr(pathlib.Path, "resolve", _bad_resolve)
    with pytest.raises(SplurgeSafeIoPathValidationError) as excinfo:
        PathValidator.validate_path(tmp_path / "x", must_exist=False)
    assert isinstance(excinfo.value.original_exception, OSError)


def test_validate_dangerous_character_and_length():
    # Dangerous character
    with pytest.raises(SplurgeSafeIoPathValidationError):
        PathValidator.validate_path("bad|name")

    # Control character
    with pytest.raises(SplurgeSafeIoPathValidationError):
        PathValidator.validate_path("bad\x01name")

    # Colon in wrong place
    with pytest.raises(SplurgeSafeIoPathValidationError):
        PathValidator.validate_path("notadrive:foo")

    # Too long
    long_path = "a" * (PathValidator.MAX_PATH_LENGTH + 1)
    with pytest.raises(SplurgeSafeIoPathValidationError):
        PathValidator.validate_path(long_path)


def test_reader_incremental_decoder_fallback(monkeypatch, tmp_path: Path):
    # Create a small file
    fpath = tmp_path / "u16be.txt"
    # write some bytes that the incremental decoder will reject (simulate)
    fpath.write_bytes(b"abc")

    class BadDecoder:
        def decode(self, b, final=False):
            raise UnicodeError("fail")

    # Make getincrementaldecoder return a factory that produces BadDecoder
    monkeypatch.setattr(codecs, "getincrementaldecoder", lambda enc: (lambda: BadDecoder()))

    reader = SafeTextFileReader(fpath, encoding="utf-8")
    # The fallback yields chunks produced by read(); ensure it yields at least once
    chunks = list(reader.read_as_stream())
    assert any(isinstance(c, list) for c in chunks)


def test_reader_footer_header_finalization(tmp_path: Path):
    # Create file with 3 lines and set skip_footer_lines to 5 (> lines)
    fpath = tmp_path / "few.txt"
    fpath.write_text("L1\nL2\nL3\n", encoding="utf-8")

    r = SafeTextFileReader(fpath, skip_header_lines=1, skip_footer_lines=5, chunk_size=2)
    # All lines become part of footer or skipped, so read() should return []
    assert r.read() == []

    # Test partial final carry (no trailing newline)
    fpath2 = tmp_path / "no_nl.txt"
    fpath2.write_text("one\npartial", encoding="utf-8")
    r2 = SafeTextFileReader(fpath2, strip=False, chunk_size=10)
    all_lines = []
    for chunk in r2.read_as_stream():
        all_lines.extend(chunk)
    # Expect two lines: 'one' and 'partial'
    assert any("partial" in ln for ln in all_lines)


def test_writer_create_new_file_exists(tmp_path: Path):
    dest = tmp_path / "exists.txt"
    dest.write_text("x")
    with pytest.raises(SplurgeSafeIoFileAlreadyExistsError):
        SafeTextFileWriter(dest, file_write_mode=TextFileWriteMode.CREATE_NEW)


def test_writer_write_unicode_and_os_errors(monkeypatch, tmp_path: Path):
    dest = tmp_path / "w.txt"
    w = SafeTextFileWriter(dest)

    # Simulate underlying write raising UnicodeEncodeError
    def raise_unicode(*args, **kwargs):
        raise UnicodeEncodeError("ascii", "", 0, 1, "reason")

    monkeypatch.setattr(w, "_file_obj", SimpleNamespace(write=raise_unicode, flush=lambda: None, close=lambda: None))
    with pytest.raises(SplurgeSafeIoFileEncodingError) as excinfo:
        w.write("é")
    assert isinstance(excinfo.value.original_exception, UnicodeEncodeError)

    # Simulate underlying write raising OSError
    def raise_os(*args, **kwargs):
        raise OSError("boom")

    monkeypatch.setattr(w, "_file_obj", SimpleNamespace(write=raise_os, flush=lambda: None, close=lambda: None))
    with pytest.raises(SplurgeSafeIoOsError) as excinfo2:
        w.write("ok")
    assert isinstance(excinfo2.value.original_exception, OSError)


def test_writer_writelines_and_flush_errors(monkeypatch, tmp_path: Path):
    dest = tmp_path / "wl.txt"
    w = SafeTextFileWriter(dest)

    # writelines -> UnicodeEncodeError
    def raise_unicode(*args, **kwargs):
        raise UnicodeEncodeError("ascii", "", 0, 1, "reason")

    monkeypatch.setattr(
        w, "_file_obj", SimpleNamespace(write=lambda s: raise_unicode(), flush=lambda: None, close=lambda: None)
    )
    with pytest.raises(SplurgeSafeIoFileEncodingError):
        w.writelines(["a", "b"])  # pragma: no cover - behavior branch

    # flush -> OSError
    monkeypatch.setattr(
        w,
        "_file_obj",
        SimpleNamespace(write=lambda s: None, flush=lambda: (_ for _ in ()).throw(OSError("boom")), close=lambda: None),
    )
    with pytest.raises(SplurgeSafeIoOsError):
        w.flush()


def test_original_exception_propagation(tmp_path: Path, monkeypatch, permit_only_target_open):
    # Ensure original_exception appears on path validator error
    original_resolve = pathlib.Path.resolve

    def _bad_resolve(self, *a, **kw):
        raise OSError("boom2")

    monkeypatch.setattr(pathlib.Path, "resolve", _bad_resolve)
    with pytest.raises(SplurgeSafeIoPathValidationError) as ei:
        PathValidator.validate_path(tmp_path / "x")
    assert isinstance(ei.value.original_exception, OSError)

    # Restore resolve so subsequent operations are normal
    monkeypatch.setattr(pathlib.Path, "resolve", original_resolve)

    # Ensure writer open-time original_exception for permission
    # Simulate permission by using the permit_only_target_open fixture via monkeypatch
    # This will raise PermissionError only for the target path
    permit_target = str(tmp_path / "a.txt")
    permit_only_target_open(permit_target, PermissionError("nope"))
    with pytest.raises(SplurgeSafeIoFilePermissionError) as e2:
        SafeTextFileWriter(tmp_path / "a.txt")
    assert isinstance(e2.value.original_exception, PermissionError)
