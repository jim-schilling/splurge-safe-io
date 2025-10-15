from pathlib import Path

import pytest

from splurge_safe_io.constants import MIN_BUFFER_SIZE
from splurge_safe_io.safe_text_file_reader import SafeTextFileReader

TEST_FILE = Path("tmp") / "large_clean.csv"


def _write_clean_csv(path: Path, rows: int = 1000):
    header = "id,name,value,description"
    lines = [header] + [f"{i},Item{i},Value{i},Description for item {i}" for i in range(rows)]
    path.write_text("\n".join(lines), encoding="utf-8")


@pytest.mark.integration
def test_flattened_stream_equals_read(tmp_path):
    # Recreate the input file
    target = tmp_path / "large_clean.csv"
    _write_clean_csv(target, rows=1000)

    reader = SafeTextFileReader(target, buffer_size=MIN_BUFFER_SIZE, chunk_size=500, strip=True)

    flattened = [ln for chunk in reader.readlines_as_stream() for ln in chunk]
    read_all = reader.read()

    # The correct behavior is equality between the flattened streamed output
    # and the full read(). This assertion verifies the bug is fixed.
    assert flattened == read_all.splitlines()
