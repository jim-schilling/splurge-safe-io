"""Tests for specific uncovered code paths in safe_text_file_reader and safe_text_file_writer.

This module targets specific lines identified in coverage gaps:
- Lines 435-440 in safe_text_file_reader.py (footer buffer with skip_empty_lines + strip)
- Lines 288-293 in safe_text_file_writer.py (exception handling)
"""

import pytest

from splurge_safe_io import (
    SafeTextFileReader,
    SafeTextFileWriter,
    SplurgeSafeIoOSError,
    SplurgeSafeIoRuntimeError,
    SplurgeSafeIoUnicodeError,
)


class TestReaderFooterBufferWithFilters:
    """Test footer buffer handling with skip_empty_lines and strip combinations.

    Targets lines 435-440 in safe_text_file_reader.py:
    - footer_buf.append(raw_line)
    - if len(footer_buf) == footer_buf.maxlen: (condition)
    - emit_raw = footer_buf.popleft()
    - if not (self.skip_empty_lines and emit_raw.strip() == ""):
    - emit_out = emit_raw.strip() if self.strip else emit_raw
    - chunk.append(emit_out)
    """

    def test_streaming_footer_buffer_with_skip_empty_lines_and_strip(self, tmp_path):
        """Test footer buffer emission with both skip_empty_lines and strip enabled.

        This exercises the code path where:
        1. Footer buffer fills (footer_buf.append, len check, popleft)
        2. skip_empty_lines is True (the and condition in line 438)
        3. strip is True (line 439 ternary)
        4. Line is non-empty (so it gets emitted)
        """
        p = tmp_path / "test.txt"
        # Create content with non-empty lines that will hit footer buffer
        # File: line1\nline2\nline3\nline4\nline5
        # With skip_footer_lines=1, the footer_buf will be filled with line4, then
        # on line5 it will emit line4 (non-empty)
        p.write_text("line1\nline2\nline3\nline4\nline5")

        reader = SafeTextFileReader(
            p,
            skip_footer_lines=1,
            skip_empty_lines=True,
            strip=True,
        )

        # Stream through the reader
        all_lines = []
        for chunk in reader.readlines_as_stream():
            all_lines.extend(chunk)

        # With skip_footer_lines=1, the last line should be skipped
        # But the previous lines should be stripped and empty ones removed
        assert "line5" not in all_lines
        assert "line1" in all_lines
        assert "line2" in all_lines
        assert "line3" in all_lines
        assert "line4" in all_lines

    def test_streaming_footer_buffer_with_empty_line_before_footer(self, tmp_path):
        """Test footer buffer when empty line is in the buffer and gets popleft.

        This exercises the specific condition:
        if not (self.skip_empty_lines and emit_raw.strip() == ""):

        When emit_raw is an empty line and skip_empty_lines is True,
        the line should NOT be added to chunk.
        """
        p = tmp_path / "test.txt"
        # Content with empty lines before the footer
        # The footer buffer will contain: "line3", "", then popleft "line3"
        p.write_text("line1\nline2\nline3\n\nline5")

        reader = SafeTextFileReader(
            p,
            skip_footer_lines=1,
            skip_empty_lines=True,
            strip=False,  # Keep whitespace as-is
        )

        all_lines = []
        for chunk in reader.readlines_as_stream():
            all_lines.extend(chunk)

        # The final empty line should be skipped (it's in footer)
        # But the earlier content should be there
        assert "line1" in all_lines
        assert "line2" in all_lines
        assert "line3" in all_lines

    def test_streaming_footer_buffer_with_strip_on_empty_lines(self, tmp_path):
        """Test that strip is applied to footer buffer lines correctly.

        This exercises line 439:
        emit_out = emit_raw.strip() if self.strip else emit_raw

        When strip=True and a line has leading/trailing whitespace,
        it should be stripped before going into the chunk.
        """
        p = tmp_path / "test.txt"
        # Lines with whitespace that will be stripped
        p.write_text("  line1  \n  line2  \n  line3  \n  line4  ")

        reader = SafeTextFileReader(
            p,
            skip_footer_lines=1,
            strip=True,
        )

        all_lines = []
        for chunk in reader.readlines_as_stream():
            all_lines.extend(chunk)

        # All lines except the last (footer) should be stripped
        assert "line1" in all_lines
        assert "line2" in all_lines
        assert "line3" in all_lines
        assert "  line4  " not in all_lines  # Not this exact string
        # The last line is in footer so not emitted
        assert len(all_lines) == 3

    def test_streaming_footer_buffer_popleft_flow(self, tmp_path):
        """Test the specific flow of footer_buf.popleft() being called.

        Targets line 437: emit_raw = footer_buf.popleft()

        This flow occurs when the footer buffer reaches maxlen,
        which happens with skip_footer_lines >= 1 and we have multiple lines.
        The buffer fills when we reach the maxlen and need to emit the leftmost.
        """
        p = tmp_path / "test.txt"
        # Create many lines to ensure footer buffer fills multiple times
        # The footer_buf.maxlen is set to skip_footer_lines, so with
        # skip_footer_lines=3, buffer fills after 3 lines, then popleft happens
        # on the 4th line
        content = "\n".join([f"line{i}" for i in range(1, 11)])
        p.write_text(content)

        reader = SafeTextFileReader(
            p,
            skip_footer_lines=3,
            skip_empty_lines=False,
            strip=False,
        )

        all_lines = []
        for chunk in reader.readlines_as_stream():
            all_lines.extend(chunk)

        # Last 3 lines should be in footer and not emitted
        assert "line8" not in all_lines
        assert "line9" not in all_lines
        assert "line10" not in all_lines
        # But earlier lines should be there
        assert "line1" in all_lines
        assert "line7" in all_lines
        assert len(all_lines) == 7

    def test_streaming_footer_buffer_no_skip_empty_when_not_enabled(self, tmp_path):
        """Test that skip_empty_lines condition doesn't affect non-empty lines.

        When a line is non-empty, the condition:
        if not (self.skip_empty_lines and emit_raw.strip() == ""):
        should always be True, so line is emitted regardless of skip_empty_lines.
        """
        p = tmp_path / "test.txt"
        p.write_text("line1\nline2\nline3\nline4")

        # Test with skip_empty_lines=False
        reader1 = SafeTextFileReader(
            p,
            skip_footer_lines=1,
            skip_empty_lines=False,
        )

        lines1 = []
        for chunk in reader1.readlines_as_stream():
            lines1.extend(chunk)

        # Test with skip_empty_lines=True
        reader2 = SafeTextFileReader(
            p,
            skip_footer_lines=1,
            skip_empty_lines=True,
        )

        lines2 = []
        for chunk in reader2.readlines_as_stream():
            lines2.extend(chunk)

        # Both should have same lines (no empty lines in this file)
        assert lines1 == lines2
        assert len(lines1) == 3  # line1-3, line4 is footer

    def test_footer_buffer_popleft_with_various_line_content(self, tmp_path):
        """Test footer buffer emission with varied line types to trigger popleft.

        This specifically targets the popleft flow (lines 435-440) by ensuring
        the footer buffer fills and needs to emit items. Creates content where
        the buffer will definitely fill during streaming.
        """
        p = tmp_path / "test.txt"
        # Create content where we have enough lines for footer buffer to fill
        # With skip_footer_lines=2, buffer maxlen is 2
        # Lines will be: [line1, line2] -> buffers line1, line2
        #               [line3] -> add to buffer, now len==2==maxlen, popleft line1
        #               [line4] -> add to buffer, now len==2==maxlen, popleft line2
        #               etc.
        content = "data1\ndata2\ndata3\ndata4\ndata5"
        p.write_text(content)

        reader = SafeTextFileReader(
            p,
            skip_footer_lines=2,
            skip_empty_lines=False,
            strip=True,
        )

        # Force streaming which triggers the popleft
        lines = []
        for chunk in reader.readlines_as_stream():
            lines.extend(chunk)

        # Lines 1-3 should be emitted (popleft'd from buffer)
        # Lines 4-5 stay in buffer as footer
        assert "data1" in lines
        assert "data2" in lines
        assert "data3" in lines
        assert "data4" not in lines  # Still in footer
        assert "data5" not in lines  # Still in footer


