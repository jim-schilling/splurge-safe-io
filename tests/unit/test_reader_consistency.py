from pathlib import Path

from splurge_safe_io.safe_text_file_reader import SafeTextFileReader, open_safe_text_reader

TEST_DIR = Path("tmp")
TEST_DIR.mkdir(exist_ok=True)
TEST_FILE = TEST_DIR / "test_reader_consistency.txt"
NUM_LINES = 10_000


def write_test_file(path: Path, n: int) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for i in range(1, n + 1):
            fh.write(f"Line{i}\n")


def test_reader_consistency_roundtrip():
    """Writes NUM_LINES lines and asserts three read methods agree.

    - SafeTextFileReader.read()
    - SafeTextFileReader.readlines_as_stream() flattened
    - open_safe_text_reader() result
    """
    write_test_file(TEST_FILE, NUM_LINES)

    for _ in range(50):
        reader = SafeTextFileReader(TEST_FILE, buffer_size=4096, chunk_size=100)

        actual0 = reader.read()

        # Flatten streamed chunks into a single list
        actual1 = []
        for chunk in reader.readlines_as_stream():
            actual1.extend(chunk)

        actual2 = []
        # open_safe_text_reader yields a StringIO with normalized content
        with open_safe_text_reader(TEST_FILE) as sio:
            actual2 = list(sio.read().splitlines())

        assert actual0.splitlines() == actual1
        assert actual0 == "\n".join(actual2)
        assert actual1 == actual2
