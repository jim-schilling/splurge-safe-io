from pathlib import Path

import pytest

from splurge_safe_io.safe_text_file_reader import SafeTextFileReader


def _write_lines_with_nl(path: Path, nl: str, count: int = 800, body: str = "Body"):
    # Write raw bytes using UTF-8 encoding with the given newline string
    with path.open("wb") as fh:
        for i in range(count):
            fh.write(f"{i},{body}".encode() + nl.encode("utf-8"))


def _find_buffer_splitting_nl(path: Path, nl: str, max_buf: int = 4096):
    data = path.read_bytes()
    nl_bytes = nl.encode("utf-8")
    # find positions where nl_bytes occurs and try to find a buffer size
    positions = [i for i in range(len(data) - len(nl_bytes) + 1) if data[i : i + len(nl_bytes)] == nl_bytes]
    for buf in range(4, max_buf + 1):
        for pos in positions:
            # check if the first byte of the newline sits at the last byte of a raw read
            if pos % buf == buf - 1:
                return buf
    return None


@pytest.mark.parametrize(
    "nl",
    ["\n", "\r", "\r\n", "\u0085", "\u2028", "\u2029"],
)
def test_newline_variants_split_roundtrip(tmp_path: Path, nl: str):
    safe_suffix = nl.encode("unicode_escape").decode("ascii").replace("\\", "_")
    f = tmp_path / ("nl_test_" + safe_suffix + ".bin")
    _write_lines_with_nl(f, nl, count=800, body="X" * 50)

    buf = _find_buffer_splitting_nl(f, nl, max_buf=2048)
    if buf is None:
        pytest.skip(f"Couldn't find a buffer size in range that splits newline {repr(nl)} across a boundary")

    reader = SafeTextFileReader(f, buffer_size=buf, chunk_size=100, strip=False)
    flattened = [ln for chunk in reader.read_as_stream() for ln in chunk]
    read_all = reader.read()

    assert flattened == read_all


def test_utf16le_no_bom_fallback_roundtrip(tmp_path: Path):
    # Write a UTF-16-LE file without a BOM. The reader requested encoding 'utf-16'
    # may encounter a decoding issue which triggers the fallback full-read path.
    f = tmp_path / "utf16le_no_bom.txt"
    lines = [f"{i},Data{{i}}" for i in range(300)]
    # write with explicit utf-16-le to avoid BOM being inserted
    with f.open("w", encoding="utf-16-le", newline="\r\n") as fh:
        for ln in lines:
            fh.write(ln + "\r\n")

    # Request 'utf-16' to exercise potential incremental decoder issues
    reader = SafeTextFileReader(f, encoding="utf-16", buffer_size=4096, chunk_size=100, strip=False)
    flattened = [ln for chunk in reader.read_as_stream() for ln in chunk]
    read_all = reader.read()

    assert flattened == read_all
