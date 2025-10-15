import pytest

from splurge_safe_io.exceptions import (
    SplurgeSafeIoFileAlreadyExistsError,
    SplurgeSafeIoFileDecodingError,
    SplurgeSafeIoFileEncodingError,
    SplurgeSafeIoFilePermissionError,
    SplurgeSafeIoPathValidationError,
)
from splurge_safe_io.path_validator import PathValidator
from splurge_safe_io.safe_text_file_reader import (
    SafeTextFileReader,
    open_safe_text_reader,
)
from splurge_safe_io.safe_text_file_writer import (
    SafeTextFileWriter,
    TextFileWriteMode,
    open_safe_text_writer,
)

pytestmark = [pytest.mark.integration]


def test_pre_resolution_policy_registration_and_clear():
    # Register a policy that rejects any path containing 'forbidden'
    def reject_forbidden(p: str):
        if "forbidden" in p:
            raise SplurgeSafeIoPathValidationError("forbidden path")

    PathValidator.register_pre_resolution_policy(reject_forbidden)
    with pytest.raises(SplurgeSafeIoPathValidationError):
        PathValidator.validate_path("/tmp/this_is_forbidden.txt")

    # Ensure the policy is visible and then clear it
    policies = PathValidator.list_pre_resolution_policies()
    assert any(callable(p) for p in policies)
    PathValidator.clear_pre_resolution_policies()


def test_windows_drive_pattern_and_sanitize():
    assert PathValidator._is_valid_windows_drive_pattern("C:")
    assert PathValidator._is_valid_windows_drive_pattern("C:/")
    assert not PathValidator._is_valid_windows_drive_pattern("bad:foo")

    s = PathValidator.sanitize_filename("<bad>:name?*\x01")
    assert "_" in s or s != ""


def test_is_safe_path_false_for_control_chars():
    # Control character (U+0001) in path should be unsafe
    assert not PathValidator.is_safe_path("has\x01control")


def test_reader_decoding_error_and_preview(tmp_path):
    # Write bytes that are invalid under UTF-8 to trigger decode error
    p = tmp_path / "bad_utf8.bin"
    p.write_bytes(b"\xff\xff\xff")

    rdr = SafeTextFileReader(p, encoding="utf-8", strip=True)
    with pytest.raises(SplurgeSafeIoFileDecodingError):
        # read() attempts to decode and should raise
        rdr.read()

    # Create a valid file and test preview max_lines behavior
    p2 = tmp_path / "lines.txt"
    p2.write_text("one\ntwo\nthree\n")
    rdr2 = SafeTextFileReader(p2)
    assert rdr2.preview(0) == []


def test_read_skip_footer_and_stream_and_open_reader(tmp_path):
    p = tmp_path / "three.txt"
    p.write_text("a\nb\nc\n")
    # skip_footer_lines greater than file lines should return []
    rdr = SafeTextFileReader(p, skip_footer_lines=10)
    assert rdr.read() == ""

    # streaming (chunk_size 1) should yield same content as read when no footer
    rdr2 = SafeTextFileReader(p, chunk_size=1)
    streamed = []
    for chunk in rdr2.readlines_as_stream():
        streamed.extend(chunk)
    assert streamed == rdr2.readlines()

    # open_safe_text_reader context manager produces a StringIO with content
    with open_safe_text_reader(p) as sio:
        txt = sio.read()
    assert "a\nb\nc" in txt


def test_path_validator_dangerous_and_length_and_is_safe(tmp_path):
    # Dangerous character '<' should raise
    with pytest.raises(SplurgeSafeIoPathValidationError):
        PathValidator.validate_path("bad<name")

    # Colon in invalid position
    with pytest.raises(SplurgeSafeIoPathValidationError):
        PathValidator.validate_path("weird:path")

    # Excessive length
    long_path = "a" * (PathValidator.MAX_PATH_LENGTH + 1)
    with pytest.raises(SplurgeSafeIoPathValidationError):
        PathValidator.validate_path(long_path)

    # is_safe_path True for normal path
    p = tmp_path / "ok.txt"
    p.write_text("x")
    assert PathValidator.is_safe_path(p)


