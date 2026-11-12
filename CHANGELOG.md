# Synthetic inventory cleanup - change log

Original demonstration only. No customer data, paid order or earnings.

Data-record numbers below exclude the header.

## Measured result

- input_data_rows: 18
- output_data_rows: 14
- fully_blank_rows_removed: 2
- exact_duplicate_rows_removed: 2
- cells_changed: 28
- review_flags: 7

## Agreed rules

Remove fully blank records and raw exact duplicates; keep the first occurrence and original order.
Trim field edges, map office/kitchen/storage to consistent category labels, display integer quantities
without padding, display CAD prices to two decimals, and change only valid YYYY/MM/DD dates to ISO.
Item IDs stay text with leading zeroes. Preserve missing values, internal note spacing, ambiguous
dates, unknown categories and records that match only after normalisation. Flag these for review.
Blank optional notes need no review. No replacement values are invented.

## Removed records

- Source record 3: exact_duplicate; identical to source record 1.
- Source record 4: fully_blank.
- Source record 10: fully_blank.
- Source record 13: exact_duplicate; identical to source record 6.

## Cell changes

| Source record | Column | Before (JSON string) | After (JSON string) |
| --- | --- | --- | --- |
| 1 | Item_Name | `"  Grid Notebook "` | `"Grid Notebook"` |
| 1 | Category | `"office"` | `"Office"` |
| 1 | Quantity | `"010"` | `"10"` |
| 1 | Unit_Price_CAD | `"4.5"` | `"4.50"` |
| 1 | Stock_Date | `"2026/11/01"` | `"2026-11-01"` |
| 2 | Category | `"OFFICE"` | `"Office"` |
| 5 | Category | `" Office "` | `"Office"` |
| 5 | Unit_Price_CAD | `"3.5"` | `"3.50"` |
| 5 | Stock_Date | `"2026/11/03"` | `"2026-11-03"` |
| 6 | Category | `"kitchen"` | `"Kitchen"` |
| 6 | Quantity | `"004"` | `"4"` |
| 6 | Unit_Price_CAD | `"8"` | `"8.00"` |
| 7 | Category | `"office"` | `"Office"` |
| 8 | Category | `"storage"` | `"Storage"` |
| 8 | Quantity | `"002"` | `"2"` |
| 8 | Stock_Date | `"2026/11/04"` | `"2026-11-04"` |
| 9 | Unit_Price_CAD | `"5.0"` | `"5.00"` |
| 11 | Category | `"STORAGE"` | `"Storage"` |
| 11 | Unit_Price_CAD | `"0015.5"` | `"15.50"` |
| 14 | Unit_Price_CAD | `"0"` | `"0.00"` |
| 15 | Category | `"office"` | `"Office"` |
| 15 | Unit_Price_CAD | `"7.0"` | `"7.00"` |
| 15 | Stock_Date | `"2026/11/06"` | `"2026-11-06"` |
| 16 | Item_Name | `" Desk Marker "` | `"Desk Marker"` |
| 16 | Quantity | `"06"` | `"6"` |
| 16 | Unit_Price_CAD | `"2"` | `"2.00"` |
| 16 | Stock_Date | `"2026/11/02"` | `"2026-11-02"` |
| 17 | Category | `"office"` | `"Office"` |

## Review flags - deliberately unresolved

- Source record 7, output record 5: missing_value_preserved (Quantity).
- Source record 9, output record 7: unresolved_date_preserved (Stock_Date).
- Source record 12, output record 9: unmapped_category_preserved (Category).
- Source record 17, output record 13: missing_value_preserved (Unit_Price_CAD).
- Source record 18, output record 14: missing_value_preserved (Stock_Date).
- Source record 2, output record 2: normalised_match_retained.
- Source record 16, output record 12: normalised_match_retained.

The machine-readable change_log.json includes every retained row's source, exact cell values
and SHA-256 fingerprints of input/output. Open/import Item_ID as Text in Excel; this CSV
demonstration does not claim desktop Excel acceptance or native XLSX formatting.
