import codecs

from splurge_safe_io.safe_text_file_reader import SafeTextFileReader


class FakeDecoder:
    """A fake incremental decoder that yields predetermined outputs
    across successive decode() calls to simulate partial decode behavior.
    """

    def __init__(self, outputs):
        # outputs is an iterable of strings to return on each decode call
        self._outputs = list(outputs)
        self._idx = 0

    def decode(self, b, final=False):
        # ignore input bytes; return next output or empty
        if self._idx < len(self._outputs):
            out = self._outputs[self._idx]
            self._idx += 1
            return out
        return ""


def make_decoder_factory(outputs):
    def factory(enc):
        return lambda: FakeDecoder(outputs)

    return factory


def test_final_parts_and_carry_emission(monkeypatch, tmp_path):
    p = tmp_path / "fake.txt"
    p.write_bytes(b"irrelevant")

    # Simulate decode() returning partial lines across calls, with the
    # final decode producing remaining text. This should force the code
    # path that computes final_parts and final_carry.
    # Sequence: first decode returns "a\npart", second returns "ial\nend\n",
    # final decode returns "" on final=True
    monkeypatch.setattr(codecs, "getincrementaldecoder", make_decoder_factory(["a\npart", "ial\nend\n"]))

    reader = SafeTextFileReader(
        p, encoding="utf-8", strip=False, skip_header_lines=0, skip_footer_lines=0, chunk_size=10
    )
    out = []
    for chunk in reader.read_as_stream():
        out.extend(chunk)

    # Expected lines: 'a' and 'partial' and 'end'
    assert "a" in out
    assert "partial" in out
    assert "end" in out


def test_footer_buffering_with_final_carry(monkeypatch, tmp_path):
    p = tmp_path / "fake2.txt"
    p.write_bytes(b"x")

    # Decoder returns two lines and then a final carry without newline
    monkeypatch.setattr(codecs, "getincrementaldecoder", make_decoder_factory(["1\n2\n", "3part"]))

    reader = SafeTextFileReader(
        p, encoding="utf-8", strip=True, skip_header_lines=0, skip_footer_lines=2, chunk_size=10
    )
    out = []
    for chunk in reader.read_as_stream():
        out.extend(chunk)

    # There are 3 logical lines: '1', '2', and '3part' but footer=2 => only '1' emitted
    assert out == ["1"]
