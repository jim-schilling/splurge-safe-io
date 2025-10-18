import pytest

from splurge_safe_io.exceptions import SplurgeSafeIoFilePermissionError, SplurgeSafeIoOsError
from splurge_safe_io.safe_text_file_writer import open_safe_text_writer


def test_open_safe_text_writer_create_parents_true(tmp_path):
    nested = tmp_path / "nested" / "subdir" / "out.txt"
    assert not nested.parent.exists()

    with open_safe_text_writer(nested, create_parents=True) as buf:
        buf.write("hello\nworld\n")

    assert nested.exists()
    content = nested.read_text(encoding="utf-8")
    assert "hello" in content


def test_open_safe_text_writer_create_parents_false_raises(tmp_path):
    nested = tmp_path / "nested" / "subdir" / "out.txt"
    assert not nested.parent.exists()

    with pytest.raises((SplurgeSafeIoOsError, SplurgeSafeIoFilePermissionError)):
        with open_safe_text_writer(nested, create_parents=False) as buf:
            buf.write("x\n")
