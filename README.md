# splurge-safe-io

[![PyPI version](https://badge.fury.io/py/splurge-safe-io.svg)](https://pypi.org/project/splurge-safe-io/)
[![Python versions](https://img.shields.io/pypi/pyversions/splurge-safe-io.svg)](https://pypi.org/project/splurge-safe-io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

[![CI](https://github.com/jim-schilling/splurge-safe-io/actions/workflows/ci-quick-test.yml/badge.svg)](https://github.com/jim-schilling/splurge-safe-io/actions/workflows/ci-quick-test.yml)
[![Coverage](https://img.shields.io/badge/coverage-93%25-brightgreen.svg)](https://github.com/jim-schilling/splurge-safe-io)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![mypy](https://img.shields.io/badge/mypy-checked-black)](https://mypy-lang.org/)


A small, secure, and deterministic text file I/O helper library.

Key features

- Deterministic newline normalization (LF) for text reads/writes.
- Secure path validation utilities to avoid traversal and dangerous characters.
- Streaming reader with incremental decoding and a safe fallback for tricky encodings.
- Clear, small exception hierarchy for stable error handling.

Quick start

```py
from splurge_safe_io.safe_text_file_reader import SafeTextFileReader
from splurge_safe_io.safe_text_file_writer import open_safe_text_writer

# Read lines
reader = SafeTextFileReader('data.csv')
rows = reader.readlines()

# Write via context manager
with open_safe_text_writer('out.txt') as buf:
    buf.write('\n'.join(['one','two','three']))
```


> **⚠️ BREAKING CHANGE for v2025.1.0:** `SafeTextFileReader.read()` now returns a `str` containing the entire normalized file content instead of a `list[str]` of lines. Use `SafeTextFileReader.readlines()` to get a list of lines.


See `docs/README-DETAILS.md` for a complete guide and usage examples.
