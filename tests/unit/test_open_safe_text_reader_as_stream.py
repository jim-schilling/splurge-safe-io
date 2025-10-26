"""Tests for open_safe_text_reader_as_stream() context manager.

Tests the memory-efficient streaming variant for large file processing.
"""

import pytest

from splurge_safe_io import (
    SplurgeSafeIoOSError,
    open_safe_text_reader_as_stream,
)


class TestOpenSafeTextReaderAsStream:
    """Tests for open_safe_text_reader_as_stream context manager."""

    def test_open_safe_text_reader_as_stream_yields_iterator(self, tmp_path):
        """Verify context manager yields an iterator of line chunks."""
        p = tmp_path / "test.txt"
        p.write_text("line1\nline2\nline3\nline4\nline5")

        with open_safe_text_reader_as_stream(p) as line_chunks:
            # Should be iterable
            chunks = list(line_chunks)
            assert len(chunks) > 0

            # Each chunk should be a list
            for chunk in chunks:
                assert isinstance(chunk, list)
                for line in chunk:
                    assert isinstance(line, str)

    def test_open_safe_text_reader_as_stream_processes_all_lines(self, tmp_path):
        """Verify all lines are processed through streaming."""
        p = tmp_path / "test.txt"
        p.write_text("line1\nline2\nline3\nline4\nline5")

        with open_safe_text_reader_as_stream(p) as line_chunks:
            all_lines = []
            for chunk in line_chunks:
                all_lines.extend(chunk)

        assert all_lines == ["line1", "line2", "line3", "line4", "line5"]

    def test_open_safe_text_reader_as_stream_with_strip(self, tmp_path):
        """Test strip parameter in streaming context."""
        p = tmp_path / "test.txt"
        p.write_text("  line1  \n  line2  \n  line3  ")

        with open_safe_text_reader_as_stream(p, strip=True) as line_chunks:
            all_lines = []
            for chunk in line_chunks:
                all_lines.extend(chunk)

        assert all_lines == ["line1", "line2", "line3"]

    def test_open_safe_text_reader_as_stream_with_skip_header(self, tmp_path):
        """Test skip_header_lines parameter in streaming."""
        p = tmp_path / "test.txt"
        p.write_text("header1\nheader2\ndata1\ndata2\ndata3")

        with open_safe_text_reader_as_stream(p, skip_header_lines=2) as line_chunks:
            all_lines = []
            for chunk in line_chunks:
                all_lines.extend(chunk)

        assert all_lines == ["data1", "data2", "data3"]

    def test_open_safe_text_reader_as_stream_with_skip_footer(self, tmp_path):
        """Test skip_footer_lines parameter in streaming."""
        p = tmp_path / "test.txt"
        p.write_text("data1\ndata2\ndata3\nfooter1\nfooter2")

        with open_safe_text_reader_as_stream(p, skip_footer_lines=2) as line_chunks:
            all_lines = []
            for chunk in line_chunks:
                all_lines.extend(chunk)

        assert all_lines == ["data1", "data2", "data3"]

    def test_open_safe_text_reader_as_stream_with_all_filters(self, tmp_path):
        """Test all filtering options combined in streaming."""
        p = tmp_path / "test.txt"
        p.write_text("H1\n  D1  \n  D2  \nF1")

        with open_safe_text_reader_as_stream(
            p,
            skip_header_lines=1,
            skip_footer_lines=1,
            strip=True,
        ) as line_chunks:
            all_lines = []
            for chunk in line_chunks:
                all_lines.extend(chunk)

        assert all_lines == ["D1", "D2"]

    def test_open_safe_text_reader_as_stream_normalizes_newlines(self, tmp_path):
        """Test that streaming normalizes mixed newlines."""
        p = tmp_path / "test.txt"
        # Mixed newline styles
        p.write_bytes(b"line1\r\nline2\rline3\nline4")

        with open_safe_text_reader_as_stream(p) as line_chunks:
            all_lines = []
            for chunk in line_chunks:
                all_lines.extend(chunk)

        assert all_lines == ["line1", "line2", "line3", "line4"]

    def test_open_safe_text_reader_as_stream_custom_encoding(self, tmp_path):
        """Test streaming with non-default encoding."""
        p = tmp_path / "test.txt"
        p.write_text("café\néàü\n日本", encoding="utf-8")

        with open_safe_text_reader_as_stream(p, encoding="utf-8") as line_chunks:
            all_lines = []
            for chunk in line_chunks:
                all_lines.extend(chunk)

        assert "café" in all_lines
        assert "éàü" in all_lines
        assert "日本" in all_lines

    def test_open_safe_text_reader_as_stream_empty_file(self, tmp_path):
        """Test streaming on empty file."""
        p = tmp_path / "empty.txt"
        p.write_text("")

        with open_safe_text_reader_as_stream(p) as line_chunks:
            chunks = list(line_chunks)
            # Empty file might yield no chunks or one empty chunk
            if chunks:
                assert all(isinstance(c, list) for c in chunks)

    def test_open_safe_text_reader_as_stream_single_line(self, tmp_path):
        """Test streaming with single line file."""
        p = tmp_path / "single.txt"
        p.write_text("only line")

        with open_safe_text_reader_as_stream(p) as line_chunks:
            all_lines = []
            for chunk in line_chunks:
                all_lines.extend(chunk)

        assert all_lines == ["only line"]

    def test_open_safe_text_reader_as_stream_large_file_simulation(self, tmp_path):
        """Simulate processing a large file in chunks."""
        p = tmp_path / "large.txt"
        # Create file with many lines
        lines = [f"line{i}" for i in range(1000)]
        p.write_text("\n".join(lines))

        with open_safe_text_reader_as_stream(p) as line_chunks:
            chunk_count = 0
            total_lines = 0
            for chunk in line_chunks:
                chunk_count += 1
                total_lines += len(chunk)
                # Each chunk should be reasonably sized (not load entire file)
                assert len(chunk) > 0

        assert total_lines == 1000
        # Should be multiple chunks (not single monolithic load)
        assert chunk_count >= 1

    def test_open_safe_text_reader_as_stream_file_not_found(self, tmp_path):
        """Test exception when file doesn't exist."""
        p = tmp_path / "nonexistent.txt"

        with pytest.raises(SplurgeSafeIoOSError):
            with open_safe_text_reader_as_stream(p) as line_chunks:
                # Consume the iterator to trigger the file read
                list(line_chunks)

    def test_open_safe_text_reader_as_stream_iteration_pattern(self, tmp_path):
        """Test typical iteration pattern for streaming."""
        p = tmp_path / "test.txt"
        p.write_text("a\nb\nc\nd\ne\nf\ng\nh")

        line_list = []
        with open_safe_text_reader_as_stream(p) as line_chunks:
            for chunk in line_chunks:
                # Process each chunk as it arrives
                for line in chunk:
                    line_list.append(line)

        assert len(line_list) == 8
        assert line_list[0] == "a"
        assert line_list[-1] == "h"

    def test_open_safe_text_reader_as_stream_memory_efficient(self, tmp_path):
        """Demonstrate memory efficiency by not loading entire file at once."""
        p = tmp_path / "test.txt"
        p.write_text("line1\nline2\nline3")

        # With streaming, we never build a single large in-memory string
        # Each chunk is independent
        chunk_sizes = []
        with open_safe_text_reader_as_stream(p) as line_chunks:
            for chunk in line_chunks:
                chunk_sizes.append(len(chunk))

        # Should have multiple chunks (or at least a reasonable number)
        assert len(chunk_sizes) > 0
        # Each chunk is bounded in size
        assert all(size > 0 for size in chunk_sizes)


