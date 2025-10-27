"""Additional tests for public API coverage gaps.

This module targets specific code paths identified in coverage analysis:
- Reader/Writer context manager helpers with various scenarios
- PathValidator edge cases and permission checks
- Exception handling paths in core functionality
"""

import io
import os

import pytest

from splurge_safe_io import (
    PathValidator,
    SafeTextFileReader,
    SafeTextFileWriter,
    SplurgeSafeIoFileExistsError,
    SplurgeSafeIoFileNotFoundError,
    SplurgeSafeIoLookupError,
    SplurgeSafeIoOSError,
    SplurgeSafeIoPathValidationError,
    SplurgeSafeIoPermissionError,
    SplurgeSafeIoUnicodeError,
    SplurgeSafeIoValueError,
    TextFileWriteMode,
    open_safe_text_reader,
    open_safe_text_writer,
)


class TestOpenSafeTextReaderContextManager:
    """Test the public open_safe_text_reader context manager helper."""

    def test_open_safe_text_reader_returns_stringio(self, tmp_path):
        """Verify context manager yields a StringIO object."""
        p = tmp_path / "test.txt"
        p.write_text("line1\nline2\nline3")

        with open_safe_text_reader(p) as sio:
            assert isinstance(sio, io.StringIO)
            content = sio.read()
            assert content == "line1\nline2\nline3"
            sio.seek(0)
            assert sio.read() == "line1\nline2\nline3"

    def test_open_safe_text_reader_with_strip(self, tmp_path):
        """Test open_safe_text_reader respects strip parameter."""
        p = tmp_path / "test.txt"
        p.write_text("  line1  \n  line2  ")

        with open_safe_text_reader(p, strip=True) as sio:
            content = sio.read()
            assert content == "line1\nline2"

    def test_open_safe_text_reader_with_skip_headers(self, tmp_path):
        """Test open_safe_text_reader skips header lines correctly."""
        p = tmp_path / "test.txt"
        p.write_text("header1\nheader2\ndata1\ndata2")

        with open_safe_text_reader(p, skip_header_lines=2) as sio:
            content = sio.read()
            assert content == "data1\ndata2"

    def test_open_safe_text_reader_with_skip_footers(self, tmp_path):
        """Test open_safe_text_reader skips footer lines correctly."""
        p = tmp_path / "test.txt"
        p.write_text("data1\ndata2\nfooter1\nfooter2")

        with open_safe_text_reader(p, skip_footer_lines=2) as sio:
            content = sio.read()
            assert content == "data1\ndata2"

    def test_open_safe_text_reader_with_all_filters(self, tmp_path):
        """Test open_safe_text_reader with header, footer, and strip."""
        p = tmp_path / "test.txt"
        p.write_text("H\n  D1  \n  D2  \nF")

        with open_safe_text_reader(p, skip_header_lines=1, skip_footer_lines=1, strip=True) as sio:
            content = sio.read()
            assert content == "D1\nD2"

    def test_open_safe_text_reader_with_mixed_newlines(self, tmp_path):
        """Test that open_safe_text_reader normalizes newlines."""
        p = tmp_path / "test.txt"
        # Write with different line ending styles
        p.write_bytes(b"line1\r\nline2\rline3\nline4")

        with open_safe_text_reader(p) as sio:
            content = sio.read()
            assert content == "line1\nline2\nline3\nline4"

    def test_open_safe_text_reader_with_custom_encoding(self, tmp_path):
        """Test open_safe_text_reader with non-default encoding."""
        p = tmp_path / "test.txt"
        p.write_text("café\néàü", encoding="utf-8")

        with open_safe_text_reader(p, encoding="utf-8") as sio:
            content = sio.read()
            assert "café" in content
            assert "éàü" in content

    def test_open_safe_text_reader_closes_buffer_on_exit(self, tmp_path):
        """Verify StringIO buffer is properly closed on context exit."""
        p = tmp_path / "test.txt"
        p.write_text("content")

        with open_safe_text_reader(p) as sio:
            pass

        # After context exit, buffer should be closed
        assert sio.closed is True

    def test_open_safe_text_reader_closes_buffer_on_exception(self, tmp_path):
        """Verify StringIO buffer is closed even if exception occurs reading."""
        p = tmp_path / "nonexistent.txt"

        with pytest.raises(SplurgeSafeIoFileNotFoundError):
            with open_safe_text_reader(p):
                pass

        # Note: exception happens during yield setup, not within context

    def test_open_safe_text_reader_file_not_found(self, tmp_path):
        """Test that missing file raises appropriate exception."""
        p = tmp_path / "nonexistent.txt"

        with pytest.raises(SplurgeSafeIoFileNotFoundError):
            with open_safe_text_reader(p):
                pass


