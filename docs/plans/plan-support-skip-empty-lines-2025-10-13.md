# Plan: Support skip_empty_lines in SafeTextFileReader

Date: 2025-10-13
Author: (planned change) — implementation checklist

Goal
-----
Add a new optional constructor parameter `skip_empty_lines: bool = False` to
`SafeTextFileReader` which, when enabled, removes whitespace-only lines from
all read operations.

Chosen semantics (Option A - preferred)
--------------------------------------
- `skip_empty_lines=True` means: treat a line as empty if `line.strip() == ""`.
  I.e., whitespace-only lines are considered empty and removed.
- Apply header/footer skipping first (positional on raw logical lines), then
  apply empty-line filtering to the remaining lines.
- The behavior affects `read()`, `read_as_stream()`, and `preview()`.
- `line_count()` will honor `skip_empty_lines` (counts only non-empty lines when
  enabled).
- `strip` remains a separate option that controls whether returned lines are
  stripped; emptiness is determined using `str.strip()` regardless of the
  `strip` setting (consistent, predictable behavior).

High-level impact
-----------------
- Invasiveness: Low–Moderate. Changes are localized to `SafeTextFileReader` but
  must be carefully applied to both full-read and streaming code paths.
- Tests: Add/modify unit tests to cover filtering semantics, chunk boundaries,
  preview early-stop, and `line_count()` behavior.
- Docs: Update API reference and CHANGELOG.

Checklist (step-by-step)
------------------------
Each checklist item is actionable and includes the files to change and the
reasoning/testing notes. Mark items as done as you implement them.

1. Planning & safety checks
   - [ ] Read current implementation of `SafeTextFileReader` (file: `splurge_safe_io/safe_text_file_reader.py`).
     - Verify where `read()`, `read_as_stream()`, `preview()`, and `line_count()` currently implement header/footer logic and chunking.
   - [ ] Search tests for assumptions around empty lines to identify places that will need updating: `grep -n "empty" tests || true` (manual review).

2. API change (non-breaking)
   - [ ] Add a new keyword-only constructor parameter in `SafeTextFileReader.__init__`:
     - Parameter: `skip_empty_lines: bool = False`
     - Update constructor docstring to document semantics and interaction with `strip` and header/footer.
  - [x] Store as `self._skip_empty_lines` and expose read-only property `skip_empty_lines`.

3. Full-read path (`read()`)
  - [x] Update `read()` implementation to perform filtering in this order:
     1. Perform full decode and split into logical lines (existing behavior).
     2. Apply header skip: slice off `skip_header_lines` from the start.
     3. Apply footer skip: slice off `skip_footer_lines` from the end (existing behavior — ensure this uses raw logical lines before filtering).
     4. If `self.skip_empty_lines` is True, remove lines where `ln.strip() == ""`.
     5. Finally, apply `strip` to returned lines if `self.strip` is True (only to remaining lines).
  - [x] Ensure returned line indices and ordering are preserved after filtering.

4. Streaming path (`read_as_stream()`)
  - [x] Ensure footer buffer creation remains based on raw logical lines (no filtering during buffer collection). The footer buffer is positional and must be computed before empty-line filtering.
  - [x] When yielding a chunk (i.e., the safe-to-emit portion), apply empty-line filtering to that chunk if `self.skip_empty_lines` is True.
  - [x] Avoid yielding empty lists; if filtering would produce an empty chunk, skip yielding that chunk.
  - [x] Carefully adapt preview() (which uses streaming) to count post-filtered lines when stopping early.
  - [x] Ensure generator `.close()` is still called when preview stops early (no resource leak).

5. Preview (`preview()`) behavior
  - [x] Modify `preview()` so its stopping condition counts only non-empty lines when `skip_empty_lines` is True.
  - [x] Ensure preview still uses a temporary reader tuned for early stop (existing pattern): create a temporary SafeTextFileReader configured with `chunk_size=max(max_lines, MIN_CHUNK_SIZE)` and `skip_header_lines=0`/`skip_footer_lines=0` as current design — but remember to pass `skip_empty_lines=self.skip_empty_lines` and `encoding`/`buffer_size` consistently.
  - [x] After collecting enough filtered lines, close the generator safely using `closer = getattr(gen, "close", None)` and call if present.

6. line_count() behavior
  - [x] Change `line_count()` to honor `self.skip_empty_lines`.
     - Small-file path: after `read()` (which already applies filtering), return `len(lines)`.
     - Large-file streaming path: when iterating `read_as_stream()`, sum `len(chunk)` where chunks are already filtered (since read_as_stream() will apply filtering), or apply filtering when counting if you reuse a streaming reader that doesn't filter.
   - [ ] Maintain the `threshold_bytes >= 1 MiB` validation.
   - [ ] Document that `line_count()` honors `skip_empty_lines` in the API docs.

