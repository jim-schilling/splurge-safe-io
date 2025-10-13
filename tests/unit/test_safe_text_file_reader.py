import codecs
from pathlib import Path

import pytest

from splurge_safe_io.exceptions import SplurgeSafeIoParameterError
from splurge_safe_io.safe_text_file_reader import SafeTextFileReader


def create_mixed_file(tmp_path, filename="mixed.txt"):
    p = tmp_path / filename
    # include different newline styles and multi-byte characters
    content = "line1\r\nline2\nline3\rline4 ü\nline5"
    p.write_bytes(content.encode("utf-8"))
    return p


def test_read_full_and_strip(tmp_path):
    p = create_mixed_file(tmp_path)
    r = SafeTextFileReader(p, strip=True)
    lines = r.read()
    assert lines[0] == "line1"
    assert any("ü" in ln for ln in lines)


def test_preview_limits(tmp_path):
    p = create_mixed_file(tmp_path)
    r = SafeTextFileReader(p)
    preview = r.preview(max_lines=2)
    assert len(preview) == 2


def test_streaming_with_chunks_and_footer(tmp_path):
    p = tmp_path / "ten.txt"
    lines = [f"l{i}" for i in range(10)]
    p.write_text("\n".join(lines))

    r = SafeTextFileReader(p, chunk_size=3, skip_footer_lines=2)
    out = []
    for chunk in r.read_as_stream():
        out.extend(chunk)
    assert len(out) == 8
    assert out[-1] == "l7"


def test_streaming_header_skip(tmp_path):
    p = tmp_path / "h.txt"
    p.write_text("h1\nh2\nbody1\nbody2")
    r = SafeTextFileReader(p, skip_header_lines=2)
    all_lines = []
    for c in r.read_as_stream():
        all_lines.extend(c)
    assert all_lines == ["body1", "body2"]


def test_preview_stops_early_without_full_read(tmp_path, monkeypatch):
    p = tmp_path / "big.txt"
    lines = [f"l{i}" for i in range(100)]
    p.write_text("\n".join(lines))

    def fail_read(self):
        raise AssertionError("_read should not be called for streaming preview")

    monkeypatch.setattr(SafeTextFileReader, "_read", fail_read)

    r = SafeTextFileReader(p)
    preview = r.preview(max_lines=5)
    assert preview == ["l0", "l1", "l2", "l3", "l4"]


def test_preview_encoding_fallback_uses_full_read(tmp_path, monkeypatch):
    p = tmp_path / "utf16.txt"
    p.write_bytes("\n".join(["a", "b", "c", "d"]).encode("utf-16-le"))

    class BrokenDecoder:
        def __init__(self, *args, **kwargs):
            pass

        def decode(self, *args, **kwargs):
            raise UnicodeError("forced")

        def __call__(self, *a, **k):
            return self

    def broken_getinc(name):
        return BrokenDecoder

    monkeypatch.setattr(__import__("codecs"), "getincrementaldecoder", broken_getinc)

    called = {"full": False}
    orig__read = SafeTextFileReader._read

    def tracked_read(self):
        called["full"] = True
        return orig__read(self)

    monkeypatch.setattr(SafeTextFileReader, "_read", tracked_read)

    r = SafeTextFileReader(p, encoding="utf-16-le")
    preview = r.preview(max_lines=2)
    assert preview == ["a", "b"]
    assert called["full"] is True


def test_preview_closes_filehandle_on_early_return(tmp_path, monkeypatch):
    p = tmp_path / "big2.txt"
    p.write_text("\n".join([f"x{i}" for i in range(50)]))

    orig_open = Path.open
    marker = {"closed": False}

    def fake_open(self, mode="rb"):
        real = orig_open(self, mode)

        class Ctx:
            def __init__(self, real, marker):
                self.real = real
                self.marker = marker

            def read(self, n=-1):
                return self.real.read(n)

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                try:
                    self.real.close()
                finally:
                    self.marker["closed"] = True
                return False

            def close(self):
                try:
                    self.real.close()
                finally:
                    self.marker["closed"] = True

        return Ctx(real, marker)

    monkeypatch.setattr(Path, "open", fake_open)

    r = SafeTextFileReader(p, chunk_size=10)
    preview = r.preview(max_lines=1)
    assert preview == ["x0"]
    assert marker["closed"] is True


