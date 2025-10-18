from pathlib import Path

import pytest

from splurge_safe_io.path_validator import PathValidator


def test_validate_path_deprecated_emits_warning(tmp_path):
    p = tmp_path / "file.txt"
    # Should not raise, but should warn
    with pytest.warns(DeprecationWarning):
        resolved = PathValidator.validate_path(p, must_exist=False)
    assert isinstance(resolved, Path)