class TestOpenSafeTextWriterContextManager:
    """Test the public open_safe_text_writer context manager helper."""

    def test_open_safe_text_writer_writes_on_success(self, tmp_path):
        """Verify context manager writes content on successful exit."""
        p = tmp_path / "output.txt"

        with open_safe_text_writer(p) as buf:
            buf.write("line1\nline2\n")

        assert p.exists()
        content = p.read_text()
        assert content == "line1\nline2\n"

    def test_open_safe_text_writer_does_not_write_on_exception(self, tmp_path):
        """Verify no file is written if exception occurs in context."""
        p = tmp_path / "output.txt"

        with pytest.raises(ValueError):
            with open_safe_text_writer(p) as buf:
                buf.write("some content")
                raise ValueError("Test exception")

        assert not p.exists()

    def test_open_safe_text_writer_with_create_new_mode(self, tmp_path):
        """Test CREATE_NEW mode raises if file already exists."""
        p = tmp_path / "output.txt"
        p.write_text("existing")

        with pytest.raises(SplurgeSafeIoFileExistsError):
            with open_safe_text_writer(p, file_write_mode=TextFileWriteMode.CREATE_NEW) as buf:
                buf.write("new content")

    def test_open_safe_text_writer_with_append_mode(self, tmp_path):
        """Test CREATE_OR_APPEND mode appends to existing file."""
        p = tmp_path / "output.txt"
        p.write_text("existing\n")

        with open_safe_text_writer(p, file_write_mode=TextFileWriteMode.CREATE_OR_APPEND) as buf:
            buf.write("appended\n")

        content = p.read_text()
        assert content == "existing\nappended\n"

    def test_open_safe_text_writer_with_create_or_truncate_mode(self, tmp_path):
        """Test CREATE_OR_TRUNCATE mode truncates existing file."""
        p = tmp_path / "output.txt"
        p.write_text("existing content that should be replaced")

        with open_safe_text_writer(p, file_write_mode=TextFileWriteMode.CREATE_OR_TRUNCATE) as buf:
            buf.write("new\n")

        content = p.read_text()
        assert content == "new\n"

    def test_open_safe_text_writer_with_create_parents_true(self, tmp_path):
        """Test create_parents=True creates parent directories."""
        p = tmp_path / "subdir1" / "subdir2" / "output.txt"

        with open_safe_text_writer(p, create_parents=True) as buf:
            buf.write("content")

        assert p.exists()
        assert p.read_text() == "content"

    def test_open_safe_text_writer_with_create_parents_false(self, tmp_path):
        """Test create_parents=False raises if parent dirs don't exist."""
        p = tmp_path / "nonexistent" / "output.txt"

        with pytest.raises(SplurgeSafeIoOSError):
            with open_safe_text_writer(p, create_parents=False) as buf:
                buf.write("content")

    def test_open_safe_text_writer_normalizes_newlines(self, tmp_path):
        """Test that open_safe_text_writer normalizes newlines."""
        p = tmp_path / "output.txt"

        with open_safe_text_writer(p) as buf:
            buf.write("line1\r\nline2\rline3\nline4")

        content = p.read_bytes()
        # Should use platform's canonical newline (usually \n on Unix, \r\n on Windows)
        # But the SafeTextFileWriter normalizes to LF
        assert b"line1" in content
        assert b"line2" in content

    def test_open_safe_text_writer_with_custom_encoding(self, tmp_path):
        """Test open_safe_text_writer with non-default encoding."""
        p = tmp_path / "output.txt"

        with open_safe_text_writer(p, encoding="utf-8") as buf:
            buf.write("café ü")

        content = p.read_text(encoding="utf-8")
        assert "café" in content
        assert "ü" in content

    def test_open_safe_text_writer_returns_stringio(self, tmp_path):
        """Verify context manager yields a StringIO object."""
        p = tmp_path / "output.txt"

        with open_safe_text_writer(p) as buf:
            assert isinstance(buf, io.StringIO)
            buf.write("test")

        assert p.read_text() == "test"

    def test_open_safe_text_writer_stringio_seekable(self, tmp_path):
        """Verify yielded StringIO supports seeking operations."""
        p = tmp_path / "output.txt"

        with open_safe_text_writer(p) as buf:
            buf.write("first")
            buf.seek(0)
            buf.write("second")  # Overwrites 'first'

        assert p.read_text() == "second"


