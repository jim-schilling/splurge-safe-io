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
    # create 10 lines
    p = tmp_path / "ten.txt"
    lines = [f"l{i}" for i in range(10)]
    p.write_text("\n".join(lines))

    # skip last 2 as footer, chunk size 3
    r = SafeTextFileReader(p, chunk_size=3, skip_footer_lines=2)
    out = []
    for chunk in r.read_as_stream():
        out.extend(chunk)
    # should have emitted 8 lines (10 - 2 footer)
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
    # Create 100 lines
    p = tmp_path / "big.txt"
    lines = [f"l{i}" for i in range(100)]
    p.write_text("\n".join(lines))

    # Prevent the full-read path from being called: _read should not be used
    def fail_read(self):
        raise AssertionError("_read should not be called for streaming preview")

    monkeypatch.setattr(SafeTextFileReader, "_read", fail_read)

    r = SafeTextFileReader(p)
    preview = r.preview(max_lines=5)
    assert len(preview) == 5
    assert preview == ["l0", "l1", "l2", "l3", "l4"]


def test_preview_encoding_fallback_uses_full_read(tmp_path, monkeypatch):
    # Prepare a file with a few lines encoded in utf-16-le
    p = tmp_path / "utf16.txt"
    content_lines = ["a", "b", "c", "d"]
    p.write_bytes("\n".join(content_lines).encode("utf-16-le"))

    # Force the incremental decoder to raise UnicodeError so the
    # read_as_stream fallback path is exercised.

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

    # Spy on _read being called (full read)
    called = {"full": False}
    orig__read = SafeTextFileReader._read

    def tracked_read(self):
        called["full"] = True
        return orig__read(self)

    monkeypatch.setattr(SafeTextFileReader, "_read", tracked_read)

    # Use encoding that matches how we wrote the file for the final full read
    r = SafeTextFileReader(p, encoding="utf-16-le")
    preview = r.preview(max_lines=2)
    assert preview == ["a", "b"]
    assert called["full"] is True


def test_preview_closes_filehandle_on_early_return(tmp_path, monkeypatch):
    p = tmp_path / "big2.txt"
    p.write_text("\n".join([f"x{i}" for i in range(50)]))

    # Wrap Path.open to return a context manager that marks when closed
    from pathlib import Path

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
    # Ask for a single line so preview returns early
    preview = r.preview(max_lines=1)
    assert preview == ["x0"]
    # The fake context manager should have been closed when preview returned
    assert marker["closed"] is True


def test_preview_respects_skip_header_lines(tmp_path, monkeypatch):
    # Create file with header lines and body
    p = tmp_path / "hdr.txt"
    p.write_text("h1\nh2\nbody1\nbody2\nbody3\nbody4")

    # Prevent the full-read path from being used
    def fail_read(self):
        raise AssertionError("_read should not be called for streaming preview with header skip")

    monkeypatch.setattr(SafeTextFileReader, "_read", fail_read)

    # Ask for two preview lines but skip the two headers
    r = SafeTextFileReader(p, skip_header_lines=2)
    preview = r.preview(max_lines=2)
    assert preview == ["body1", "body2"]


def test_preview_closes_filehandle_and_allows_deletion(tmp_path, monkeypatch):
    # Similar to the previous closure test, but also attempt to delete the file
    p = tmp_path / "big3.txt"
    p.write_text("\n".join([f"y{i}" for i in range(50)]))

    from pathlib import Path

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

    # Try to delete the file to ensure no OS-level lock remains (Windows check)
    try:
        p.unlink()
    except Exception as e:
        # If deletion failed, surface a helpful message for debugging
        raise AssertionError("File could not be deleted after preview; handle might still be open") from e
