from pathlib import Path

import pytest

from splurge_safe_io.constants import MIN_BUFFER_SIZE
from splurge_safe_io.safe_text_file_reader import SafeTextFileReader


@pytest.mark.parametrize("line_len", [1, 5, 16, 31, 64, 127, 256, 511, 1024])
@pytest.mark.parametrize("newline", ["\r\n", "\n"])  # include CRLF and LF
def test_line_length_and_buffer_boundaries(tmp_path: Path, line_len: int, newline: str):
    # Generate a file with many lines of specified byte length (excluding newline)
    suffix = "crlf" if newline == "\r\n" else "lf"
    f = tmp_path / f"lines_len_{line_len}_{suffix}.txt"
    body = "A" * line_len
    # Write 2000 lines to ensure many raw-read boundaries
    with f.open("wb") as fh:
        for i in range(2000):
            fh.write(f"{i},{body}".encode() + newline.encode("utf-8"))

    # Try a selection of buffer sizes (including MIN_BUFFER_SIZE and multiples)
    buffer_sizes = [MIN_BUFFER_SIZE, MIN_BUFFER_SIZE + 1, 2048, 4096, 8192]
    for buf in buffer_sizes:
        reader = SafeTextFileReader(f, buffer_size=buf, chunk_size=500, strip=False)
        flattened = [ln for chunk in reader.read_as_stream() for ln in chunk]
        read_all = reader.read()
        assert flattened == read_all, f"Mismatch for line_len={line_len} newline={repr(newline)} buf={buf}"
