from splurge_safe_io import constants


def test_constants_exist():
    assert hasattr(constants, "CANONICAL_NEWLINE")
    assert hasattr(constants, "DEFAULT_ENCODING")
    assert hasattr(constants, "DEFAULT_CHUNK_SIZE")
    assert hasattr(constants, "MIN_CHUNK_SIZE")
    assert isinstance(constants.CANONICAL_NEWLINE, str)
    assert isinstance(constants.DEFAULT_ENCODING, str)
    assert isinstance(constants.DEFAULT_CHUNK_SIZE, int)
    assert isinstance(constants.MIN_CHUNK_SIZE, int)