def test_reader_stream_footer_header_and_final_carry(tmp_path):
    # File whose last line has no newline (final carry)
    p = tmp_path / "carry.txt"
    p.write_text("1\n2\n3")
    rdr = SafeTextFileReader(p, chunk_size=2, skip_header_lines=1, skip_footer_lines=1)
    chunks = list(rdr.readlines_as_stream())
    # skip header (1) and footer (1) -> only middle '2' remains
    flat = [x for chunk in chunks for x in chunk]
    assert flat == ["2"]


def test_writer_append_and_normalization_and_open_writer_exception(tmp_path):
    p = tmp_path / "norm.txt"
    # write initial content
    w1 = SafeTextFileWriter(p, file_write_mode=TextFileWriteMode.CREATE_OR_TRUNCATE)
    w1.write("line1\r\nline2\rline3\n")
    w1.close()
    # append mode should add content
    w2 = SafeTextFileWriter(p, file_write_mode=TextFileWriteMode.CREATE_OR_APPEND)
    w2.write("more\n")
    w2.close()
    content = p.read_text()
    assert "line1" in content and "more" in content

    # open_safe_text_writer should not write on exception inside context
    out = tmp_path / "ctxfail.txt"
    try:
        with open_safe_text_writer(out) as buf:
            buf.write("x")
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    assert not out.exists()


def test_writer_create_new_and_permission_and_encode_and_writelines_none(
    tmp_path, permit_only_target_open, monkeypatch
):
    p = tmp_path / "out.txt"
    # create the file so CREATE_NEW fails
    p.write_text("exists")
    with pytest.raises(SplurgeSafeIoFileAlreadyExistsError):
        SafeTextFileWriter(p, file_write_mode=TextFileWriteMode.CREATE_NEW)

    # Permission error during open -> mapped exception (use fixture)
    permit_only_target_open(str(tmp_path / "willfail.txt"), PermissionError("nope"))
    with pytest.raises(SplurgeSafeIoFilePermissionError):
        SafeTextFileWriter(tmp_path / "willfail.txt")

    # Create a writer and simulate UnicodeEncodeError on write
    p2 = tmp_path / "write.txt"
    w = SafeTextFileWriter(p2)

    # Replace underlying file object's write to raise UnicodeEncodeError
    def raise_encode(*args, **kwargs):
        # UnicodeEncodeError expects the object argument to be a str
        raise UnicodeEncodeError("ascii", "x", 0, 1, "reason")

    w._file_obj.write = raise_encode
    with pytest.raises(SplurgeSafeIoFileEncodingError):
        w.write("some text")

    # writelines(None) should be a no-op and not raise
    assert w.writelines(None) is None
    w.close()

    # open_safe_text_writer should write content on successful exit
    out = tmp_path / "ctx.txt"
    with open_safe_text_writer(out) as buf:
        buf.write("line1\nline2\n")
    assert out.exists()
    assert out.read_text().count("line1") == 1


def test_writer_open_exception_mappings_explicit(monkeypatch, tmp_path, permit_only_target_open):
    # UnicodeEncodeError -> SplurgeSafeIoFileEncodingError
    def fake_open_enc(*args, **kwargs):
        raise UnicodeEncodeError("ascii", "x", 0, 1, "reason")

    # limit the simulated encoding error to the target path
    permit_only_target_open(str(tmp_path / "enc.txt"), UnicodeEncodeError("ascii", "x", 0, 1, "reason"))
    from splurge_safe_io.exceptions import SplurgeSafeIoFileEncodingError

    with pytest.raises(SplurgeSafeIoFileEncodingError):
        SafeTextFileWriter(tmp_path / "enc.txt")

    # PermissionError -> SplurgeSafeIoFilePermissionError
    def fake_open_perm(*args, **kwargs):
        raise PermissionError("no")

    permit_only_target_open(str(tmp_path / "perm.txt"), PermissionError("no"))
    from splurge_safe_io.exceptions import SplurgeSafeIoFilePermissionError

    with pytest.raises(SplurgeSafeIoFilePermissionError):
        SafeTextFileWriter(tmp_path / "perm.txt")


