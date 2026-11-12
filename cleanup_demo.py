"""One synthetic, agreed-schema CSV demonstration. No network or client files."""
from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import date
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HEADERS = ["Item_ID", "Item_Name", "Category", "Quantity", "Unit_Price_CAD", "Stock_Date", "Supplier_Note"]
CATEGORIES = {"office": "Office", "kitchen": "Kitchen", "storage": "Storage"}
REQUIRED = HEADERS[:-1]


def read_input(path: Path) -> list[list[str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.reader(handle, strict=True))
    if not rows or rows[0] != HEADERS:
        raise ValueError("Expected the seven agreed inventory headers in order")
    data = rows[1:]
    if len(data) > 100:
        raise ValueError("One file, at most 100 data rows (header excluded)")
    if any(len(row) != len(HEADERS) for row in data):
        raise ValueError("Every data record must have exactly seven fields")
    return data


def normalise(column: str, value: str) -> str:
    value = value.strip()
    if column == "Category":
        return CATEGORIES.get(value.casefold(), value)
    if column == "Quantity" and re.fullmatch(r"[0-9]+", value):
        return str(int(value))
    if column == "Unit_Price_CAD" and re.fullmatch(r"[0-9]+(?:\.[0-9]{1,2})?", value):
        return format(Decimal(value), ".2f")
    if column == "Stock_Date" and re.fullmatch(r"\d{4}[-/]\d{2}[-/]\d{2}", value):
        try:
            return date.fromisoformat(value.replace("/", "-")).isoformat()
        except ValueError:
            pass
    return value


def clean_rows(rows: list[list[str]]) -> tuple[list[list[str]], dict]:
    if len(rows) > 100 or any(len(row) != len(HEADERS) for row in rows):
        raise ValueError("Expected no more than 100 seven-field data records")
    output, removed, changes, provenance, flags = [], [], [], [], []
    seen = {}
    for source_row, row in enumerate(rows, 1):
        if all(not value.strip() for value in row):
            removed.append({"source_row": source_row, "reason": "fully_blank"})
            continue
        key = tuple(row)
        if key in seen:
            removed.append({"source_row": source_row, "reason": "exact_duplicate", "duplicate_of": seen[key]})
            continue
        seen[key] = source_row
        cleaned = [normalise(column, value) for column, value in zip(HEADERS, row)]
        output.append(cleaned)
        output_row = len(output)
        provenance.append({"output_row": output_row, "source_row": source_row})
        for column, before, after in zip(HEADERS, row, cleaned):
            if before != after:
                changes.append({"source_row": source_row, "output_row": output_row,
                                "column": column, "before": before, "after": after})
        for column, value in zip(HEADERS, cleaned):
            reason = None
            if column in REQUIRED and not value:
                reason = "missing_value_preserved"
            elif column == "Stock_Date" and value:
                try:
                    date.fromisoformat(value)
                except ValueError:
                    reason = "unresolved_date_preserved"
            elif column == "Category" and value and value not in CATEGORIES.values():
                reason = "unmapped_category_preserved"
            if reason:
                flags.append({"source_row": source_row, "output_row": output_row,
                              "column": column, "value": value, "reason": reason})
    groups = {}
    for output_row, row in enumerate(output, 1):
        groups.setdefault(tuple(row), []).append(output_row)
    for group in groups.values():
        if len(group) > 1:
            for output_row in group:
                flags.append({"source_row": provenance[output_row - 1]["source_row"],
                              "output_row": output_row, "reason": "normalised_match_retained",
                              "matching_output_rows": group})
    summary = {"input_data_rows": len(rows), "output_data_rows": len(output),
               "fully_blank_rows_removed": sum(x["reason"] == "fully_blank" for x in removed),
               "exact_duplicate_rows_removed": sum(x["reason"] == "exact_duplicate" for x in removed),
               "cells_changed": len(changes), "review_flags": len(flags)}
    return output, {"schema_version": 1, "synthetic_demonstration": True,
                    "row_numbering": "1-based data records; header excluded", "summary": summary,
                    "removed_rows": removed, "provenance": provenance,
                    "cell_changes": changes, "review_flags": flags}


def write_demo(root: Path = ROOT) -> dict:
    source = root / "synthetic_input.csv"
    output = root / "cleaned_output.csv"
    rows = read_input(source)
    cleaned, audit = clean_rows(rows)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(HEADERS)
        writer.writerows(cleaned)
    audit["sha256"] = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in (source, output)}
    (root / "change_log.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    lines = ["# Synthetic inventory cleanup - change log", "",
             "Original demonstration only. No customer data, paid order or earnings.", "",
             "Data-record numbers below exclude the header.", "", "## Measured result", ""]
    lines += [f"- {key}: {value}" for key, value in audit["summary"].items()]
    lines += ["", "## Agreed rules", "",
              "Remove fully blank records and raw exact duplicates; keep the first occurrence and original order.",
              "Trim field edges, map office/kitchen/storage to consistent category labels, display integer quantities",
              "without padding, display CAD prices to two decimals, and change only valid YYYY/MM/DD dates to ISO.",
              "Item IDs stay text with leading zeroes. Preserve missing values, internal note spacing, ambiguous",
              "dates, unknown categories and records that match only after normalisation. Flag these for review.",
              "Blank optional notes need no review. No replacement values are invented.", "", "## Removed records", ""]
    for entry in audit["removed_rows"]:
        suffix = f"; identical to source record {entry['duplicate_of']}" if "duplicate_of" in entry else ""
        lines.append(f"- Source record {entry['source_row']}: {entry['reason']}{suffix}.")
    lines += ["", "## Cell changes", "", "| Source record | Column | Before (JSON string) | After (JSON string) |",
              "| --- | --- | --- | --- |"]
    for entry in audit["cell_changes"]:
        lines.append(f"| {entry['source_row']} | {entry['column']} | `{json.dumps(entry['before'])}` | `{json.dumps(entry['after'])}` |")
    lines += ["", "## Review flags - deliberately unresolved", ""]
    lines += [f"- Source record {entry['source_row']}, output record {entry['output_row']}: "
              f"{entry['reason']}" + (f" ({entry['column']})" if "column" in entry else "") + "."
              for entry in audit["review_flags"]]
    lines += ["", "The machine-readable change_log.json includes every retained row's source, exact cell values",
              "and SHA-256 fingerprints of input/output. Open/import Item_ID as Text in Excel; this CSV",
              "demonstration does not claim desktop Excel acceptance or native XLSX formatting.", ""]
    (root / "CHANGELOG.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return audit


if __name__ == "__main__":
    print(json.dumps(write_demo()["summary"], indent=2))