class TestWriterExceptionHandling:
    """Test exception handling code paths in safe_text_file_writer.py.

    Targets lines 288-293 in safe_text_file_writer.py:
    - UnicodeEncodeError handling (line 285-286)
    - OSError handling (line 288-292)
    - Exception handling (line 294-296)

    These are marked with pragma: no cover, so we need monkeypatching
    to trigger the error conditions.
    """

    def test_write_unicode_encode_error(self, tmp_path):
        """Test that UnicodeEncodeError is properly mapped to SplurgeSafeIoUnicodeError.

        Targets line 285-286 exception handling.
        """
        p = tmp_path / "test.txt"

        writer = SafeTextFileWriter(p, encoding="ascii")

        # Try to write content that can't be encoded in ASCII
        with pytest.raises(SplurgeSafeIoUnicodeError) as exc_info:
            writer.write("café")  # Contains non-ASCII character

        assert "encoding" in str(exc_info.value).lower()

    def test_write_os_error_handling(self, tmp_path):
        """Test that OSError during write is mapped to SplurgeSafeIoOSError.

        Targets lines 288-292 exception handling.
        """
        p = tmp_path / "test.txt"

        writer = SafeTextFileWriter(p)

        # Mock the file object's write method to raise OSError
        def raise_os_error(*args, **kwargs):
            raise OSError("Simulated OS error")

        writer._file_obj.write = raise_os_error

        with pytest.raises(SplurgeSafeIoOSError) as exc_info:
            writer.write("test content")

        assert "general" in str(exc_info.value).lower()

    def test_write_generic_exception_handling(self, tmp_path):
        """Test that generic exceptions are mapped to SplurgeSafeIoRuntimeError.

        Targets lines 294-296 exception handling.
        """
        p = tmp_path / "test.txt"

        writer = SafeTextFileWriter(p)

        # Mock the file object's write method to raise a generic exception
        def raise_generic_error(*args, **kwargs):
            raise RuntimeError("Simulated runtime error")

        writer._file_obj.write = raise_generic_error

        with pytest.raises(SplurgeSafeIoRuntimeError) as exc_info:
            writer.write("test content")

        assert "general" in str(exc_info.value).lower()

    def test_write_error_includes_file_path(self, tmp_path):
        """Test that error messages include the file path for debugging.

        All three exception paths should include self._file_path in the message.
        """
        p = tmp_path / "test.txt"

        writer = SafeTextFileWriter(p)

        # Mock to raise OSError
        def raise_os_error(*args, **kwargs):
            raise OSError("test error")

        writer._file_obj.write = raise_os_error

        with pytest.raises(SplurgeSafeIoOSError) as exc_info:
            writer.write("test")

        # File path should be in the error message
        assert str(p) in str(exc_info.value) or "test.txt" in str(exc_info.value)

    def test_writelines_with_unicode_error(self, tmp_path):
        """Test writelines also properly handles UnicodeEncodeError.

        writelines uses the same _write_to_file method.
        """
        p = tmp_path / "test.txt"

        writer = SafeTextFileWriter(p, encoding="ascii")

        # Try to write lines with non-ASCII characters
        with pytest.raises(SplurgeSafeIoUnicodeError):
            writer.writelines(["line1\n", "café\n", "line3\n"])
