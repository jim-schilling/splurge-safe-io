import builtins as _builtins
import sys
from collections.abc import Callable
from pathlib import Path
from pathlib import Path as _Path

import pytest


@pytest.fixture
def permit_only_target_open(monkeypatch) -> Callable[[str, BaseException], None]:
    """Monkeypatch ``builtins.open`` so it raises ``exc`` only when called
    for ``target_path`` and otherwise calls through to the real ``open``.

    This helper reduces the blast radius of global ``open`` monkeypatches
    used in tests that simulate platform-level errors (PermissionError,
    UnicodeEncodeError, etc.). Tests using this fixture remain serial
    (do not run in parallel) because they replace a global builtin for the
    duration of the test; the fixture relies on pytest's ``monkeypatch`` to
    restore the original behavior at teardown.

    Usage:
        permit_only_target_open(str(path), PermissionError("nope"))
    """

    def _patch(target_path: str | Path, exc: BaseException) -> None:
        real_open = _builtins.open

        target_str = str(Path(target_path))

        def _fake_open(name, *args, **kwargs):
            try:
                name_str = str(Path(name))
            except Exception:
                name_str = str(name)
            if name_str == target_str:
                raise exc
            return real_open(name, *args, **kwargs)

        monkeypatch.setattr(_builtins, "open", _fake_open)

    return _patch


# Ensure tests can import the local package when pytest runs from the
# repository root or when the test runner's CWD differs. Prepend the
# repository root to sys.path so `import splurge_safe_io` resolves to the
# local source tree.
_ROOT = _Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
