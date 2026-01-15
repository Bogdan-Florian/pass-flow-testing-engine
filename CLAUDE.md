# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PASS Flow Testing Engine is a Python data validation framework that validates database records against CSV input data. It orchestrates multi-stage test flows: batch script execution (local/SFTP/SSH) → CSV processing → SQL-based validation against databases (SQLite, PostgreSQL, MySQL).

## Commands

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Run Tests
```bash
pytest tests/                          # All tests
pytest tests/test_validator.py         # Specific test file
pytest -v tests/                       # Verbose output
```

### Run Example Suites
```bash
python flow_tests/system_flow/init_db.py           # Initialize SQLite DB
python run_suites.py test-manifest-system-flow.yaml # Run suite
```

### CLI Options
```bash
python run_suites.py <manifest.yaml> [--db-url <url>] [--suite NAME] [--tags TAG]
```

## Architecture

### Core Data Flow
```
Manifest YAML → ManifestLoader
    ↓
For each Suite:
    ConfigLoader → BatchExecutor (InputDelivery + SshRunner) → CSVProcessor → Validator
    ↓
Reporter → AggregateReporter → JSON reports
```

### Key Modules

| Module | Purpose |
|--------|---------|
| `run_suites.py` | Primary entry point - multi-suite orchestration |
| `main.py` | Legacy single-suite entry point |
| `config_loader.py` | Parses suite `config.yaml` files |
| `manifest_loader.py` | Parses test manifest files |
| `batch_executor.py` | Executes scripts (local/SFTP/SSH) |
| `csv_processor.py` | CSV reading and row iteration |
| `validator.py` | SQL validation engine with type conversion |
| `reporter.py` | Per-suite JSON reports |
| `aggregate_reporter.py` | Cross-suite summary reports |

### Configuration Hierarchy
- **Manifest** (`test-manifest-*.yaml`): Defines database connection, SFTP/SSH settings, list of suites
- **Suite Config** (`config.yaml`): CSV file settings, batch scripts, variables, validation rules

### Type System
Variables support typed conversion: `${row.ColumnName:type}` where type is `string`, `int`, `float`, `decimal`, `date`, or `datetime`.

### Batch Script Resolution
Batch scripts are platform-aware: provide base path without extension (e.g., `batches/step1`), and `.bat` is used on Windows, `.sh` on non-Windows.

## Key Conventions

- Suite directories: lowercase with underscores (e.g., `flow_tests/system_flow/`)
- Config paths are relative to the config file location
- Reports output to `reports/<suite_name>/<suite_name>_results.json`
- Aggregate report at `reports/aggregate_summary.json`
- Validation queries must return exactly one row by default
- Use `execution.validation_copy_path` if batches modify/delete the input CSV
