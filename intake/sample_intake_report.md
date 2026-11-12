# Intake check: synthetic_input.csv

- Format: csv; columns: 7; data rows: 16 (limit 100)
- Scope result: **IN_SCOPE**
- Fully blank rows: 2; exact duplicate rows: 2
- Original file fingerprint (SHA-256): `b51464fb9bfa800a3e57c68b951f3bfde8fc6fddbeff45dd66d853384f6ece99`


Row numbers are spreadsheet rows (header is row 1). No cell values are shown.

## Questions before I start

1. 2 row(s) are exact copies of an earlier row (rows 4, 14). OK to remove them and keep the first copy?
2. 2 fully blank row(s) (rows 5, 11). OK to remove them?
3. Column 'Item_ID' has 16 value(s) starting with 0. Is it an ID/code (keep the zeros as text) or a number (drop them)?
4. Column 'Category' has 3 value(s) written with different capitalisation. Which spelling should be the standard?
5. Column 'Quantity' has 6 value(s) starting with 0. Is it an ID/code (keep the zeros as text) or a number (drop them)?
6. Column 'Quantity' has 1 blank cell(s). Leave them blank (default), or is there a rule?
7. Column 'Unit_Price_CAD' has 1 blank cell(s). Leave them blank (default), or is there a rule?
8. Column 'Stock_Date' mixes or has unclear date formats (rows 10 could be day-first or month-first). Is the source day-first or month-first, and which output format do you want (e.g. YYYY-MM-DD)?
9. Column 'Stock_Date' has 1 blank cell(s). Leave them blank (default), or is there a rule?
10. Column 'Supplier_Note' has 7 blank cell(s). Leave them blank (default), or is there a rule?