def test_writelines_encoding_mapping(monkeypatch, tmp_path):
    p = tmp_path / "writelines.txt"
    w = SafeTextFileWriter(p)

    # simulate UnicodeEncodeError on underlying write
    def raise_enc(*args, **kwargs):
        raise UnicodeEncodeError("ascii", "x", 0, 1, "reason")

    w._file_obj.write = raise_enc
    from splurge_safe_io.exceptions import SplurgeSafeIoFileEncodingError

    with pytest.raises(SplurgeSafeIoFileEncodingError):
        w.writelines(["a"])


def test_reader_stream_footer_and_byte_boundary(tmp_path):
    # Footer buffering: file with 6 lines, skip last 2
    p = tmp_path / "many.txt"
    p.write_text("\n".join(str(i) for i in range(6)) + "\n")
    # Streaming with chunk_size should yield lists of length <= chunk_size
    rdr = SafeTextFileReader(p, chunk_size=2, skip_footer_lines=1)
    chunks = list(rdr.readlines_as_stream())
    # Ensure chunks are lists and contain only strings from the source file
    assert all(isinstance(ch, list) for ch in chunks)
    flat = [x for ch in chunks for x in ch]
    assert all(isinstance(s, str) for s in flat)
    expected = [str(i) for i in range(6)]
    assert set(flat).issubset(set(expected))

    # Byte-boundary carry: include multibyte UTF-8 chars and small chunk_size
    p2 = tmp_path / "multi.txt"
    # '€' is 3 bytes in UTF-8, write explicit UTF-8 bytes to avoid platform-encoding differences
    p2.write_bytes("€\n€\n€\n".encode())
    rdr2 = SafeTextFileReader(p2, encoding="utf-8", chunk_size=2)
    # should not raise and should return 3 lines
    out_chunks = list(rdr2.readlines_as_stream())
    out = [x for chunk in out_chunks for x in chunk]
    assert len(out) == 3
    assert all(isinstance(s, str) for s in out)


def test_reader_newline_variants_and_long_line(tmp_path):
    # Create a file with many newline types and a very long line to force carry
    newlines = ["\r\n", "\r", "\n", "\x0b", "\x0c", "\x1c", "\x1d", "\x1e", "\x85", "\u2028", "\u2029"]
    parts = [f"L{i}" for i in range(len(newlines))]
    content = "".join(p + nl for p, nl in zip(parts, newlines, strict=False)) + "ENDLINE"
    # add a very long line without newline to force carry
    content = "A" * 200 + "\n" + content
    p = tmp_path / "varnl.txt"
    p.write_bytes(content.encode("utf-8"))

    rdr = SafeTextFileReader(p, chunk_size=16, strip=False)
    flat = [x for ch in rdr.readlines_as_stream() for x in ch]
    # compare to full readlines() semantics
    full = rdr.readlines()
    assert flat == full


def test_read_as_stream_fallback_decoder(monkeypatch, tmp_path):
    # Force the incremental decoder to raise UnicodeError so read_as_stream falls back to self.read()
    p = tmp_path / "fb.txt"
    p.write_text("one\ntwo\nthree\n")

    class BadDecoder:
        def __init__(self, *args, **kwargs):
            pass

        def decode(self, *args, **kwargs):
            raise UnicodeError("boom")

    import codecs

    monkeypatch.setattr(codecs, "getincrementaldecoder", lambda enc: (lambda: BadDecoder()))
    rdr = SafeTextFileReader(p, chunk_size=1)
    # Should not raise and should yield same lines as readlines()
    streamed = [x for ch in rdr.readlines_as_stream() for x in ch]
    assert streamed == rdr.readlines()