7. Tests — unit tests updates and additions
  - [x] Update `tests/unit/test_safe_text_file_reader.py` to include tests for `skip_empty_lines`:
     - Test: `test_read_skips_whitespace_lines` — set up a file with blank and whitespace-only lines; assert `read()` removes them when `skip_empty_lines=True` and retains them when False.
     - Test: `test_read_preserves_strip_behavior` — with `skip_empty_lines=True` and `strip=False`, ensure whitespace-only lines are removed but non-empty lines preserve whitespace where expected.
     - Test: `test_read_as_stream_filters_empty_lines` — create a file with lines such that chunk boundaries would include empty-only chunks; assert `read_as_stream()` yields only chunks that contain non-empty lines and doesn't yield empty lists.
     - Test: `test_preview_counts_post_filter_lines` — file with many leading empty/whitespace-only lines; `preview(max_lines=N)` should return the first N non-empty lines.
     - Test: `test_footer_and_header_skipping_then_filtering` — ensure header/footer are removed first and then empty-line filtering applied to the rest.
     - Test: `test_line_count_respects_skip_empty_lines_small_and_large` — exercise both small-file and streaming path via monkeypatched `Path.stat` to confirm counts match expectations.
     - Test: `test_preview_closes_filehandle_with_skip_empty_lines` — ensure resource finalization still happens when `preview()` stops early with skip_empty_lines True.
  - [x] Use `monkeypatch.setattr` to fake `Path.stat` and to spy on `_read()` when necessary (consistent with existing tests).
  - [x] Run the updated test file: `pytest -q tests/unit/test_safe_text_file_reader.py` and then full `pytest -q`.

8. Docs & changelog
  - [x] Update `docs/api/API-REFERENCE.md` to document `skip_empty_lines` parameter and semantics (examples and order relative to header/footer/strip). Add note that this affects `line_count()`.
  - [x] Update `CHANGELOG.md` under `[2025.0.5]` with the new option, default behavior, and rationale.

9. Linting, typing, and CI
  - [x] Run `ruff check .` and address any style issues.
  - [x] Run `mypy .` and fix typing issues (if any). Use `getattr(gen, "close", None)` style where needed to satisfy mypy for optional close() attributes.
  - [x] Run full test suite and CI: `pytest -q` and `pytest --cov` (optional coverage check).

10. Performance & edge-case review
    - [ ] Review performance on a large file (multi-GB) in streaming path; confirm that filtering per-chunk doesn't cause excessive memory usage.
    - [ ] Ensure that removing empty lines doesn't create pathological chunking behavior for consumers expecting fixed-size chunks. Document that chunk sizes are advisory and may vary when filtering removes lines.

11. Release prep
  - [x] Bump version (if part of this release plan) and add the changelog entry if not already present.
  - [x] Commit changes with a clear commit message: "Add skip_empty_lines option to SafeTextFileReader; update streaming and tests".
  - [ ] Open a PR against `main` or your release branch and request review.

12. Rollback / mitigation plan
    - [ ] If the change causes an unexpected regression, revert the commit and open a follow-up PR with a narrower change (for example, a dedicated utility function instead of a reader option).
    - [ ] If behavior for `line_count()` should remain absolute (count all logical lines regardless of skip option), revert that specific change and add a new helper method `count_non_empty_lines()`.

Implementation notes / code pointers
----------------------------------
- Files to edit:
  - `splurge_safe_io/safe_text_file_reader.py` (primary)
  - `tests/unit/test_safe_text_file_reader.py` (tests)
  - `docs/api/API-REFERENCE.md` (docs)
  - `CHANGELOG.md` (changelog)
- Key functions/sections to inspect in `safe_text_file_reader.py`:
  - `class SafeTextFileReader.__init__` — add param
  - `def _read(self)` / `def read(self)` — full-read path
  - `def read_as_stream(self)` — streaming path and footer-buffer logic
  - `def preview(self, max_lines=...)` — early-stop logic
  - `def line_count(self, threshold_bytes=...)` — counting behavior
- Existing tests use `monkeypatch.setattr(Path, "stat", ...)` and spies on `_read` — continue this pattern for testing streaming vs small-file paths.

Example command sequence for local work
--------------------------------------
```bash
# run tests and linters during development
ruff check .
mypy .
pytest -q tests/unit/test_safe_text_file_reader.py
pytest -q
```

Estimated effort
----------------
- Implementation: 1–2 hours
- Tests: 1–2 hours
- Docs + changelog: 30–60 minutes
- Total: 3–5 hours (including CI runs and fixes)

Acceptance criteria
-------------------
- `skip_empty_lines` is a documented keyword-only argument with default False.
- `read()`, `read_as_stream()`, and `preview()` behave correctly per the semantics above.
- `line_count()` honors `skip_empty_lines`.
- New unit tests pass and existing tests continue to pass.
- Ruff and mypy pass.

Questions / decision points for implementer
------------------------------------------
- Confirm final decision: we chose Option A (whitespace-only lines are removed via `line.strip() == ""`).
- Confirm `line_count()` should honor `skip_empty_lines` (recommended).

