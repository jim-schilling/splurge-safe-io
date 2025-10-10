from pathlib import Path

from splurge_safe_io.safe_text_file_reader import SafeTextFileReader


def _make_crlf_file(path: Path, num_lines: int = 300, line_body: str = "X" * 30) -> None:
    # Create lines terminated explicitly with CRLF to reproduce the CRLF split
    with path.open("wb") as fh:
        for i in range(num_lines):
            line = f"{i},{line_body}\r\n".encode()
            fh.write(line)


def _find_splitting_buffer(path: Path, max_buf: int = 512):
    # Find a buffer size in [4, max_buf] such that some CR ("\r") falls
    # at the final byte position of a raw read (i.e., index % buf == buf-1).
    data = path.read_bytes()
    cr_positions = [i for i, b in enumerate(data) if b == 0x0D]  # 0x0d == '\r'
    for buf in range(4, max_buf + 1):
        for pos in cr_positions:
            if pos % buf == (buf - 1):
                return buf
    return None


def test_crlf_split_boundary_roundtrip(tmp_path: Path):
    f = tmp_path / "crlf_split.csv"
    _make_crlf_file(f, num_lines=600)

    buf = _find_splitting_buffer(f, max_buf=1024)
    assert buf is not None, "Failed to find a buffer size that splits a CRLF across a boundary"

    reader = SafeTextFileReader(f, buffer_size=buf, chunk_size=100, strip=False)
    flattened = [ln for chunk in reader.read_as_stream() for ln in chunk]
    read_all = reader.read()

    assert flattened == read_all
