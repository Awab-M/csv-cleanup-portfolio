# The CSV cleaner was green. I still wanted proof it hadn't erased data.

*An original, self-directed engineering case study · November 2026 · Python, CSV, deterministic validation · AI-assisted implementation, reviewed against the published source. No customer data or paid-client results.*

An automation can report "success" even when it has silently done the wrong thing. I ran into a version of that problem while preparing a small CSV-cleanup service. The easy part was writing code to trim whitespace, standardize dates and remove duplicates. The difficult part was deciding what the word *duplicate* meant, proving that no other rows vanished, and making the result inspectable by someone who did not write the cleaner.

Rather than put a generic "cleaned successfully" banner on a sample, I built a narrow, reproducible synthetic inventory exercise and a verifier that can disagree with the cleaner.

**Observed result:** 18 fictional data rows in, 14 out; two wholly blank rows and two raw *exact* duplicate rows removed; 28 individual cell changes recorded; seven review flags. The demonstration has 17 passing automated tests plus a separate validation script. Those numbers describe this fixture, not arbitrary customer files.

The [source, tests and before/after files](https://github.com/Awab-M/csv-cleanup-portfolio) are public, so the claims can be checked independently.

## 1. The "same after cleaning" trap

Imagine these two source records:

| Original record | ID | Name | Category | Qty | Price |
| --- | --- | --- | --- | --- | --- |
| 2 | 0002 | \`Desk Marker\` | \`OFFICE\` | \`6\` | \`2.00\` |
| 16 | 0002 | \` Desk Marker \` | \`Office\` | \`06\` | \`2\` |

Normalization makes the output rows identical. But that does **not** prove the original rows represented one transaction. A cleaner that deduplicates *after* normalization would silently throw one away.

In my bounded demo, exact raw duplicates are removable only when all seven source fields match before normalization. A near-duplicate that becomes identical afterward remains in the output, with a flag showing the matching output-row numbers. A buyer can then decide whether those records are truly duplicates.

The difference is only a few lines of code, but it changes the contract: the cleaner is permitted to standardize formatting, not guess record identity.

\`\`\`python
key = tuple(row)                 # raw input, before normalization
if key in seen:
    removed.append({
        "source_row": source_row,
        "reason": "exact_duplicate",
        "duplicate_of": seen[key],
    })
    continue
seen[key] = source_row
cleaned = [normalise(col, value) for col, value in zip(HEADERS, row)]
\`\`\`

This also exposes a design choice: **exact** duplicate means byte-for-byte-equivalent parsed field values, not case-insensitive business identity. That trade-off is conservative and reviewable.

## 2. Keep a ledger of rows, not just a success message

The original file contains 18 data records. The output contains 14. Four disappeared for approved reasons. A dashboard saying "18 → 14" is not enough evidence.

Every retained row therefore gets a one-based mapping to the source record:

\`\`\`json
{"output_row": 1, "source_row": 1}
\`\`\`

Every removal gets its own reason, and duplicate removals point to the first occurrence. In the published fixture, source records 3 and 13 are exact duplicates; records 4 and 10 are fully blank.

For each modified cell, the change record contains the source row, output row, column name, original value and final value. This is how the published change log can account for 28 edits without obscuring which ones happened.

The cleaner also embeds SHA-256 fingerprints of the source and result. These hashes are not proof that a correction is *right*. They prove that the files reviewed now are the same bytes the audit receipt refers to.

The point of the ledger is not bureaucracy. It's the ability to answer a buyer who says, "Where did my record go?" with a source-row number rather than a shrug.

## 3. Don't make up missing facts

A field containing \`0\` is not equivalent to an empty field. The demo preserves a real zero quantity and price while leaving missing quantity or price values empty and flagged.

Dates are more treacherous. Converting \`2026/11/01\` to \`2026-11-01\` is safe under the agreed YYYY/MM/DD rule. Converting \`11/04/2026\` is not: it could mean April 11 or November 4. The code preserves the latter string and asks for clarification.

The same rule applies to unrecognized category labels. \`OFFICE\` is mapped to \`Office\` because "office" is in the agreed dictionary. \`Mixed\` is not "fixed" into one of the known categories.

One useful engineering constraint was making numeric formatting explicit with \`Decimal\`, rather than round-tripping money through binary floating-point arithmetic:

\`\`\`python
if column == "Unit_Price_CAD" and re.fullmatch(
    r"[0-9]+(?:\.[0-9]{1,2})?", value
):
    return format(Decimal(value), ".2f")
\`\`\`

Unsupported numeric strings are preserved, not guessed. That's more important than producing a visually uniform spreadsheet at any cost.

## 4. A second program should check the first one

Unit tests catch regressions, but a test that merely calls the cleaning function and trusts its output can repeat the same mistake.

The independent \`validate.py\` script starts from the published source CSV and checks the delivered CSV, JSON audit receipt and hashes. It reconstructs which source rows should remain, verifies their order, recomputes allowed transformations by column, and rejects missing or invented nonempty values.

It separately compares the exact cell-change ledger and review flags against the transformations that actually occurred. If an output cell is changed without a matching receipt—or if a receipt claims an edit that never occurred—the verifier fails.

That separation is valuable. The cleaner answers "What do I want to do?" The verifier answers "Given the rules and original data, what am I actually allowed to have done?"

A second way to test integrity is mutation: regenerate the files, deliberately alter a delivered value, and verify the validation fails. The public test suite includes tampering checks, row-limit cases, Unicode/quoted CSV handling, exact versus near duplicates, invalid dates, leading-zero IDs, deterministic reruns and original-input preservation.

## 5. Run it, don't take my word for it

From the project root with Python 3:

\`\`\`powershell
python -B cleanup_demo.py
python -B -m unittest -v test_cleanup
python -B validate.py
\`\`\`

The [project README](https://github.com/Awab-M/csv-cleanup-portfolio/blob/main/README.md) links directly to the [synthetic input](https://github.com/Awab-M/csv-cleanup-portfolio/blob/main/synthetic_input.csv), [cleaned output](https://github.com/Awab-M/csv-cleanup-portfolio/blob/main/cleaned_output.csv), [change log](https://github.com/Awab-M/csv-cleanup-portfolio/blob/main/CHANGELOG.md) and [independent checker](https://github.com/Awab-M/csv-cleanup-portfolio/blob/main/validate.py).

**Scope matters.** This is a seven-column, maximum-100-row CSV demonstration. It is not a universal data-cleaning library. The tests do not establish that arbitrary Excel workbooks, formulas, macros, localized currencies or live client data are handled correctly. No paid orders, customer testimonials or field reliability statistics are implied.

The lesson I took from this experiment is simple: a green automation result is not a delivery standard. For a workflow that edits another person's data, the useful output is **the changed file plus evidence of what changed, why, and what was intentionally left unresolved**.

That makes the workflow slower to claim success—and much easier to trust.
