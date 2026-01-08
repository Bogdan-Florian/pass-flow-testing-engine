# Analyst Example Flow

This example shows a simple "policy inserted" validation. It assumes:
- The database already exists and is populated by your batch process.
- The batch scripts already exist and are maintained by your team.

## Files
- config.yaml: template suite configuration
- test.csv: example input rows to validate
- test-manifest-analyst-example.yaml: template manifest

## How to use
1) Update config.yaml:
   - Set the batch script path(s) in `batches.script`.
   - Set the destination folder in `copy_input_file_to`.
   - Adjust SQL in `validations` to match your schema.

2) Update test-manifest-analyst-example.yaml:
   - Set `database.connection_url` to your Postgres database.

3) Run:
   python run_suites.py test-manifest-analyst-example.yaml

## Quick mapping guide
The CSV columns map into `variables`, and those variables are used in SQL and expectations:
- CSV column `PolicyNumber` -> variable `policy_number`
- CSV column `Amount` -> variable `amount` (as Decimal)
- CSV column `Status` -> variable `status`

When you see:
- `:policy_number` in SQL, that uses the variable from the CSV row.
- `${status}` in `expect.columns`, that compares the DB value to the CSV row value.

## Notes
- This flow does not create schemas or seed data. Your batches and DB own that.
- `validation_copy_path` preserves a local copy for validation even if batches delete the input file.
- `:decimal` forces numeric values to be treated as Decimal for precise comparisons (avoids float rounding).