def test_preview_respects_skip_header_lines(tmp_path, monkeypatch):
    p = tmp_path / "hdr.txt"
    p.write_text("h1\nh2\nbody1\nbody2\nbody3\nbody4")

    def fail_read(self):
        raise AssertionError("_read should not be called for streaming preview with header skip")

    monkeypatch.setattr(SafeTextFileReader, "_read", fail_read)

    r = SafeTextFileReader(p, skip_header_lines=2)
    preview = r.preview(max_lines=2)
    assert preview == ["body1", "body2"]


def test_preview_closes_filehandle_and_allows_deletion(tmp_path, monkeypatch):
    p = tmp_path / "big3.txt"
    p.write_text("\n".join([f"y{i}" for i in range(50)]))

    orig_open = Path.open
    marker = {"closed": False}

    def fake_open(self, mode="rb"):
        real = orig_open(self, mode)

        class Ctx:
            def __init__(self, real, marker):
                self.real = real
                self.marker = marker

            def read(self, n=-1):
                return self.real.read(n)

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                try:
                    self.real.close()
                finally:
                    self.marker["closed"] = True
                return False

            def close(self):
                try:
                    self.real.close()
                finally:
                    self.marker["closed"] = True

        return Ctx(real, marker)

    monkeypatch.setattr(Path, "open", fake_open)

    r = SafeTextFileReader(p, chunk_size=10)
    preview = r.preview(max_lines=1)
    assert preview == ["y0"]
    assert marker["closed"] is True

    try:
        p.unlink()
    except Exception as e:
        raise AssertionError("File could not be deleted after preview; handle might still be open") from e


def test_line_count_small_file_uses_full_read(tmp_path):
    p = tmp_path / "small.txt"
    content = "a\n b\n c\n"
    p.write_bytes(content.encode("utf-8"))

    r = SafeTextFileReader(p)
    count = r.line_count(threshold_bytes=1024 * 1024)
    assert count == 3


def test_line_count_large_file_uses_streaming(tmp_path, monkeypatch):
    p = tmp_path / "large.txt"
    lines = [f"l{i}" for i in range(1000)]
    p.write_text("\n".join(lines))

    r = SafeTextFileReader(p)

    class StatObj:
        st_size = 2_000_000
        import stat as _stat

        st_mode = _stat.S_IFREG

    def fail__read(self):
        raise AssertionError("_read should not be called for streaming path")

    monkeypatch.setattr(Path, "stat", lambda self, *a, **k: StatObj)
    monkeypatch.setattr(SafeTextFileReader, "_read", fail__read)

    count = r.line_count(threshold_bytes=1 * 1024 * 1024)
    assert count == 1000


def test_line_count_encoding_fallback_reads_full(tmp_path, monkeypatch):
    p = tmp_path / "utf16-count.txt"
    p.write_bytes("\n".join(["x", "y", "z"]).encode("utf-16-le"))

    class BrokenDecoder:
        def __init__(self, *a, **k):
            pass

        def decode(self, *a, **k):
            raise UnicodeError("forced")

        def __call__(self, *a, **k):
            return self

    def broken_getinc(name):
        return BrokenDecoder

    monkeypatch.setattr(codecs, "getincrementaldecoder", broken_getinc)

    class StatObj:
        st_size = 2_000_000
        import stat as _stat

        st_mode = _stat.S_IFREG

    monkeypatch.setattr(Path, "stat", lambda self, *a, **k: StatObj)

    # Spy on _read being called (full read) when incremental decoder fails
    called = {"full": False}
    orig__read = SafeTextFileReader._read

    def tracked_read(self):
        called["full"] = True
        return orig__read(self)

    monkeypatch.setattr(SafeTextFileReader, "_read", tracked_read)

    r = SafeTextFileReader(p, encoding="utf-16-le")
    count = r.line_count(threshold_bytes=1 * 1024 * 1024)

    assert count == 3
    assert called["full"] is True


def test_line_count_rejects_small_threshold(tmp_path):
    p = tmp_path / "t.txt"
    p.write_text("1\n2\n3")
    r = SafeTextFileReader(p)
    with pytest.raises(SplurgeSafeIoParameterError):
        r.line_count(threshold_bytes=512 * 1024)


