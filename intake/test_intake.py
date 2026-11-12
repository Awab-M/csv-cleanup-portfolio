"""Tests for intake_check.py. Uses the demo's synthetic CSV as an independent cross-check."""
import hashlib
import tempfile
import unittest
from pathlib import Path

import openpyxl

import intake_check as ic

SYNTH = Path(__file__).resolve().parent.parent / "synthetic_input.csv"


def write(tmp: Path, name: str, text: str, encoding="utf-8") -> Path:
    p = tmp / name
    p.write_bytes(text.encode(encoding))
    return p


class IntakeTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def col(self, p, name):
        return next(c for c in p["columns"] if c["name"] == name)

    def test_synthetic_csv_matches_demo_counts(self):
        before = hashlib.sha256(SYNTH.read_bytes()).hexdigest()
        p = ic.profile(SYNTH)
        self.assertEqual(len(p["blank_rows"]), 2)
        self.assertEqual(len(p["exact_duplicate_rows"]), 2)
        self.assertEqual(p["data_rows"] + len(p["blank_rows"]), 18)
        self.assertEqual(p["scope"], "IN_SCOPE")
        self.assertEqual(p["column_count"], 7)
        self.assertTrue(self.col(p, "Stock_Date")["ambiguous_date_rows"])
        self.assertGreater(self.col(p, "Item_ID")["leading_zero_cells"], 0)
        self.assertGreater(self.col(p, "Category")["case_variant_groups"], 0)
        self.assertEqual(hashlib.sha256(SYNTH.read_bytes()).hexdigest(), before, "input must not change")
        self.assertEqual(p["sha256"], before)

    def test_report_never_echoes_cell_values(self):
        f = write(self.tmp, "a.csv", "Name,Code\nZebraSecretValue,007\nZebraSecretValue,007\n")
        p = ic.profile(f)
        text = ic.render(p)
        self.assertNotIn("ZebraSecretValue", text)
        self.assertNotIn("007", text)
        self.assertIn("exact copies", text)

    def test_row_limit_boundary(self):
        rows = "".join(f"{i},x{i}\n" for i in range(100))
        self.assertEqual(ic.profile(write(self.tmp, "ok.csv", "id,v\n" + rows + ",\n"))["scope"], "IN_SCOPE")
        over = ic.profile(write(self.tmp, "over.csv", "id,v\n" + rows + "100,x100\n"))
        self.assertEqual((over["scope"], over["data_rows"]), ("OVER_ROW_LIMIT", 101))
        self.assertEqual(ic.main([str(self.tmp / "over.csv")]), 2)

    def test_semicolon_bom_and_cp1252(self):
        p = ic.profile(write(self.tmp, "s.csv", "﻿Nom;Prix\nCafé;1,50\n"))
        self.assertEqual((p["column_count"], p["columns"][0]["name"]), (2, "Nom"))
        self.assertTrue(any("Delimiter" in n for n in p["file_notes"]))
        p2 = ic.profile(write(self.tmp, "w.csv", "Nom,Prix\nCafé,2\n", encoding="cp1252"))
        self.assertTrue(any("Windows-1252" in n for n in p2["file_notes"]))

    def test_date_classes(self):
        self.assertEqual(ic._date_class("2026-11-01"), "year-first")
        self.assertEqual(ic._date_class("11/04/2026"), "ambiguous")
        self.assertEqual(ic._date_class("25/04/2026"), "day-first")
        self.assertEqual(ic._date_class("04/25/2026"), "month-first")
        self.assertEqual(ic._date_class("05/05/2026"), "same-either-way")
        self.assertIsNone(ic._date_class("4.50"))
        self.assertIsNone(ic._date_class("A-12-3"))

    def test_formula_like_and_money_and_ragged(self):
        f = write(self.tmp, "f.csv", 'a,b\n=SUM(A1),"$1,200"\n-5,3\nx,y,z\n')
        p = ic.profile(f)
        self.assertEqual(self.col(p, "a")["formula_like_rows"], [2])
        self.assertEqual(self.col(p, "b")["currency_or_thousands_cells"], 1)
        self.assertEqual(p["ragged_rows"], [4])
        self.assertEqual(p["scope"], "NEEDS_STRUCTURE_FIX")

    def test_header_issues(self):
        p = ic.profile(write(self.tmp, "h.csv", "id,ID,\n1,2,3\n"))
        self.assertEqual(len(p["header_issues"]), 2)
        self.assertEqual(p["scope"], "NEEDS_STRUCTURE_FIX")

    def test_xlsx_workbook(self):
        import datetime as dt
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["SKU", "Qty", "Date", "Total"])
        ws.append(["0007", 3, dt.datetime(2026, 11, 1), "=B2*2"])
        ws.append(["0007", 3, dt.datetime(2026, 11, 1), "=B2*2"])
        ws.append([None, None, None, None])
        ws.append(["0008", 4.5, "11/04/2026", 9])
        ws.merge_cells("A7:B7")
        wb.create_sheet("Other")
        f = self.tmp / "b.xlsx"
        wb.save(f)
        before = hashlib.sha256(f.read_bytes()).hexdigest()
        p = ic.profile(f)
        self.assertEqual((p["format"], p["data_rows"], p["column_count"]), ("xlsx", 3, 4))
        self.assertEqual((p["blank_rows"], p["exact_duplicate_rows"]), ([4], [3]))
        self.assertEqual(self.col(p, "Total")["formula_like_rows"], [2, 3])
        self.assertEqual(self.col(p, "SKU")["leading_zero_cells"], 3)
        self.assertEqual(self.col(p, "Date")["ambiguous_date_rows"], [5])
        notes = " ".join(p["file_notes"])
        for word in ("2 sheets", "merged", "true Excel dates"):
            self.assertIn(word, notes)
        self.assertEqual(hashlib.sha256(f.read_bytes()).hexdigest(), before, "input must not change")

    def test_rejects_macro_and_unknown_types(self):
        for name in ("m.xlsm", "o.xls", "t.txt"):
            f = write(self.tmp, name, "x")
            with self.assertRaises(ic.IntakeError):
                ic.profile(f)
            self.assertEqual(ic.main([str(f)]), 1)

    def test_clean_file_has_no_questions(self):
        p = ic.profile(write(self.tmp, "c.csv", "id,name\n1,Pen\n2,Ink\n"))
        self.assertEqual(p["questions"], [])
        self.assertIn("ready to clean", ic.render(p))


if __name__ == "__main__":
    unittest.main()
