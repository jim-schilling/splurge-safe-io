import io
from pathlib import Path

import pytest

from splurge_safe_io.exceptions import (
    SplurgeSafeIoFileDecodingError,
    SplurgeSafeIoFileNotFoundError,
    SplurgeSafeIoFilePermissionError,
    SplurgeSafeIoOsError,
)
from splurge_safe_io.safe_text_file_reader import SafeTextFileReader


def test__read_unicode_decode_error_maps(tmp_path, monkeypatch):
    p = tmp_path / "bad.txt"

    # Create a fake open that returns bytes that will cause decode() to raise
    class FakeBytesIO(io.BytesIO):
        def read(self, *a, **k):
            return b"\xff\xff\xff"  # invalid for utf-8

    # Create the file so PathValidator passes
    p.write_bytes(b"")

    # Patch Path.open to return our FakeBytesIO for this path
    original_open = Path.open

    def fake_path_open(self, mode="rb", *a, **k):
        if self == p:
            return FakeBytesIO()
        return original_open(self, mode, *a, **k)

    monkeypatch.setattr(Path, "open", fake_path_open)

    with pytest.raises(SplurgeSafeIoFileDecodingError):
        SafeTextFileReader(p, encoding="utf-8").read()


def test__read_file_not_found_and_permission(monkeypatch):
    p = Path("/nonexistent/path.txt")
    # When path does not exist, PathValidator should raise SplurgeSafeIoFileNotFoundError
    with pytest.raises(SplurgeSafeIoFileNotFoundError):
        SafeTextFileReader(p)

    # For permission error mapping, create a real file then patch Path.open
    tmp = Path.cwd() / "tmp_perm_test.txt"
    try:
        tmp.write_bytes(b"ok")
        original_open = Path.open

        def fake_open_perm(self, mode="rb", *a, **k):
            if self == tmp:
                raise PermissionError("denied")
            return original_open(self, mode, *a, **k)

        monkeypatch.setattr(Path, "open", fake_open_perm)
        with pytest.raises(SplurgeSafeIoFilePermissionError):
            SafeTextFileReader(tmp).read()
    finally:
        try:
            tmp.unlink()
        except Exception:
            pass


def test__read_os_and_io_error_maps(monkeypatch):
    # Create a real file and patch Path.open to raise OSError/IOError for it
    real = Path.cwd() / "tmp_os_io_test.txt"
    try:
        real.write_bytes(b"ok")
        original_open = Path.open

        def fake_open_os(self, mode="rb", *a, **k):
            if self == real:
                raise OSError("osbad")
            return original_open(self, mode, *a, **k)

        monkeypatch.setattr(Path, "open", fake_open_os)
        with pytest.raises(SplurgeSafeIoOsError):
            SafeTextFileReader(real).read()

        def fake_open_io(self, mode="rb", *a, **k):
            if self == real:
                raise OSError("iobad")
            return original_open(self, mode, *a, **k)

        monkeypatch.setattr(Path, "open", fake_open_io)
        # IOError is an alias of OSError on modern Python; we map both to SplurgeSafeIoOsError
        with pytest.raises(SplurgeSafeIoOsError):
            SafeTextFileReader(real).read()
    finally:
        try:
            real.unlink()
        except Exception:
            pass


def test_read_as_stream_unicode_fallback(monkeypatch, tmp_path):
    # Force incremental decoder to raise UnicodeError in read_as_stream try block
    p = tmp_path / "badstream.txt"
    # Write a small file that's valid UTF-16LE without BOM and read with utf-16
    data = "a\nb\nc\n".encode("utf-16le")
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("wb") as f:
        f.write(data)

    # monkeypatch the codecs.getincrementaldecoder to return a decoder that raises
    class BadDecoder:
        def decode(self, b):
            raise UnicodeError("boom")

    monkeypatch.setattr("codecs.getincrementaldecoder", lambda enc: lambda: BadDecoder())

    reader = SafeTextFileReader(p, encoding="utf-16", chunk_size=2)
    collected = []
    for chunk in reader.readlines_as_stream():
        collected.extend(chunk)
    assert collected == ["a", "b", "c"]
