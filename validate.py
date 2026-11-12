"""Independent semantic checks of the delivered CSV and its row/cell receipts."""
from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import date
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def validate(root: Path = ROOT) -> dict:
    def require(condition: bool, message: str) -> None:
        if not condition:
            raise ValueError(message)
    def read(name: str) -> list[list[str]]:
        with (root / name).open(encoding="utf-8-sig", newline="") as handle:
            return list(csv.reader(handle, strict=True))

    source_file, output_file = read("synthetic_input.csv"), read("cleaned_output.csv")
    headers, source, output = source_file[0], source_file[1:], output_file[1:]
    require(headers == ["Item_ID", "Item_Name", "Category", "Quantity", "Unit_Price_CAD", "Stock_Date", "Supplier_Note"], "Wrong source schema")
    require(output_file[0] == headers, "Headers changed")
    require(len(source) <= 100 and all(len(row) == 7 for row in source + output), "Row limit/width failed")
    audit = json.loads((root / "change_log.json").read_text(encoding="utf-8"))
    for name in ("synthetic_input.csv", "cleaned_output.csv"):
        require(audit["sha256"][name] == hashlib.sha256((root / name).read_bytes()).hexdigest(), f"Hash mismatch: {name}")
    retained, removed, first = [], [], {}
    for number, row in enumerate(source, 1):
        if all(not value.strip() for value in row):
            removed.append({"source_row": number, "reason": "fully_blank"})
        elif tuple(row) in first:
            removed.append({"source_row": number, "reason": "exact_duplicate", "duplicate_of": first[tuple(row)]})
        else:
            first[tuple(row)] = number
            retained.append(number)
    require(audit["removed_rows"] == removed, "Removal receipt differs from source")
    require(len(output) == len(retained), "Lost or invented records")
    require(audit["provenance"] == [{"output_row": i, "source_row": n} for i, n in enumerate(retained, 1)], "Row provenance/order changed")
    changes, expected_flags = [], []
    for output_number, (source_number, after) in enumerate(zip(retained, output), 1):
        before = source[source_number - 1]
        for col, old, new in zip(headers, before, after):
            old_trimmed = old.strip()
            require(bool(new) == bool(old_trimmed), f"Missing value invented or existing value erased: {source_number}/{col}")
            if col in ("Item_ID", "Item_Name", "Supplier_Note"):
                require(new == old_trimmed, f"Text changed beyond edge trimming: {source_number}/{col}")
            elif col == "Category":
                allowed = {"office": "Office", "kitchen": "Kitchen", "storage": "Storage"}
                require(new == allowed.get(old_trimmed.casefold(), old_trimmed), "Unapproved category")
            elif col == "Quantity":
                expected = str(int(old_trimmed)) if re.fullmatch(r"[0-9]+", old_trimmed) else old_trimmed
                require(new == expected, "Quantity changed")
            elif col == "Unit_Price_CAD":
                supported = re.fullmatch(r"[0-9]+(?:\.[0-9]{1,2})?", old_trimmed)
                require(new == (format(Decimal(old_trimmed), ".2f") if supported else old_trimmed), "Price changed")
            elif col == "Stock_Date":
                expected = old_trimmed
                if re.fullmatch(r"\d{4}[-/]\d{2}[-/]\d{2}", old_trimmed):
                    try:
                        expected = date.fromisoformat(old_trimmed.replace("/", "-")).isoformat()
                    except ValueError:
                        pass
                require(new == expected, "Unapproved date conversion")
            if old != new:
                changes.append({"source_row": source_number, "output_row": output_number, "column": col, "before": old, "after": new})
            reason = None
            if col != "Supplier_Note" and not new:
                reason = "missing_value_preserved"
            elif col == "Stock_Date" and new:
                try:
                    date.fromisoformat(new)
                except ValueError:
                    reason = "unresolved_date_preserved"
            elif col == "Category" and new and new not in ("Office", "Kitchen", "Storage"):
                reason = "unmapped_category_preserved"
            if reason:
                expected_flags.append({"source_row": source_number, "output_row": output_number, "column": col, "value": new, "reason": reason})
    groups = {}
    for number, row in enumerate(output, 1):
        groups.setdefault(tuple(row), []).append(number)
    for group in groups.values():
        if len(group) > 1:
            for number in group:
                expected_flags.append({"source_row": retained[number - 1], "output_row": number, "reason": "normalised_match_retained", "matching_output_rows": group})
    require(audit["cell_changes"] == changes, "Cell change receipt incomplete or false")
    require(audit["review_flags"] == expected_flags, "Review flags incomplete or false")
    summary = {"input_data_rows": len(source), "output_data_rows": len(output),
               "fully_blank_rows_removed": sum(x["reason"] == "fully_blank" for x in removed),
               "exact_duplicate_rows_removed": sum(x["reason"] == "exact_duplicate" for x in removed),
               "cells_changed": len(changes), "review_flags": len(expected_flags)}
    require(audit["summary"] == summary, "Summary counts differ")
    return {"status": "PASS", "checks": ["schema and 100-row limit", "SHA-256 file integrity", "exact-only removals", "stable row provenance", "no invented or erased values", "approved formats only", "complete cell change log", "complete unresolved review flags", "summary reconciliation"], "summary": summary}


if __name__ == "__main__":
    print(json.dumps(validate(), indent=2))
