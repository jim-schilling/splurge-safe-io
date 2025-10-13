# splurge-safe-io — Detailed Usage Guide

This document provides a detailed walkthrough of `splurge-safe-io` usage, examples, configuration options, and links to the API reference.

Overview

`splurge-safe-io` aims to provide a small, well-tested set of helpers for reading and writing text files in a deterministic, secure manner.

Why use this library?

- Avoid platform-dependent newline behavior by decoding and normalizing newlines consistently.
- Simplify error handling with a small, documented exception hierarchy.
- Validate paths defensively to avoid path traversal and dangerous characters.

Contents

- Installation
- Quick start
- Detailed examples
- Exception contract and how to inspect the original exception
- Link to API reference

Installation

Install from source or add to your project path. (No published package yet.)

Quick start

```py
from splurge_safe_io.safe_text_file_reader import SafeTextFileReader
from splurge_safe_io.safe_text_file_writer import open_safe_text_writer

r = SafeTextFileReader('example.txt')
print(r.read())

with open_safe_text_writer('out.txt') as buf:
    buf.write('a\n b\n')

Small usage: skipping empty/whitespace-only lines

```py
from splurge_safe_io.safe_text_file_reader import SafeTextFileReader

# example.txt contains blank lines and whitespace-only lines
r = SafeTextFileReader('example.txt', skip_empty_lines=True)
for chunk in r.read_as_stream():
    for line in chunk:
        print(line)

# Quick preview returning first 5 non-empty lines
preview = r.preview(5)
print(preview)
```
```

Detailed examples

- Using `skip_header_lines` and `skip_footer_lines` in `SafeTextFileReader`.
- Streaming with `read_as_stream()` for large files.
- Using `PathValidator.validate_path()` to enforce safe paths within a base directory.

Notes / gotchas:

- `SafeTextFileReader` defaults to `strip=False` to avoid surprising trimming of lines; pass `strip=True` when you want whitespace removed.
- The streaming reader performs raw byte reads using a `buffer_size` (default 8192 bytes) and yields up to `chunk_size` lines per yielded list. For most workloads the defaults are sensible; tune `buffer_size` only if you have specific performance needs.
- `PathValidator` supports registering pre-resolution policies via `PathValidator.register_pre_resolution_policy(policy)`. See `docs/api/API-REFERENCE.md` for a short reference to the helper methods.
 - The streaming reader performs raw byte reads using a `buffer_size` (default 8192 bytes) and yields up to `chunk_size` lines per yielded list. The library enforces a minimum buffer size (`MIN_BUFFER_SIZE = 4096`) so providing a smaller `buffer_size` will be rounded up to that minimum.

Exception contract

All high-level I/O errors are mapped to `SplurgeSafeIo*` exceptions. Each mapped exception preserves the original builtin in the
`original_exception` attribute and via exception chaining (`from`). When raising library exceptions programmatically, prefer passing
the original builtin via the constructor (``original_exception=<exc>``) and use ``raise ... from <exc>`` to retain chaining.
See `API-REFERENCE.md` for the canonical mapping.

Links

- Full API reference: `docs/api/API-REFERENCE.md`
- Change log: `CHANGELOG.md` (if present)