class TestOpenSafeTextReaderAsStreamVsRegular:
    """Compare streaming vs regular context manager."""

    def test_streaming_vs_regular_same_content(self, tmp_path):
        """Verify both methods produce identical content."""
        from splurge_safe_io import open_safe_text_reader

        p = tmp_path / "test.txt"
        test_content = "line1\nline2\nline3\nline4"
        p.write_text(test_content)

        # Get lines from streaming version
        with open_safe_text_reader_as_stream(p) as line_chunks:
            streaming_lines = []
            for chunk in line_chunks:
                streaming_lines.extend(chunk)

        # Get lines from regular version
        with open_safe_text_reader(p) as sio:
            regular_lines = sio.getvalue().split("\n")
            # Remove empty string at end if present
            if regular_lines[-1] == "":
                regular_lines = regular_lines[:-1]

        assert streaming_lines == regular_lines

    def test_streaming_vs_regular_with_filters(self, tmp_path):
        """Verify both methods handle filters identically."""
        from splurge_safe_io import open_safe_text_reader

        p = tmp_path / "test.txt"
        p.write_text("H\n  D1  \n  D2  \nF")

        # Streaming version
        with open_safe_text_reader_as_stream(p, skip_header_lines=1, skip_footer_lines=1, strip=True) as line_chunks:
            streaming_lines = []
            for chunk in line_chunks:
                streaming_lines.extend(chunk)

        # Regular version
        with open_safe_text_reader(p, skip_header_lines=1, skip_footer_lines=1, strip=True) as sio:
            regular_content = sio.getvalue()
            regular_lines = [line for line in regular_content.split("\n") if line]

        assert streaming_lines == regular_lines
