import pytest

from splurge_safe_io.safe_text_file_writer import SafeTextFileWriter, TextFileWriteMode, open_safe_text_writer


def test_write_and_readback(tmp_path):
    p = tmp_path / "out.txt"
    w = SafeTextFileWriter(p, file_write_mode=TextFileWriteMode.CREATE_OR_TRUNCATE)
    w.write("a\r\nb\n")
    w.flush()
    w.close()
    text = p.read_text()
    assert "\n" in text
    assert "\r" not in text


def test_writelines_and_context_manager(tmp_path):
    p = tmp_path / "out2.txt"
    with open_safe_text_writer(p) as buf:
        buf.write("x\r\ny\n")
    # file should now exist
    assert p.exists()
    assert p.read_text().count("\n") >= 1


def test_create_new_mode_raises_if_exists(tmp_path):
    p = tmp_path / "exists.txt"
    p.write_text("x")
    from splurge_safe_io.exceptions import SplurgeSafeIoFileAlreadyExistsError

    with pytest.raises(SplurgeSafeIoFileAlreadyExistsError):
        SafeTextFileWriter(p, file_write_mode=TextFileWriteMode.CREATE_NEW)
