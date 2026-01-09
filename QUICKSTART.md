# Quick Start: PASS Flow Testing Engine

This guide shows how to run the tool locally for both SQLite (bundled examples) and Postgres. It assumes batches already exist and the database/schema are managed outside the tool.

## 1) Install dependencies
### Online
```
pip install -r requirements.txt
```

### Air-gapped (using local wheelhouse `deps/`)
```
python -m venv .venv
.\.venv\Scripts\activate
pip install --no-index --find-links deps -r requirements.txt
```
("deps" is a folder of .whl files; keep it alongside the repo.)

## 2) Run a bundled SQLite example (system_flow)
```
python flow_tests/system_flow/init_db.py
python run_suites.py test-manifest-system-flow.yaml
```
Expected: batch logs under `reports/system_flow/`, report at `reports/system_flow/system_flow_results.json`.

## 3) Run the Postgres analyst example
Update `test-manifest-analyst-example.yaml` with your Postgres URL, then:
```
python run_suites.py test-manifest-analyst-example.yaml
```
Config template: `flow_tests/analyst_example/config.yaml` (edit `batches.script`, `copy_input_file_to`, and SQL/expectations).

### Optional: SFTP delivery
If the batch machine is remote, you can configure SFTP in the manifest (next to `database`):
```
database:
  connection_url: postgresql://user:pass@host/db
sftp:
  host: your-sftp-host
  port: 22
  username: your-user
  password: your-password
  # private_key: /path/to/key (optional)
```
Keep `copy_input_file_to` in the suite config as the remote target directory; the runner uploads the CSV there before batches run.

### Optional: Remote batch execution (SSH)
If batches must run on the remote machine, add an `ssh` block to the manifest:
```
ssh:
  host: your-ssh-host
  port: 22
  username: your-user
  password: your-password
  # private_key: /path/to/key (optional)
  # os: Linux (default)  # adjust if the remote OS is different
  # shell: /bin/bash     # optional override
```
With `ssh` configured, batch scripts are executed remotely via SSH; `copy_input_file_to` points to the remote directory where the script will find the CSV.

## 4) Run diagnostic scenarios (optional)
```
python flow_tests/system_flow/init_db.py
python run_suites.py test-manifest-system-flow.yaml

python flow_tests/system_flow_batch2_fail/init_db.py
python run_suites.py test-manifest-system-flow-batch2-fail.yaml

python flow_tests/system_flow_missing_script/init_db.py
python run_suites.py test-manifest-system-flow-missing-script.yaml

python flow_tests/system_flow_input_delivery_fail/init_db.py
python run_suites.py test-manifest-system-flow-input-delivery-fail.yaml

python flow_tests/system_flow_validation_fail/init_db.py
python run_suites.py test-manifest-system-flow-validation-fail.yaml

python flow_tests/system_flow_multi/init_db.py
python run_suites.py test-manifest-system-flow-multi.yaml
```

## 5) CLI basics (run_suites.py)
```
python run_suites.py <manifest.yaml> [--db-url <url>] [--suite NAME] [--tags TAG]
```
- `--db-url` overrides the manifest DB URL.
- `--suite` filters suites by name (can repeat).
- `--tags` filters suites by tag (can repeat).

## 6) File locations
- Reports: `reports/<suite_name>/<suite_name>_results.json`
- Batch logs: `reports/<suite_name>/...log`
- Aggregate report: `reports/aggregate_summary.json`

## 7) Validation copy safety
If batches delete or move the input CSV, set `execution.validation_copy_path` in the suite config. The runner copies the CSV there before batches run and uses the copy for validation.

## 8) Common pitfalls
- Queries must return exactly one row; 0 or multiple rows fail the validation.
- CSV must exist at config load time (if your batch creates it later, use `validation_copy_path` with a stable source path).
- Windows manifests/configs: quote paths containing `:` (drive letters) to avoid YAML parse errors.
- Ensure DB drivers are installed (e.g., `psycopg2` for Postgres).

## 9) Path resolution
- Suite config paths (CSV, scripts, validation_copy_path) are resolved relative to the config file location.
- Batch scripts: provide the base path without extension; `.bat` is used on Windows, `.sh` on non-Windows.

## 10) Reports
- Per-suite report includes summary, failures (with `sql_executed`), all results, and batch execution (if run).
- Aggregate report summarizes all suites in a manifest.

## 11) Passing arguments to batch scripts
- Add `args` to a batch entry to append arguments after the script name (works for local `.bat`/`.sh` and SSH runs):
```
batches:
  - name: Step 1
    script: flow_tests/system_flow/batches/step1
    copy_input_file_to: /opt/remote/input
    args: ["--mode", "full", "/opt/remote/input/test.csv"]
```
- `args` must be a list; each item is stringified as-is before invocation.
