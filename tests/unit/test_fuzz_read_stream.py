import hypothesis.strategies as st
from hypothesis import given, settings

from splurge_safe_io.safe_text_file_reader import SafeTextFileReader


@settings(max_examples=30, deadline=2000)
@given(
    buf=st.integers(min_value=256, max_value=8192),
    num_lines=st.integers(min_value=50, max_value=2000),
    max_line_len=st.integers(min_value=1, max_value=1024),
)
def test_fuzz_stream_vs_read(buf: int, num_lines: int, max_line_len: int):
    # Build a file with many lines of varying lengths up to max_line_len
    import tempfile
    from pathlib import Path as _P

    td = tempfile.TemporaryDirectory()
    f = _P(td.name) / "fuzz_test.txt"
    import random

    rng = random.Random(0)
    with f.open("wb") as fh:
        for i in range(num_lines):
            ln = "".join(rng.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(rng.randint(1, max_line_len)))
            fh.write(f"{i},{ln}\r\n".encode())

    reader = SafeTextFileReader(f, buffer_size=buf, chunk_size=500, strip=False)
    flattened = [ln for chunk in reader.read_as_stream() for ln in chunk]
    read_all = reader.read()
    assert flattened == read_all
    td.cleanup()
