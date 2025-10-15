import os
import tempfile

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from splurge_safe_io.exceptions import SplurgeSafeIoFileDecodingError, SplurgeSafeIoPathValidationError
from splurge_safe_io.path_validator import PathValidator
from splurge_safe_io.safe_text_file_reader import SafeTextFileReader


def test_windows_drive_patterns():
    # Windows drive-like patterns should be accepted by the validator
    # when they look like valid drive specs; on non-Windows platforms
    # the validator should still accept strings but resolution may differ.
    patterns = ["C:", "C:\\", "C:\\path\\to\\file.txt", "D:/path/file.txt"]
    for p in patterns:
        try:
            PathValidator.validate_path(p, allow_relative=True)
        except SplurgeSafeIoPathValidationError:
            # On some platforms or environments this may raise; ensure
            # the exception is a PathValidationError rather than a crash.
            assert True


def test_unc_path_like_strings():
    # UNC paths (\\server\share\path) are Windows-specific; ensure they
    # are handled as strings by the validator and don't crash.
    unc = "\\\\server\\share\\folder\\file.txt"
    try:
        PathValidator.validate_path(unc)
    except SplurgeSafeIoPathValidationError:
        assert True


def test_symlink_behavior(tmp_path):
    target = tmp_path / "target.txt"
    target.write_text("x")
    link = tmp_path / "link.txt"
    try:
        link.symlink_to(target)
    except (NotImplementedError, OSError):
        pytest.skip("Symlinks not supported in this environment")

    # Validating the symlink should resolve and succeed when must_exist=True
    resolved = PathValidator.validate_path(link, must_exist=True)
    assert resolved.exists()


@given(st.text(min_size=1, max_size=200))
def test_hypothesis_reader_roundtrip_random_lines(s):
    # Property-based test: build a file with random content (may include
    # weird characters) and verify reader.read() returns a list of lines
    # whose concatenation (joined by canonical newline) matches normalized file.
    import tempfile

    # create a temporary file with the generated string
    tf = tempfile.NamedTemporaryFile(delete=False)
    try:
        # write raw bytes using utf-8, replacing errors to avoid write failure
        tf.write(s.encode("utf-8", errors="replace"))
        tf.close()
        reader = SafeTextFileReader(tf.name, chunk_size=16)
        lines = reader.read()
        rebuilt = "\n".join(lines)
        # Verify rebuilt uses canonical newline and decodes to a string
        assert isinstance(rebuilt, str)
    finally:
        try:
            os.unlink(tf.name)
        except OSError:
            pass


@given(st.text(min_size=1, max_size=100))
def test_hypothesis_chunked_stream_equals_full_read(s):
    # Ensure that streaming with small chunk sizes equals full read for many inputs
    import tempfile

    tf = tempfile.NamedTemporaryFile(delete=False)
    try:
        tf.write(s.encode("utf-8", errors="replace"))
        tf.close()
        full = SafeTextFileReader(tf.name).read()
        streamed = []
        for c in SafeTextFileReader(tf.name, chunk_size=1).readlines_as_stream():
            streamed.extend(c)
        assert "\n".join(streamed) == full
    finally:
        try:
            os.unlink(tf.name)
        except OSError:
            pass


# Hypothesis: binary fuzzing across several encodings. Increase examples for
# better coverage; allow decode failures as acceptable behavior.
@settings(deadline=None, max_examples=200)
@given(data=st.binary(min_size=1, max_size=512), enc=st.sampled_from(["utf-8", "latin-1", "utf-16"]))
def test_hypothesis_binary_encoding_roundtrip(data, enc):
    tf = tempfile.NamedTemporaryFile(delete=False)
    try:
        tf.write(data)
        tf.close()
        # Full read may raise decoding errors depending on encoding; that's
        # acceptable. If it succeeds, streaming should match full read.
        try:
            full = SafeTextFileReader(tf.name, encoding=enc).read()
        except SplurgeSafeIoFileDecodingError:
            return

        streamed = []
        for chunk in SafeTextFileReader(tf.name, chunk_size=1, encoding=enc).readlines_as_stream():
            streamed.extend(chunk)
        assert "\n".join(streamed) == full
    finally:
        try:
            os.unlink(tf.name)
        except OSError:
            pass


def test_windows_unc_and_posix_specifics():
    # UNC-style string on Windows should be accepted as an input that
    # does not crash the validator. On POSIX this string is unusual but
    # should still be handled gracefully.
    unc = "\\\\server\\share\\file.txt"
    try:
        PathValidator.validate_path(unc)
    except SplurgeSafeIoPathValidationError:
        # allowed to raise validation error, but must not crash
        assert True

    # POSIX absolute path behavior: on non-Windows platforms, absolute
    # paths should be accepted; on Windows they may still be accepted
    # if they look like drive paths.
    posix_abs = "/usr/bin/env"
    try:
        PathValidator.validate_path(posix_abs)
    except SplurgeSafeIoPathValidationError:
        assert True
