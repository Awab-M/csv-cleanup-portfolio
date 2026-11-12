import csv
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from cleanup_demo import HEADERS, ROOT, clean_rows, normalise, read_input, write_demo
from validate import validate


EXPECTED = [
    ["0001", "Grid Notebook", "Office", "10", "4.50", "2026-11-01", ""],
    ["0002", "Desk Marker", "Office", "6", "2.00", "2026-11-02", "Sample only"],
    ["0003", "Binder Clips", "Office", "12", "3.50", "2026-11-03", ""],
    ["0004", "Stoneware Mug", "Kitchen", "4", "8.00", "2026-11-03", ""],
    ["0005", "Label Roll", "Office", "", "6.75", "2026-11-04", "Quantity not supplied"],
    ["0006", "Cable Box", "Storage", "2", "18.00", "2026-11-04", 'Demo, size "M"'],
    ["0007", "Tea Towel", "Kitchen", "8", "5.00", "11/04/2026", "Date needs owner confirmation"],
    ["0008", "Drawer Tray", "Storage", "3", "15.50", "2026-11-05", ""],
    ["0009", "Sample Bundle", "Mixed", "1", "11.25", "2026-11-05", "Category needs owner confirmation"],
    ["0010", "Refill Pad", "Office", "0", "0.00", "2026-11-06", "Keep  two  spaces"],
    ["0011", "Sheet Pack", "Office", "5", "7.00", "2026-11-06", ""],
    ["0002", "Desk Marker", "Office", "6", "2.00", "2026-11-02", "Sample only"],
    ["0012", "Pen Cup", "Office", "9", "", "2026-11-07", "Price not supplied"],
    ["0013", "Foam Tray", "Storage", "4", "9.95", "", "Date not supplied"],
]


class CleanupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copyfile(ROOT / "synthetic_input.csv", self.root / "synthetic_input.csv")

    def test_golden_output_every_cell_and_order(self):
        output, audit = clean_rows(read_input(ROOT / "synthetic_input.csv"))
        self.assertEqual(output, EXPECTED)
        self.assertEqual(audit["summary"]["input_data_rows"], 18)
        self.assertEqual(audit["summary"]["output_data_rows"], 14)
        self.assertEqual(audit["summary"]["review_flags"], 7)

    def test_raw_exact_duplicates_only(self):
        _, audit = clean_rows(read_input(ROOT / "synthetic_input.csv"))
        self.assertEqual(audit["removed_rows"], [
            {"source_row": 3, "reason": "exact_duplicate", "duplicate_of": 1},
            {"source_row": 4, "reason": "fully_blank"},
            {"source_row": 10, "reason": "fully_blank"},
            {"source_row": 13, "reason": "exact_duplicate", "duplicate_of": 6},
        ])

    def test_near_duplicates_retained_and_flagged(self):
        output, audit = clean_rows(read_input(ROOT / "synthetic_input.csv"))
        self.assertEqual(output[1], output[11])
        flags = [x for x in audit["review_flags"] if x["reason"] == "normalised_match_retained"]
        self.assertEqual([x["source_row"] for x in flags], [2, 16])

    def test_identifiers_and_internal_note_spacing_preserved(self):
        self.assertEqual(normalise("Item_ID", " 0001 "), "0001")
        self.assertEqual(normalise("Supplier_Note", " Keep  two  spaces "), "Keep  two  spaces")

    def test_missing_values_and_zero_are_distinct(self):
        output, _ = clean_rows(read_input(ROOT / "synthetic_input.csv"))
        self.assertEqual(output[4][3], "")
        self.assertEqual(output[12][4], "")
        self.assertEqual(output[13][5], "")
        self.assertEqual(output[9][3:5], ["0", "0.00"])

    def test_ambiguous_and_invalid_dates_not_guessed(self):
        for value in ("11/04/2026", "2026/02/30", "2026-13-01", "not supplied"):
            self.assertEqual(normalise("Stock_Date", value), value)
        self.assertEqual(normalise("Stock_Date", "2028/02/29"), "2028-02-29")

    def test_precision_and_unsupported_numeric_text_not_changed(self):
        for value in ("12.345", "1,234.50", "unknown", "-2", "=1+1"):
            self.assertEqual(normalise("Unit_Price_CAD", value), value)
        self.assertEqual(normalise("Unit_Price_CAD", "99999999999999999999.99"), "99999999999999999999.99")

    def test_unknown_category_not_invented(self):
        self.assertEqual(normalise("Category", " Mixed "), "Mixed")

    def test_100_row_boundary_accepted_101_rejected(self):
        row = ["1", "Item", "Office", "1", "1", "2026-11-01", ""]
        clean_rows([row] * 100)
        with self.assertRaisesRegex(ValueError, "100"):
            clean_rows([row] * 101)

    def test_header_and_ragged_records_rejected(self):
        path = self.root / "invalid.csv"
        path.write_text("wrong,header\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "headers"):
            read_input(path)
        path.write_text(",".join(HEADERS) + "\n1,short\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "seven fields"):
            read_input(path)

    def test_utf8_bom_unicode_and_quoted_fields_round_trip(self):
        row = ["0001", "Caf\u00e9 mug", "Kitchen", "1", "2", "2026-11-01", 'Demo, size "M"\nsecond line']
        with (self.root / "synthetic_input.csv").open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerows([HEADERS, row])
        write_demo(self.root)
        self.assertEqual(validate(self.root)["status"], "PASS")
        self.assertEqual(read_input(self.root / "cleaned_output.csv")[0][1], "Caf\u00e9 mug")
        self.assertEqual(read_input(self.root / "cleaned_output.csv")[0][6], row[6])

    def test_rebuild_deterministic_and_original_untouched(self):
        before = (self.root / "synthetic_input.csv").read_bytes()
        write_demo(self.root)
        names = ("cleaned_output.csv", "change_log.json", "CHANGELOG.md")
        first = {name: (self.root / name).read_bytes() for name in names}
        write_demo(self.root)
        self.assertEqual(first, {name: (self.root / name).read_bytes() for name in names})
        self.assertEqual(before, (self.root / "synthetic_input.csv").read_bytes())
        self.assertEqual(validate(self.root)["status"], "PASS")

    def mutate_output(self, mutation):
        write_demo(self.root)
        path = self.root / "cleaned_output.csv"
        with path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.reader(handle))
        mutation(rows)
        with path.open("w", encoding="utf-8", newline="") as handle:
            csv.writer(handle, lineterminator="\n").writerows(rows)
        audit_path = self.root / "change_log.json"
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        audit["sha256"]["cleaned_output.csv"] = hashlib.sha256(path.read_bytes()).hexdigest()
        audit_path.write_text(json.dumps(audit), encoding="utf-8")

    def test_validator_rejects_invented_missing_quantity_even_with_new_hash(self):
        self.mutate_output(lambda rows: rows[5].__setitem__(3, "5"))
        with self.assertRaisesRegex(ValueError, "invented"):
            validate(self.root)

    def test_validator_rejects_wrong_price_even_with_new_hash(self):
        self.mutate_output(lambda rows: rows[1].__setitem__(4, "45.00"))
        with self.assertRaisesRegex(ValueError, "Price changed"):
            validate(self.root)

    def test_validator_rejects_dropped_near_duplicate(self):
        self.mutate_output(lambda rows: rows.pop(12))
        with self.assertRaisesRegex(ValueError, "Lost or invented records"):
            validate(self.root)

    def test_validator_rejects_missing_review_receipt(self):
        write_demo(self.root)
        path = self.root / "change_log.json"
        audit = json.loads(path.read_text(encoding="utf-8"))
        audit["review_flags"].pop()
        path.write_text(json.dumps(audit), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Review flags"):
            validate(self.root)

    def test_validator_rejects_unlogged_change(self):
        write_demo(self.root)
        path = self.root / "change_log.json"
        audit = json.loads(path.read_text(encoding="utf-8"))
        audit["cell_changes"].pop()
        path.write_text(json.dumps(audit), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Cell change receipt"):
            validate(self.root)


if __name__ == "__main__":
    unittest.main(verbosity=2)