def test_streaming_large_file_skip_empty_lines_behavior(tmp_path, monkeypatch):
    """Create a temporary file >1MiB, force streaming, and validate behavior
    of read_as_stream(), line_count(), and preview() with skip_empty_lines
    True and False.
    """
    p = tmp_path / "large_mixed.txt"

    # Build content mixing non-empty, empty, and whitespace-only lines until
    # we exceed ~1.2 MiB to ensure a realistically large file (but keep write
    # time bounded for CI).
    parts = []
    total = 0
    i = 0
    target = 1_200_000
    pattern = ["data-{}", "", "   ", "more-{}", ""]
    while total < target:
        for pat in pattern:
            if "{}" in pat:
                s = pat.format(i)
            else:
                s = pat
            parts.append(s)
            total += len(s) + 1  # +1 for newline when joined
        i += 1

    content = "\n".join(parts)
    p.write_bytes(content.encode("utf-8"))

    # Fake an on-disk size large enough so the implementation chooses the
    # streaming path (avoid creating a 64+ MiB file in the test).
    class StatObj:
        st_size = 2_000_000
        import stat as _stat

        st_mode = _stat.S_IFREG

    monkeypatch.setattr(Path, "stat", lambda self, *a, **k: StatObj)

    # First: skip_empty_lines = True
    r_true = SafeTextFileReader(p, skip_empty_lines=True)
    collected_true: list[str] = []
    for chunk in r_true.read_as_stream():
        collected_true.extend(chunk)

    # Build expected sequences using the same normalization the reader uses
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    expected_all = normalized.splitlines()
    expected_non_empty = [s for s in expected_all if s.strip() != ""]

    # Exact match: collected (streamed) non-empty lines should equal expected
    assert collected_true == expected_non_empty

    # line_count should match the number of non-empty logical lines
    count_true = r_true.line_count()
    assert count_true == len(expected_non_empty)

    # preview should return the first N non-empty lines
    preview_true = r_true.preview(5)
    assert preview_true == expected_non_empty[:5]

    # Second: skip_empty_lines = False (default)
    r_false = SafeTextFileReader(p, skip_empty_lines=False)
    collected_false: list[str] = []
    for chunk in r_false.read_as_stream():
        collected_false.extend(chunk)

    # Exact match: streamed output should equal the original logical lines
    assert collected_false == expected_all

    count_false = r_false.line_count()
    assert count_false == len(expected_all)

    preview_false = r_false.preview(5)
    # Preview should return the first 5 logical lines (may include empties)
    assert preview_false == expected_all[:5]


def test_streaming_large_file_skip_empty_lines_behavior_utf16(tmp_path, monkeypatch):
    """Same as test_streaming_large_file_skip_empty_lines_behavior but
    the file is written in UTF-16-LE and the incremental decoder is forced
    to fail so the streaming implementation falls back to a full read.
    """
    p = tmp_path / "large_mixed_utf16.txt"

    parts = []
    total = 0
    i = 0
    target = 1_200_000
    pattern = ["data-{}", "", "   ", "more-{}", ""]
    while total < target:
        for pat in pattern:
            if "{}" in pat:
                s = pat.format(i)
            else:
                s = pat
            parts.append(s)
            total += len(s) + 1
        i += 1

    content = "\n".join(parts)
    # write as utf-16-le bytes
    p.write_bytes(content.encode("utf-16-le"))

    # Force incremental decoder to raise to trigger fallback to full read
    class BrokenDecoder:
        def __init__(self, *a, **k):
            pass

        def decode(self, *a, **k):
            raise UnicodeError("forced")

        def __call__(self, *a, **k):
            return self

    def broken_getinc(name):
        return BrokenDecoder

    monkeypatch.setattr(codecs, "getincrementaldecoder", broken_getinc)

    class StatObj:
        st_size = 2_000_000
        import stat as _stat

        st_mode = _stat.S_IFREG

    monkeypatch.setattr(Path, "stat", lambda self, *a, **k: StatObj)

    # First: skip_empty_lines = True
    r_true = SafeTextFileReader(p, skip_empty_lines=True, encoding="utf-16-le")
    collected_true: list[str] = []
    for chunk in r_true.read_as_stream():
        collected_true.extend(chunk)

    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    expected_all = normalized.splitlines()
    expected_non_empty = [s for s in expected_all if s.strip() != ""]

    assert collected_true == expected_non_empty

    count_true = r_true.line_count()
    assert count_true == len(expected_non_empty)

    preview_true = r_true.preview(5)
    assert preview_true == expected_non_empty[:5]

    # Second: skip_empty_lines = False
    r_false = SafeTextFileReader(p, skip_empty_lines=False, encoding="utf-16-le")
    collected_false: list[str] = []
    for chunk in r_false.read_as_stream():
        collected_false.extend(chunk)

    assert collected_false == expected_all

    count_false = r_false.line_count()
    assert count_false == len(expected_all)

    preview_false = r_false.preview(5)
    assert preview_false == expected_all[:5]
