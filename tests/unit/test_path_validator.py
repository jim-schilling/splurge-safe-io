import pytest

from splurge_safe_io.exceptions import SplurgeSafeIoOSError, SplurgeSafeIoPathValidationError
from splurge_safe_io.path_validator import PathValidator


def test_validate_existing_file(tmp_path):
    f = tmp_path / "foo.txt"
    f.write_text("hello")
    resolved = PathValidator.get_validated_path(str(f), must_exist=True, must_be_file=True)
    assert str(resolved).endswith("foo.txt")


def test_nonexistent_file_raises(tmp_path):
    f = tmp_path / "nope.txt"
    with pytest.raises(SplurgeSafeIoOSError):
        PathValidator.get_validated_path(str(f), must_exist=True)


def test_control_character_rejected(tmp_path):
    bad = "bad\x00name"
    with pytest.raises(SplurgeSafeIoPathValidationError):
        PathValidator.get_validated_path(bad)


def test_base_directory_restriction(tmp_path):
    base = tmp_path / "base"
    base.mkdir()
    inside = base / "inside.txt"
    inside.write_text("x")
    outside = tmp_path / "outside.txt"
    outside.write_text("y")

    # inside should be allowed when base_directory provided
    resolved = PathValidator.get_validated_path(inside, base_directory=base)
    assert base in resolved.parents or resolved == inside

    # outside should fail when resolved outside base_directory
    with pytest.raises(SplurgeSafeIoPathValidationError):
        PathValidator.get_validated_path(outside, base_directory=base)


def test_register_pre_resolution_policy(tmp_path):
    def deny_dotdot(p: str):
        if ".." in p:
            raise SplurgeSafeIoPathValidationError("dotdot-not-allowed")

    PathValidator.register_pre_resolution_policy(deny_dotdot)
    with pytest.raises(SplurgeSafeIoPathValidationError):
        PathValidator.get_validated_path("../etc/passwd")
    PathValidator.clear_pre_resolution_policies()
    # after clearing policies, the same path won't raise (but may fail other checks)
    # we don't assert success because other environment specifics might intervene
