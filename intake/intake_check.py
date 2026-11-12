"""Read-only intake check for ONE buyer file (.csv or .xlsx) against the US$15 Gig scope.

Scope checked: one file, one sheet, up to 100 non-blank data rows (header excluded).
The input is never modified. The report lists counts, column names and row numbers
only; it never echoes cell values, so it is safe to paste into a Fiverr order chat.

Usage:  python -B intake_check.py <file> [--out report.md]
Exit:   0 in scope, 2 out of scope, 1 unreadable/unsupported.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import re
import sys
from pathlib import Path

ROW_LIMIT = 100
DATE_SEP = re.compile(r"^(\d{1,4})[/\-.](\d{1,2})[/\-.](\d{1,4})$")
LEADING_ZERO = re.compile(r"^0\d+$")
NUMBER = re.compile(r"^[+-]?\d+([.,]\d+)?$")
MONEY = re.compile(r"^[\$€£]|[\$€£]$|\d,\d{3}")


class IntakeError(Exception):
    """File cannot be checked (unsupported type or unreadable)."""


def _cell_text(cell) -> str:
    v = cell.value
    if v is None:
        return ""
    if isinstance(v, dt.datetime):
        return v.date().isoformat() if v.time() == dt.time(0) else v.isoformat(sep=" ")
    if isinstance(v, (dt.date, dt.time)):
        return v.isoformat()
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def load_table(path: Path):
    """Return (format, records, notes). records[0] is the header row."""
    ext = path.suffix.lower()
    notes: list[str] = []
    if ext == ".csv":
        raw = path.read_bytes()
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw.decode("cp1252")
            notes.append("File is not UTF-8; read as Windows-1252. Confirm accented characters look right.")
        first = text.split("\n", 1)[0]
        delim = max(",;\t|", key=first.count)
        if delim != ",":
            notes.append(f"Delimiter is {delim!r}, not a comma.")
        records = [list(r) for r in csv.reader(io.StringIO(text, newline=""), delimiter=delim)]
        return "csv", records, notes
    if ext == ".xlsx":
        import openpyxl

        wb = openpyxl.load_workbook(path, data_only=False)
        ws = wb.worksheets[0]
        if len(wb.worksheets) > 1:
            notes.append(f"Workbook has {len(wb.worksheets)} sheets; only the first ('{ws.title}') is in scope.")
        if ws.merged_cells.ranges:
            notes.append(f"{len(ws.merged_cells.ranges)} merged cell range(s); merged cells must be unmerged or explained.")
        typed_dates = 0
        records = []
        for row in ws.iter_rows():
            typed_dates += sum(isinstance(c.value, (dt.date, dt.datetime)) for c in row)
            records.append([_cell_text(c) for c in row])
        if typed_dates:
            notes.append(f"{typed_dates} cell(s) are true Excel dates (shown here as YYYY-MM-DD).")
        return "xlsx", records, notes
    if ext in (".xlsm", ".xlsb", ".xls"):
        raise IntakeError(f"{ext} is not accepted (macros/legacy format). Ask the buyer to export .xlsx or .csv.")
    raise IntakeError(f"Unsupported file type {ext!r}. Accepted: .csv, .xlsx.")


def _date_class(value: str) -> str | None:
    m = DATE_SEP.match(value)
    if not m:
        return None
    a, b, c = (int(x) for x in m.groups())
    if len(m.group(1)) == 4:
        return "year-first"
    if len(m.group(3)) not in (2, 4) or a == 0 or b == 0:
        return None
    if a > 12 and b <= 12:
        return "day-first"
    if b > 12 and a <= 12:
        return "month-first"
    if a <= 12 and b <= 12:
        return "same-either-way" if a == b else "ambiguous"
    return None


def profile(path: Path) -> dict:
    fmt, records, notes = load_table(path)
    if not records:
        raise IntakeError("File is empty.")
    while len(records) > 1 and not any(x.strip() for x in records[-1]):
        records.pop()  # trailing empty rows are spreadsheet padding, not data
    ragged = []
    if fmt == "csv":
        ragged = [n for n, r in enumerate(records, 1) if any(x.strip() for x in r) and len(r) != len(records[0])]
    width = max(len(r) for r in records)
    records = [r + [""] * (width - len(r)) for r in records]
    keep = [i for i in range(width) if any(r[i].strip() for r in records)]
    header = [records[0][i].strip() for i in keep]
    body = [(n, [r[i] for i in keep]) for n, r in enumerate(records[1:], 2)]

    header_issues = []
    if any(not h for h in header):
        header_issues.append("One or more columns have no header name.")
    if len({h.casefold() for h in header if h}) != len([h for h in header if h]):
        header_issues.append("Two or more columns share the same header name.")

    blank_rows = [n for n, r in body if not any(x.strip() for x in r)]
    data = [(n, r) for n, r in body if any(x.strip() for x in r)]
    seen: set[tuple] = set()
    dup_rows = []
    for n, r in data:
        key = tuple(r)
        if key in seen:
            dup_rows.append(n)
        seen.add(key)

    columns = []
    for ci, name in enumerate(header):
        vals = [(n, r[ci]) for n, r in data]
        filled = [(n, v) for n, v in vals if v.strip()]
        forms: dict[str, set[str]] = {}
        for _, v in filled:
            if not NUMBER.match(v.strip()):
                forms.setdefault(v.strip().casefold(), set()).add(v.strip())
        classes: dict[str, int] = {}
        ambiguous = []
        for n, v in filled:
            c = _date_class(v.strip())
            if c:
                classes[c] = classes.get(c, 0) + 1
                if c == "ambiguous":
                    ambiguous.append(n)
        columns.append({
            "name": name or f"(unnamed column {ci + 1})",
            "blank_cells": len(vals) - len(filled),
            "edge_whitespace_cells": sum(v != v.strip() for _, v in filled),
            "case_variant_groups": sum(len(s) > 1 for s in forms.values()),
            "leading_zero_cells": sum(bool(LEADING_ZERO.match(v.strip())) for _, v in filled),
            "currency_or_thousands_cells": sum(bool(MONEY.search(v.strip())) for _, v in filled),
            "date_classes": classes,
            "ambiguous_date_rows": ambiguous,
            "formula_like_rows": [n for n, v in filled
                                  if v.strip()[0] in "=@" or (v.strip()[0] in "+-" and not NUMBER.match(v.strip()))],
        })

    in_scope = len(data) <= ROW_LIMIT and not header_issues and not ragged
    result = {
        "file": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "format": fmt,
        "row_limit": ROW_LIMIT,
        "data_rows": len(data),
        "scope": "IN_SCOPE" if in_scope else ("OVER_ROW_LIMIT" if len(data) > ROW_LIMIT else "NEEDS_STRUCTURE_FIX"),
        "column_count": len(header),
        "blank_rows": blank_rows,
        "exact_duplicate_rows": dup_rows,
        "ragged_rows": ragged,
        "header_issues": header_issues,
        "file_notes": notes,
        "columns": columns,
    }
    result["questions"] = questions(result)
    return result


def questions(p: dict) -> list[str]:
    q = []
    if p["scope"] == "OVER_ROW_LIMIT":
        q.append(f"The file has {p['data_rows']} data rows; the Basic package covers {p['row_limit']}. "
                 "Which rows should I work on, or would you like a custom offer for the full file?")
    if p["exact_duplicate_rows"]:
        q.append(f"{len(p['exact_duplicate_rows'])} row(s) are exact copies of an earlier row "
                 f"(rows {_rows(p['exact_duplicate_rows'])}). OK to remove them and keep the first copy?")
    if p["blank_rows"]:
        q.append(f"{len(p['blank_rows'])} fully blank row(s) (rows {_rows(p['blank_rows'])}). OK to remove them?")
    if p["ragged_rows"]:
        q.append(f"Rows {_rows(p['ragged_rows'])} have a different number of fields than the header. "
                 "Can you confirm which column each value belongs to?")
    for issue in p["header_issues"]:
        q.append(issue + " What should the column names be?")
    for c in p["columns"]:
        n = c["name"]
        if c["ambiguous_date_rows"] or len(c["date_classes"]) > 1:
            q.append(f"Column '{n}' mixes or has unclear date formats"
                     + (f" (rows {_rows(c['ambiguous_date_rows'])} could be day-first or month-first)" if c["ambiguous_date_rows"] else "")
                     + ". Is the source day-first or month-first, and which output format do you want (e.g. YYYY-MM-DD)?")
        if c["leading_zero_cells"]:
            q.append(f"Column '{n}' has {c['leading_zero_cells']} value(s) starting with 0. "
                     "Is it an ID/code (keep the zeros as text) or a number (drop them)?")
        if c["case_variant_groups"]:
            q.append(f"Column '{n}' has {c['case_variant_groups']} value(s) written with different capitalisation. "
                     "Which spelling should be the standard?")
        if c["blank_cells"]:
            q.append(f"Column '{n}' has {c['blank_cells']} blank cell(s). Leave them blank (default), or is there a rule?")
        if c["currency_or_thousands_cells"]:
            q.append(f"Column '{n}' has currency symbols or thousands separators. Keep them, or plain numbers with two decimals?")
        if c["formula_like_rows"]:
            q.append(f"Column '{n}' has formula-like content in rows {_rows(c['formula_like_rows'])}. "
                     "I will treat it as text and not run it. Is that expected?")
    return q


def _rows(rows: list[int]) -> str:
    return ", ".join(map(str, rows[:12])) + (" ..." if len(rows) > 12 else "")


def render(p: dict) -> str:
    out = [f"# Intake check: {p['file']}", "",
           f"- Format: {p['format']}; columns: {p['column_count']}; data rows: {p['data_rows']} (limit {p['row_limit']})",
           f"- Scope result: **{p['scope']}**",
           f"- Fully blank rows: {len(p['blank_rows'])}; exact duplicate rows: {len(p['exact_duplicate_rows'])}",
           f"- Original file fingerprint (SHA-256): `{p['sha256']}`", ""]
    out += [f"- Note: {n}" for n in p["file_notes"]]
    out += ["", "Row numbers are spreadsheet rows (header is row 1). No cell values are shown.", "",
            "## Questions before I start", ""]
    out += [f"{i}. {q}" for i, q in enumerate(p["questions"], 1)] or ["None. The file is ready to clean with the default rules."]
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("file")
    ap.add_argument("--out", help="write the Markdown report here")
    a = ap.parse_args(argv)
    try:
        p = profile(Path(a.file))
    except (IntakeError, OSError) as e:
        print(f"CANNOT CHECK: {e}", file=sys.stderr)
        return 1
    if a.out:
        Path(a.out).write_text(render(p), encoding="utf-8", newline="\n")
    print(json.dumps({k: v for k, v in p.items() if k != "columns"}, indent=2))
    return 0 if p["scope"] == "IN_SCOPE" else 2


if __name__ == "__main__":
    sys.exit(main())
