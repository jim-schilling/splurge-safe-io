from pathlib import Path

import pytest

from splurge_safe_io.exceptions import (
    SplurgeSafeIoFilePermissionError,
    SplurgeSafeIoOsError,
)
from splurge_safe_io.safe_text_file_writer import SafeTextFileWriter


def test_create_parents_false_raises_when_parent_missing(tmp_path):
    # target in a nested non-existent directory
    nested = tmp_path / "nonexistent" / "subdir" / "out.txt"
    # Ensure parent does not exist
    assert not nested.parent.exists()

    # Expect opening writer without create_parents to raise an OS error when opening
    with pytest.raises((SplurgeSafeIoOsError, SplurgeSafeIoFilePermissionError)):
        SafeTextFileWriter(nested, create_parents=False)


def test_create_parents_true_creates_and_writes(tmp_path):
    nested = tmp_path / "nonexistent" / "subdir" / "out.txt"
    assert not nested.parent.exists()

    writer = SafeTextFileWriter(nested, create_parents=True)
    try:
        writer.write("hello\nworld\n")
        writer.flush()
    finally:
        writer.close()

    assert nested.exists()
    content = nested.read_text(encoding=writer.encoding)
    assert "hello" in content


def test_create_parents_permission_error(monkeypatch, tmp_path):
    nested = tmp_path / "noaccess" / "out.txt"

    # Simulate PermissionError when mkdir is called
    original_mkdir = Path.mkdir

    def fake_mkdir(self, *args, **kwargs):
        raise PermissionError("simulated")

    monkeypatch.setattr(Path, "mkdir", fake_mkdir)

    with pytest.raises(SplurgeSafeIoFilePermissionError):
        SafeTextFileWriter(nested, create_parents=True)

    # Restore
    monkeypatch.setattr(Path, "mkdir", original_mkdir)