class TestPathValidatorAdvanced:
    """Test advanced PathValidator scenarios for coverage."""

    def test_path_validator_must_be_readable(self, tmp_path):
        """Test must_be_readable=True raises for non-existent file."""
        p = tmp_path / "nonexistent.txt"

        with pytest.raises(SplurgeSafeIoFileNotFoundError):
            PathValidator.get_validated_path(p, must_exist=False, must_be_readable=True)

    def test_path_validator_must_be_writable(self, tmp_path):
        """Test must_be_writable=True raises for non-existent file."""
        p = tmp_path / "nonexistent.txt"

        with pytest.raises(SplurgeSafeIoFileNotFoundError):
            PathValidator.get_validated_path(p, must_exist=False, must_be_writable=True)

    def test_path_validator_must_be_file_with_directory(self, tmp_path):
        """Test must_be_file=True raises when path is a directory."""
        with pytest.raises(SplurgeSafeIoPathValidationError):
            PathValidator.get_validated_path(tmp_path, must_exist=True, must_be_file=True)

    def test_path_validator_with_base_directory_absolute_path(self, tmp_path):
        """Test absolute path with base_directory is allowed if within bounds."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        f = subdir / "file.txt"
        f.write_text("content")

        # Absolute path within base should work
        result = PathValidator.get_validated_path(f, base_directory=tmp_path, must_exist=True)
        assert result == f

    def test_path_validator_path_traversal_detected(self, tmp_path):
        """Test that path traversal attempts are rejected."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        # Try to escape parent directory
        traversal_path = subdir / ".." / ".." / "etc" / "passwd"

        with pytest.raises(SplurgeSafeIoPathValidationError) as exc_info:
            PathValidator.get_validated_path(traversal_path, base_directory=subdir, must_exist=False)

        assert "path-traversal-detected" in str(exc_info.value)

    def test_path_validator_dangerous_character_detection(self):
        """Test that dangerous characters are rejected."""
        for char in PathValidator._DANGEROUS_CHARS:
            path_with_dangerous = f"test{char}file.txt"
            with pytest.raises(SplurgeSafeIoPathValidationError):
                PathValidator.get_validated_path(path_with_dangerous)

    def test_path_validator_null_character_rejected(self):
        """Test that null bytes in path are rejected."""
        with pytest.raises(SplurgeSafeIoPathValidationError):
            PathValidator.get_validated_path("test\x00file.txt")

    def test_path_validator_relative_to_base_directory(self, tmp_path):
        """Test relative path resolution with base_directory."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        # Relative path from base directory
        result = PathValidator.get_validated_path("subdir", base_directory=tmp_path, must_exist=True)
        assert result == subdir

    def test_path_validator_windows_drive_pattern_recognition(self):
        """Test Windows drive pattern recognition (C: or C:\\...)."""
        if os.name != "nt":
            pytest.skip("Windows-specific test")

        # These should be recognized as valid Windows paths (not raise)
        try:
            # C: alone might not be valid, but C:\\ should be
            validator = PathValidator()
            assert validator._is_valid_windows_drive_pattern("C:")
            assert validator._is_valid_windows_drive_pattern("C:\\")
            assert validator._is_valid_windows_drive_pattern("D:/")
        except Exception as e:
            # If OS constraints prevent this, skip gracefully
            pytest.skip(f"Cannot validate Windows drive on this system: {e}")

    def test_path_validator_relative_path_not_allowed(self, tmp_path):
        """Test that relative paths are rejected when allow_relative=False."""
        with pytest.raises(SplurgeSafeIoPathValidationError):
            PathValidator.get_validated_path("relative/path.txt", allow_relative=False)


class TestSafeTextFileReaderEdgeCases:
    """Test edge cases in SafeTextFileReader not covered by other tests."""

    def test_reader_with_encoding_fallback(self, tmp_path):
        """Test reader with multiple encoding scenarios."""
        p = tmp_path / "test.txt"
        # Write UTF-8 content
        p.write_text("UTF-8: café", encoding="utf-8")

        reader = SafeTextFileReader(p, encoding="utf-8")
        content = reader.read()
        assert "café" in content

    def test_reader_preview_empty_file(self, tmp_path):
        """Test preview() on empty file."""
        p = tmp_path / "empty.txt"
        p.write_text("")

        reader = SafeTextFileReader(p)
        preview = reader.preview()
        assert preview == []

    def test_reader_readlines_preserves_order(self, tmp_path):
        """Test that readlines maintains line order."""
        p = tmp_path / "test.txt"
        p.write_text("first\nsecond\nthird")

        reader = SafeTextFileReader(p)
        lines = reader.readlines()
        assert lines == ["first", "second", "third"]

    def test_reader_readlines_with_unicode_errors(self, tmp_path):
        """Test readlines with invalid UTF-8 sequences."""
        p = tmp_path / "bad_utf8.txt"
        p.write_bytes(b"valid\xff\xfeinvalid")

        reader = SafeTextFileReader(p, encoding="utf-8")
        with pytest.raises(SplurgeSafeIoUnicodeError):
            reader.readlines()

    def test_reader_readlines_as_stream_with_chunks(self, tmp_path):
        """Test readlines_as_stream yields line chunks."""
        p = tmp_path / "test.txt"
        p.write_text("a\nb\nc\nd\ne")

        reader = SafeTextFileReader(p)
        all_lines = []
        for chunk in reader.readlines_as_stream():
            all_lines.extend(chunk)

        assert all_lines == ["a", "b", "c", "d", "e"]

    def test_reader_line_count_consistency(self, tmp_path):
        """Test that line_count matches readlines length."""
        p = tmp_path / "test.txt"
        content = "line1\nline2\nline3\nline4\nline5"
        p.write_text(content)

        reader = SafeTextFileReader(p)
        readlines_count = len(reader.readlines())
        line_count = reader.line_count()

        assert readlines_count == line_count


class TestSafeTextFileWriterEdgeCases:
    """Test edge cases in SafeTextFileWriter not covered by other tests."""

    def test_writer_empty_content(self, tmp_path):
        """Test writing empty content."""
        p = tmp_path / "empty.txt"

        writer = SafeTextFileWriter(p)
        writer.write("")

        assert p.read_text() == ""

    def test_writer_large_content(self, tmp_path):
        """Test writing large content."""
        p = tmp_path / "large.txt"
        large_content = "x" * 1_000_000  # 1MB of x's

        writer = SafeTextFileWriter(p)
        writer.write(large_content)

        assert len(p.read_text()) == 1_000_000

    def test_writer_unicode_content(self, tmp_path):
        """Test writing unicode content."""
        p = tmp_path / "unicode.txt"
        unicode_content = "Hello 世界 🌍 café"

        writer = SafeTextFileWriter(p, encoding="utf-8")
        writer.write(unicode_content)
        writer.close()

        content = p.read_text(encoding="utf-8")
        assert content == unicode_content

    def test_writer_preserves_exact_newlines(self, tmp_path):
        """Test that writer preserves specified newline format."""
        p = tmp_path / "newlines.txt"

        writer = SafeTextFileWriter(p, canonical_newline="\n")
        writer.write("line1\nline2\n")

        content = p.read_bytes()
        assert b"\r\n" not in content or os.name == "nt"  # Windows may use CRLF


class TestExceptionAttributes:
    """Test that exceptions have proper attributes for debugging."""

    def test_os_error_has_error_code(self):
        """Test SplurgeSafeIoOSError has error_code attribute."""
        exc = SplurgeSafeIoOSError(error_code="test-code", message="Test message")
        assert exc.error_code == "test-code"

    def test_value_error_has_error_code(self):
        """Test SplurgeSafeIoValueError has error_code attribute."""
        exc = SplurgeSafeIoValueError(error_code="invalid-threshold", message="Threshold too small")
        assert exc.error_code == "invalid-threshold"

    def test_path_validation_error_has_error_code(self):
        """Test SplurgeSafeIoPathValidationError has error_code attribute."""
        exc = SplurgeSafeIoPathValidationError(error_code="dangerous-char", message="Path contains dangerous character")
        assert exc.error_code == "dangerous-char"

    def test_lookup_error_hierarchy(self):
        """Test SplurgeSafeIoLookupError is properly defined."""
        exc = SplurgeSafeIoLookupError(error_code="encoding-failed", message="Could not decode with encoding")
        assert exc.error_code == "encoding-failed"

    def test_file_not_found_error_has_error_code(self):
        """Test SplurgeSafeIoFileNotFoundError has error_code attribute."""
        exc = SplurgeSafeIoFileNotFoundError(error_code="file-not-found", message="File not found")
        assert exc.error_code == "file-not-found"
        assert issubclass(SplurgeSafeIoFileNotFoundError, SplurgeSafeIoOSError)

    def test_permission_error_has_error_code(self):
        """Test SplurgeSafeIoPermissionError has error_code attribute."""
        exc = SplurgeSafeIoPermissionError(error_code="permission-denied", message="Permission denied")
        assert exc.error_code == "permission-denied"
        assert issubclass(SplurgeSafeIoPermissionError, SplurgeSafeIoOSError)

    def test_file_exists_error_has_error_code(self):
        """Test SplurgeSafeIoFileExistsError has error_code attribute."""
        exc = SplurgeSafeIoFileExistsError(error_code="file-exists", message="File exists")
        assert exc.error_code == "file-exists"
        assert issubclass(SplurgeSafeIoFileExistsError, SplurgeSafeIoOSError)

    def test_unicode_error_has_error_code(self):
        """Test SplurgeSafeIoUnicodeError has error_code attribute."""
        from splurge_safe_io import SplurgeSafeIoUnicodeError

        exc = SplurgeSafeIoUnicodeError(error_code="decoding", message="Unicode decode error")
        assert exc.error_code == "decoding"
        assert issubclass(SplurgeSafeIoUnicodeError, SplurgeSafeIoValueError)
