import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import run_suites


def write_text(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def yaml_path(path):
    return f"'{Path(path).as_posix()}'"


class FakeValidator:
    fail_ids = set()

    def __init__(self, *args, **kwargs):
        pass

    def validate_row(self, row_num, row_data, variables_config, validations):
        policy_id = row_data.get("id")
        if policy_id in self.fail_ids:
            return {
                "has_failures": True,
                "validations": [{
                    "name": "check",
                    "passed": False,
                    "errors": ["forced failure"],
                    "sql_executed": "select 1"
                }]
            }
        return {
            "has_failures": False,
            "validations": [{
                "name": "check",
                "passed": True,
                "errors": [],
                "sql_executed": "select 1"
            }]
        }


class FakeBatchExecutor:
    def __init__(self, *args, **kwargs):
        pass

    def execute_batches(self, *args, **kwargs):
        return True, []


def build_minimal_config(csv_rel_path):
    return f"""file:
  path: {csv_rel_path}
  delimiter: ","
  encoding: "utf-8"

validations:
  - name: check
    sql: "select 1"
    expect:
      row_count: 1
"""


def build_manifest(config_path, report_dir, db_url="sqlite:///:memory:"):
    return f"""version: 1

database:
  connection_url: '{db_url}'

suites:
  - name: suite_one
    enabled: true
    critical: false
    config: {yaml_path(config_path)}

reporting:
  output_dir: {yaml_path(report_dir)}
"""


def test_run_suites_cli_smoke(tmp_path, monkeypatch):
    manifest_path = tmp_path / "manifest.yaml"
    write_text(
        manifest_path,
        "version: 1\n"
        "database:\n"
        "  connection_url: 'sqlite:///:memory:'\n"
        "suites:\n"
        "  - name: s\n"
        "    config: 'c.yaml'\n"
    )

    def fake_run_all(self, suite_filter=None, tags_filter=None):
        return True

    monkeypatch.setattr(run_suites.SuiteRunner, "run_all", fake_run_all)
    monkeypatch.setattr(sys, "argv", ["run_suites.py", str(manifest_path)])

    with pytest.raises(SystemExit) as excinfo:
        run_suites.main()

    assert excinfo.value.code == 0


def test_path_resolution_and_report_output(tmp_path, monkeypatch):
    (tmp_path / "other").mkdir(parents=True, exist_ok=True)
    suite_dir = tmp_path / "suites" / "nested"
    csv_path = suite_dir / "data.csv"
    write_text(csv_path, "id\n1\n")

    config_path = suite_dir / "config.yaml"
    write_text(config_path, build_minimal_config("data.csv"))

    report_dir = tmp_path / "reports"
    manifest_path = tmp_path / "manifest.yaml"
    write_text(manifest_path, build_manifest(config_path, report_dir))

    FakeValidator.fail_ids = set()
    monkeypatch.setattr(run_suites, "Validator", FakeValidator)
    monkeypatch.setattr(run_suites, "BatchExecutor", FakeBatchExecutor)
    monkeypatch.chdir(tmp_path / "other")

    runner = run_suites.SuiteRunner(manifest_path)
    assert runner.run_all()

    report_file = report_dir / "suite_one" / "suite_one_results.json"
    report = report_file.read_text(encoding="utf-8")
    assert "\"total_rows\": 1" in report


def test_report_includes_sql_executed_on_failure(tmp_path, monkeypatch):
    suite_dir = tmp_path / "suite"
    csv_path = suite_dir / "data.csv"
    write_text(csv_path, "id\nFAIL\n")

    config_path = suite_dir / "config.yaml"
    write_text(config_path, build_minimal_config("data.csv"))

    report_dir = tmp_path / "reports"
    manifest_path = tmp_path / "manifest.yaml"
    write_text(manifest_path, build_manifest(config_path, report_dir))

    FakeValidator.fail_ids = {"FAIL"}
    monkeypatch.setattr(run_suites, "Validator", FakeValidator)
    monkeypatch.setattr(run_suites, "BatchExecutor", FakeBatchExecutor)

    runner = run_suites.SuiteRunner(manifest_path)
    assert not runner.run_all()

    report_file = report_dir / "suite_one" / "suite_one_results.json"
    report = report_file.read_text(encoding="utf-8")
    assert "\"sql_executed\": \"select 1\"" in report


def test_aggregate_summary_two_suites(tmp_path, monkeypatch):
    report_dir = tmp_path / "reports"

    suite_a = tmp_path / "suite_a"
    write_text(suite_a / "data.csv", "id\nPASS\n")
    write_text(suite_a / "config.yaml", build_minimal_config("data.csv"))

    suite_b = tmp_path / "suite_b"
    write_text(suite_b / "data.csv", "id\nFAIL\n")
    write_text(suite_b / "config.yaml", build_minimal_config("data.csv"))

    manifest_path = tmp_path / "manifest.yaml"
    write_text(
        manifest_path,
        f"""version: 1

database:
  connection_url: 'sqlite:///:memory:'

suites:
  - name: suite_a
    enabled: true
    critical: false
    config: {yaml_path(suite_a / 'config.yaml')}
  - name: suite_b
    enabled: true
    critical: false
    config: {yaml_path(suite_b / 'config.yaml')}

reporting:
  output_dir: {yaml_path(report_dir)}
"""
    )

    FakeValidator.fail_ids = {"FAIL"}
    monkeypatch.setattr(run_suites, "Validator", FakeValidator)
    monkeypatch.setattr(run_suites, "BatchExecutor", FakeBatchExecutor)

    runner = run_suites.SuiteRunner(manifest_path)
    assert not runner.run_all()

    aggregate = (report_dir / "aggregate_summary.json").read_text(encoding="utf-8")
    assert "\"total_suites\": 2" in aggregate
    assert "\"passed_suites\": 1" in aggregate
    assert "\"failed_suites\": 1" in aggregate


def test_batch_failure_short_circuit(tmp_path, monkeypatch):
    class FailingBatchExecutor:
        def __init__(self, *args, **kwargs):
            pass

        def execute_batches(self, *args, **kwargs):
            return False, [{
                "batch_name": "step1",
                "script": "script",
                "status": "FAILED",
                "exit_code": 1,
                "error": "boom",
                "duration_seconds": 0.1
            }]

    suite_dir = tmp_path / "suite"
    write_text(suite_dir / "data.csv", "id\n1\n")
    write_text(suite_dir / "config.yaml", build_minimal_config("data.csv") + "batches:\n  - name: step1\n    script: step1\n")

    report_dir = tmp_path / "reports"
    manifest_path = tmp_path / "manifest.yaml"
    write_text(manifest_path, build_manifest(suite_dir / "config.yaml", report_dir))

    monkeypatch.setattr(run_suites, "Validator", FakeValidator)
    monkeypatch.setattr(run_suites, "BatchExecutor", FailingBatchExecutor)

    runner = run_suites.SuiteRunner(manifest_path)
    assert not runner.run_all()

    report_file = report_dir / "suite_one" / "suite_one_results.json"
    report = report_file.read_text(encoding="utf-8")
    assert "\"batch_execution\"" in report
    assert "\"total_rows\": 0" in report
