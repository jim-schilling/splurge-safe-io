import builtins
import io
import pathlib

import pytest

from splurge_safe_io.exceptions import (
    SplurgeSafeIoError,
    SplurgeSafeIoFileExistsError,
    SplurgeSafeIoOSError,
    SplurgeSafeIoPermissionError,
    SplurgeSafeIoUnicodeError,
)
from splurge_safe_io.safe_text_file_writer import SafeTextFileWriter, TextFileWriteMode, open_safe_text_writer

pytestmark = [pytest.mark.integration]


class FakeFile(io.StringIO):
    def __init__(self, raise_on_write=None, raise_on_flush=None):
        super().__init__()
        self._raise_on_write = raise_on_write
        self._raise_on_flush = raise_on_flush

    def write(self, s):
        if self._raise_on_write:
            raise self._raise_on_write
        return super().write(s)

    def flush(self):
        if self._raise_on_flush:
            raise self._raise_on_flush
        return super().flush()


@pytest.mark.serial
def test_open_file_exists_raises(tmp_path, permit_only_target_open):
    # Simulate open() raising FileExistsError for CREATE_NEW mode.
    #
    # This test intentionally monkeypatches the global ``builtins.open`` to
    # simulate platform-level failures. We keep the fake call-aware so it
    # only affects the intended target path. Tests that replace global
    # builtins should be run serially or rely on monkeypatch to restore
    # state; our CI runs tests serially by default in this branch.
    target = tmp_path / "exists.txt"

    # Use test fixture to simulate open() raising FileExistsError only for target
    permit_only_target_open(str(target), FileExistsError("exists"))

    with pytest.raises(SplurgeSafeIoFileExistsError):
        SafeTextFileWriter(target, file_write_mode=TextFileWriteMode.CREATE_NEW)


@pytest.mark.serial
def test_open_permission_error_maps(tmp_path, permit_only_target_open):
    target = tmp_path / "perm.txt"
    permit_only_target_open(str(target), PermissionError("nope"))

    with pytest.raises(SplurgeSafeIoPermissionError):
        SafeTextFileWriter(target)


@pytest.mark.serial
def test_open_unicode_encode_error_maps(tmp_path, permit_only_target_open):
    target = tmp_path / "enc.txt"
    permit_only_target_open(str(target), UnicodeEncodeError("utf-8", "", 0, 1, "reason"))

    with pytest.raises(SplurgeSafeIoUnicodeError):
        SafeTextFileWriter(target)


def test_write_raises_mapped_exceptions(tmp_path, monkeypatch):
    # Provide a writer whose write() will raise various exceptions and ensure
    # they are mapped correctly by SafeTextFileWriter.write()
    target = tmp_path / "out.txt"

    # Case: UnicodeEncodeError
    f = FakeFile(raise_on_write=UnicodeEncodeError("utf-8", "", 0, 1, "reason"))
    real_open = builtins.open

    def open_factory(name, *a, **k):
        try:
            name_str = str(pathlib.Path(name))
        except Exception:
            name_str = str(name)
        if name_str == str(target):
            return f
        return real_open(name, *a, **k)

    monkeypatch.setattr(builtins, "open", open_factory)
    w = SafeTextFileWriter(target)
    with pytest.raises(SplurgeSafeIoUnicodeError):
        w.write("abc")

    # Case: IOError (aliasing to OSError on modern Python) -> OsError
    f = FakeFile(raise_on_write=OSError("ioerr"))
    real_open = builtins.open

    def open_factory(name, *a, **k):
        try:
            name_str = str(pathlib.Path(name))
        except Exception:
            name_str = str(name)
        if name_str == str(target):
            return f
        return real_open(name, *a, **k)

    monkeypatch.setattr(builtins, "open", open_factory)
    w = SafeTextFileWriter(target)
    with pytest.raises(SplurgeSafeIoOSError):
        w.write("abc")

    # Case: OSError -> map to SplurgeSafeIoOSError (canonical mapping)
    f = FakeFile(raise_on_write=OSError("oserr"))
    real_open = builtins.open

    def open_factory(name, *a, **k):
        try:
            name_str = str(pathlib.Path(name))
        except Exception:
            name_str = str(name)
        if name_str == str(target):
            return f
        return real_open(name, *a, **k)

    monkeypatch.setattr(builtins, "open", open_factory)
    w = SafeTextFileWriter(target)
    with pytest.raises(SplurgeSafeIoOSError):
        w.write("abc")

    # Case: Generic Exception -> SplurgeSafeIoError
    f = FakeFile(raise_on_write=Exception("boom"))
    real_open = builtins.open

    def open_factory(name, *a, **k):
        try:
            name_str = str(pathlib.Path(name))
        except Exception:
            name_str = str(name)
        if name_str == str(target):
            return f
        return real_open(name, *a, **k)

    monkeypatch.setattr(builtins, "open", open_factory)
    w = SafeTextFileWriter(target)
    with pytest.raises(SplurgeSafeIoError):
        w.write("abc")


def test_flush_raises_mapped_exceptions(tmp_path, monkeypatch):
    target = tmp_path / "out2.txt"

    # Case: IOError -> OsError (aliasing to OSError on modern Python)
    f = FakeFile(raise_on_flush=OSError("ioerr"))
    real_open = builtins.open

    def open_factory2(name, *a, **k):
        try:
            name_str = str(pathlib.Path(name))
        except Exception:
            name_str = str(name)
        if name_str == str(target):
            return f
        return real_open(name, *a, **k)

    monkeypatch.setattr(builtins, "open", open_factory2)
    w = SafeTextFileWriter(target)
    with pytest.raises(SplurgeSafeIoOSError):
        w.flush()

    # Case: OSError -> map to SplurgeSafeIoOSError (canonical mapping)
    f = FakeFile(raise_on_flush=OSError("oserr"))
    real_open = builtins.open

    def open_factory3(name, *a, **k):
        try:
            name_str = str(pathlib.Path(name))
        except Exception:
            name_str = str(name)
        if name_str == str(target):
            return f
        return real_open(name, *a, **k)

    monkeypatch.setattr(builtins, "open", open_factory3)
    w = SafeTextFileWriter(target)
    with pytest.raises(SplurgeSafeIoOSError):
        w.flush()

    # Case: Generic Exception
    f = FakeFile(raise_on_flush=Exception("boom"))
    real_open = builtins.open

    def open_factory4(name, *a, **k):
        try:
            name_str = str(pathlib.Path(name))
        except Exception:
            name_str = str(name)
        if name_str == str(target):
            return f
        return real_open(name, *a, **k)

    monkeypatch.setattr(builtins, "open", open_factory4)
    w = SafeTextFileWriter(target)
    with pytest.raises(SplurgeSafeIoError):
        w.flush()


def test_open_safe_text_writer_context_writes_on_success(tmp_path):
    target = tmp_path / "ctx.txt"
    with open_safe_text_writer(target, encoding="utf-8") as buf:
        buf.write("one\r\ntwo\rthree\n")
    # Ensure file written and normalized to LF
    with target.open("r", encoding="utf-8") as f:
        content = f.read()
    assert content == "one\ntwo\rthree\n".replace("\r\n", "\n").replace("\r", "\n")
