# CLAUDE.md

Public portfolio repo proving a small CSV-cleanup service. It is evidence, so every claim in the docs must match what the code and fixtures actually do. Stdlib Python 3 only (openpyxl is needed solely for .xlsx intake and its tests).

## Commands (run from repo root)
- `python -B cleanup_demo.py` rebuilds `cleaned_output.csv`, `change_log.json`, `CHANGELOG.md` from `synthetic_input.csv`; must leave `git status` clean.
- `python -B -m unittest -v test_cleanup` runs the 21 cleaner/validator tests.
- `python -B validate.py` runs the independent checker (prints PASS).
- `python -B -m unittest discover -s intake` runs the 16 intake tests.
- `python -B intake/intake_check.py FILE.csv --out report.md` runs the pre-order check (exit 0 in scope, 2 out of scope, 1 unreadable).

## Layout
- `cleanup_demo.py`: cleaner for the fixed 7-column inventory schema, max 100 data rows.
- `validate.py`: re-derives the allowed result from the input and checks output, receipts and SHA-256s.
- `synthetic_input.csv`, `cleaned_output.csv`, `change_log.json`, `CHANGELOG.md`: fixture and generated artifacts (do not hand-edit).
- `intake/`: read-only buyer file check plus `sample_intake_report.md` (generated from the fixture).
- `docs/`: case study. `portfolio_proof.png`: README image. `.gitattributes` (`* -text`) keeps bytes exact for the hashes.

## Conventions
- Row numbers are 1-based data records, header excluded (intake reports use spreadsheet rows, header = row 1).
- Duplicates are exact raw matches only, keeping the first. Near-matches are kept and flagged.
- Never invent values; unknown or ambiguous data is preserved and flagged.
- Intake output shows counts, column names and row numbers, never cell values.
- Files are written with `\n` line endings and UTF-8.

## Invariants
- Regenerating the demo is deterministic; `validate.py` must pass.
- README/CHANGELOG numbers (18 in, 14 out, 28 changes, 7 flags, test counts) must match real output. Update docs when test counts change.
- Everything is synthetic: no client data, testimonials, income claims or invented metrics. Do not alter pricing or contact details in README without the owner's say-so.
- If `synthetic_input.csv` changes, regenerate artifacts and `intake/sample_intake_report.md`.

## Known gaps (priority order)
1. Demo date rule covers only YYYY/MM/DD and YYYY-MM-DD; no other formats are converted.
2. `.xlsx` intake is tested only with openpyxl, not desktop Excel; the demo cleaner handles CSV only.
3. The case study links to GitHub URLs, so it cannot be verified offline.
