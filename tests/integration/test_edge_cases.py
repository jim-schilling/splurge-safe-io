import pathlib

import pytest

from splurge_safe_io.exceptions import (
    SplurgeSafeIoFileDecodingError,
    SplurgeSafeIoFileEncodingError,
    SplurgeSafeIoFilePermissionError,
    SplurgeSafeIoPathValidationError,
)
from splurge_safe_io.path_validator import PathValidator
from splurge_safe_io.safe_text_file_reader import SafeTextFileReader
from splurge_safe_io.safe_text_file_writer import SafeTextFileWriter

pytestmark = [pytest.mark.integration]


def test_allow_relative_false_raises(tmp_path):
    # Create a relative path string and ensure allow_relative=False rejects it
    rel = "somefile.txt"
    with pytest.raises(SplurgeSafeIoPathValidationError):
        PathValidator.get_validated_path(rel, allow_relative=False)


def test_must_be_readable_permission_error(mocker, tmp_path):
    f = tmp_path / "r.txt"
    f.write_text("ok")
    # Patch os.access to return False only for our test path
    real_access = __import__("os").access

    def access_stub(path, mode):
        try:
            pth = pathlib.Path(path)
        except Exception:
            pth = path
        if pth == f:
            return False
        return real_access(path, mode)

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(__import__("os"), "access", access_stub)
    try:
        with pytest.raises(SplurgeSafeIoFilePermissionError):
            PathValidator.get_validated_path(f, must_be_readable=True)
    finally:
        monkeypatch.undo()


def test_long_path_rejected():
    # Construct an overly long path string
    long_path = "a" * (PathValidator.MAX_PATH_LENGTH + 10)
    with pytest.raises(SplurgeSafeIoPathValidationError):
        PathValidator.get_validated_path(long_path)


@pytest.mark.serial
def test_path_resolve_outside_base_with_mock(mocker, tmp_path):
    base = tmp_path / "base"
    base.mkdir()
    p = tmp_path / "outside.txt"
    p.write_text("x")

    # Force Path.resolve to return a path outside base for this instance
    original_resolve = pathlib.Path.resolve

    def fake_resolve(self):
        if str(self) == str(p):
            return pathlib.Path(tmp_path / "not_in_base" / "file.txt")
        return original_resolve(self)

    mocker.patch.object(pathlib.Path, "resolve", fake_resolve)

    with pytest.raises(SplurgeSafeIoPathValidationError):
        PathValidator.get_validated_path(p, base_directory=base)


def test_reader_unicode_decode_error(tmp_path):
    p = tmp_path / "badutf8.bin"
    # invalid utf-8 sequence
    p.write_bytes(b"\xff\xff\xff")
    with pytest.raises(SplurgeSafeIoFileDecodingError):
        SafeTextFileReader(p).read()


def test_reader_chunk_boundary_multibyte(tmp_path):
    # Use a character that encodes to multiple bytes (e.g., 'ü') and small chunk size
    p = tmp_path / "mb.txt"
    text = "aü\nbü\ncü\n"
    p.write_text(text, encoding="utf-8")

    # chunk_size=1 forces the reader to process one byte at a time
    r = SafeTextFileReader(p, chunk_size=1)
    stream_lines = []
    for chunk in r.readlines_as_stream():
        stream_lines.extend(chunk)

    full_lines = SafeTextFileReader(p).read()
    assert stream_lines == full_lines.splitlines()


def test_reader_skip_footer_larger_than_file(tmp_path):
    p = tmp_path / "short.txt"
    p.write_text("onlyline")
    r = SafeTextFileReader(p, skip_footer_lines=10)
    out = []
    for c in r.readlines_as_stream():
        out.extend(c)
    assert out == []
    assert SafeTextFileReader(p, skip_footer_lines=10).read() == ""


def test_reader_empty_file(tmp_path):
    p = tmp_path / "empty.txt"
    p.write_text("")
    r = SafeTextFileReader(p)
    assert r.read() == ""
    out = []
    for c in r.readlines_as_stream():
        out.extend(c)
    assert out == []


@pytest.mark.serial
def test_writer_permission_error_on_open(mocker, tmp_path, permit_only_target_open):
    p = tmp_path / "out.txt"
    # Patch builtins.open to raise PermissionError when attempting to open only for this path
    permit_only_target_open(str(p), PermissionError("nope"))
    with pytest.raises(SplurgeSafeIoFilePermissionError):
        SafeTextFileWriter(p)


def test_writer_encoding_error_on_write(tmp_path):
    p = tmp_path / "out2.txt"
    w = SafeTextFileWriter(p)

    class BadFile:
        def write(self, _):
            # Construct UnicodeEncodeError with a str object for the object
            # argument to avoid TypeError from unittest.mock internals.
            raise UnicodeEncodeError("utf-8", "\ufffd", 0, 1, "reason")

    # Replace the internal file object with one that raises on write
    w._file_obj = BadFile()
    with pytest.raises(SplurgeSafeIoFileEncodingError):
        w.write("data")
