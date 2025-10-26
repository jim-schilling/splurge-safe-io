from pathlib import Path

import pytest

from splurge_safe_io.exceptions import SplurgeSafeIoOSError, SplurgeSafeIoPathValidationError, SplurgeSafeIoValueError
from splurge_safe_io.path_validator import PathValidator
from splurge_safe_io.safe_text_file_reader import SafeTextFileReader
from splurge_safe_io.safe_text_file_writer import SafeTextFileWriter

pytestmark = [pytest.mark.integration]


@pytest.mark.serial
def test_reader_original_exception_on_oserror(monkeypatch, tmp_path):
    p = tmp_path / "x.txt"
    p.write_text("ok")

    def fake_open(self, mode="rb", *a, **k):
        raise OSError("boom")

    # Patch Path.open to simulate an OSError while reading; monkeypatch will
    # restore the original implementation at teardown. This patch is global
    # to the Path class but is safe because the test suite runs serially in
    # this environment.
    monkeypatch.setattr(Path, "open", fake_open)

    with pytest.raises(SplurgeSafeIoOSError) as excinfo:
        SafeTextFileReader(p).read()

    err = excinfo.value
    # __cause__ should be the original OSError and original_exception populated
    assert isinstance(err.__cause__, OSError)


def test_writer_original_exception_on_open(monkeypatch, tmp_path, permit_only_target_open):
    def fake_open(*a, **k):
        # UnicodeEncodeError expects a str object for the second parameter
        raise UnicodeEncodeError("ascii", "", 0, 1, "reason")

    # Use fixture to limit blast radius to the target path
    permit_only_target_open(str(tmp_path / "o.txt"), UnicodeEncodeError("ascii", "", 0, 1, "reason"))

    with pytest.raises(SplurgeSafeIoValueError) as excinfo:
        SafeTextFileWriter(tmp_path / "o.txt")

    err = excinfo.value
    assert isinstance(err.__cause__, UnicodeEncodeError)


@pytest.mark.serial
def test_path_validator_original_exception_on_resolve(monkeypatch, tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("x")

    def raise_os(self):
        raise OSError("boom")

    # Patch Path.resolve to simulate a resolve-time error (monkeypatch will restore)
    monkeypatch.setattr(Path, "resolve", raise_os)

    with pytest.raises(SplurgeSafeIoPathValidationError) as excinfo:
        PathValidator.get_validated_path(p)

    err = excinfo.value
    assert isinstance(err.__cause__, OSError)
