# Transparent CSV cleanup — tested example

A **self-directed synthetic demonstration**, not a customer order, review, or testimonial.

I offer bounded CSV/Excel cleanup on Fiverr through seller **awabm1234**. Starter scope: one CSV/Excel data file of up to 100 rows, with an agreed duplicate rule, standard formatting, and a concise change log. Missing or ambiguous facts are flagged, not invented. AI-assisted preparation and independent checks are part of the workflow.

**Request the service on Fiverr:** https://www.fiverr.com/awabm1234

## Free check before you order

Not sure your file fits the US$15 package? `intake/intake_check.py` reads one `.csv` or `.xlsx` file on your own computer and reports:

- whether it is inside the 100-row scope;
- how many fully blank rows and exact duplicate rows it has;
- which columns have unclear dates, leading zeros, mixed capitalisation, blanks or currency symbols;
- the exact questions I would ask before changing anything.

Your file is never modified or uploaded. The report shows counts, column names and row numbers only, never cell values. See the [sample report](intake/sample_intake_report.md).

```powershell
pip install openpyxl   # only needed for .xlsx files
python -B intake/intake_check.py your_file.csv --out report.md
```

Ten automated tests cover the check (`python -B -m unittest discover -s intake`). It checks a file; it does not clean it. `.xlsx` reading was tested with openpyxl, not in desktop Excel.

## Original proof

![CSV cleanup demo with before/after results](portfolio_proof.png)

- 18 fictional input records became 14 output records after removing **two blank records and two exact duplicates**.
- 28 cell-format edits, documented in `CHANGELOG.md` and `change_log.json`.
- Seven ambiguous/uncertain issues deliberately flagged for buyer review.
- 17 automated unit tests and a separate validation script pass locally.
- The original stays unchanged; this example does not use client data.

Review [synthetic source](synthetic_input.csv), [cleaned result](cleaned_output.csv), [change record](CHANGELOG.md), and [test script](test_cleanup.py).

## Reproduce

```powershell
python -B cleanup_demo.py
python -B -m unittest -v test_cleanup
python -B validate.py
```

This is a **CSV demonstration**; native workbook features are not proved by these tests. A real engagement requires review of the buyer's format, approved transformation rules, and a platform order. Do not share real sensitive data or credentials. No income or previous customer outcome is claimed.