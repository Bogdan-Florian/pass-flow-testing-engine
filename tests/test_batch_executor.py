import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import batch_executor
from batch_executor import BatchExecutor, LocalCopyDelivery


def test_build_command_windows():
    command = BatchExecutor.build_command("C:\\scripts\\run.bat", "Windows")
    assert command == ["cmd.exe", "/c", "C:\\scripts\\run.bat"]


def test_build_command_non_windows_with_shell_override():
    command = BatchExecutor.build_command("/tmp/run.sh", "Linux", shell="zsh")
    assert command == ["zsh", "/tmp/run.sh"]


def test_build_command_non_windows_fallback_to_sh(monkeypatch):
    monkeypatch.setattr(batch_executor.shutil, "which", lambda _: None)
    command = BatchExecutor.build_command("/tmp/run.sh", "Linux")
    assert command == ["sh", "/tmp/run.sh"]


def test_resolve_script_path_windows():
    executor = BatchExecutor("suite", os_name="Windows")
    script_path = executor._resolve_script_path("scripts/run")
    assert script_path.suffix == ".bat"


def test_resolve_script_path_non_windows():
    executor = BatchExecutor("suite", os_name="Linux")
    script_path = executor._resolve_script_path("scripts/run")
    assert script_path.suffix == ".sh"


def test_validate_script_missing_file(tmp_path):
    executor = BatchExecutor("suite")
    script_path = tmp_path / "missing.sh"
    is_valid, error_msg = executor._validate_script(script_path)
    assert not is_valid
    assert "Script not found" in error_msg


def test_validate_script_is_not_file(tmp_path):
    executor = BatchExecutor("suite")
    script_path = tmp_path / "folder"
    script_path.mkdir()
    is_valid, error_msg = executor._validate_script(script_path)
    assert not is_valid
    assert "Script is not a file" in error_msg


def test_validate_script_not_readable(tmp_path):
    if os.name == "nt":
        pytest.skip("Windows does not reliably enforce read permissions for chmod.")
    executor = BatchExecutor("suite")
    script_path = tmp_path / "run.sh"
    script_path.write_text("echo ok", encoding="utf-8")
    script_path.chmod(0)
    try:
        is_valid, error_msg = executor._validate_script(script_path)
        assert not is_valid
        assert "Script not readable" in error_msg
    finally:
        script_path.chmod(0o600)


def test_local_copy_delivery_missing_source(tmp_path):
    delivery = LocalCopyDelivery()
    missing = tmp_path / "missing.csv"
    dest = tmp_path / "dest"
    success, error_msg = delivery.deliver(missing, dest)
    assert not success
    assert "Source file not found" in error_msg


def test_local_copy_delivery_success(tmp_path):
    delivery = LocalCopyDelivery()
    source = tmp_path / "input.csv"
    source.write_text("a,b\n1,2\n", encoding="utf-8")
    dest = tmp_path / "dest"
    success, error_msg = delivery.deliver(source, dest)
    assert success
    assert error_msg is None
    copied = dest / source.name
    assert copied.exists()
    assert copied.read_text(encoding="utf-8") == "a,b\n1,2\n"


def test_default_log_file_formatting():
    filename = BatchExecutor._default_log_file(3, "My Batch/Name")
    assert filename == "batch_03_My_Batch_Name.log"


def test_execute_batches_missing_script_key(tmp_path):
    executor = BatchExecutor("suite", output_dir=tmp_path)
    success, results = executor.execute_batches([{"name": "NoScript"}], tmp_path / "input.csv")
    assert not success
    assert results
    assert results[0]["status"] == "FAILED"
    assert "script" in results[0]["error"]


def test_execute_batches_run_script_failure(tmp_path, monkeypatch):
    script_base = tmp_path / "run"
    script_path = script_base.with_suffix(".sh")
    script_path.write_text("#!/bin/sh\necho ok\n", encoding="utf-8")

    executor = BatchExecutor("suite", output_dir=tmp_path, os_name="Linux")
    monkeypatch.setattr(executor, "_run_script", lambda *_: (2, "bad exit"))

    batch_configs = [{"name": "FailingBatch", "script": str(script_base)}]
    success, results = executor.execute_batches(batch_configs, tmp_path / "input.csv")
    assert not success
    assert results
    assert results[0]["status"] == "FAILED"
    assert results[0]["exit_code"] == 2


def test_execute_batches_input_delivery_failure(tmp_path):
    class FailingDelivery:
        def deliver(self, *_):
            return False, "nope"

    script_base = tmp_path / "run"
    script_path = script_base.with_suffix(".sh")
    script_path.write_text("#!/bin/sh\necho ok\n", encoding="utf-8")

    executor = BatchExecutor(
        "suite",
        output_dir=tmp_path,
        os_name="Linux",
        input_delivery=FailingDelivery()
    )
    batch_configs = [{
        "name": "CopyFail",
        "script": str(script_base),
        "copy_input_file_to": str(tmp_path / "dest")
    }]
    success, results = executor.execute_batches(batch_configs, tmp_path / "input.csv")
    assert not success
    assert results
    assert results[0]["status"] == "FAILED"
    assert "File copy error" in results[0]["error"]


def test_execute_batches_success_flow(tmp_path, monkeypatch):
    class NoopDelivery:
        def deliver(self, *_):
            return True, None

    script_base = tmp_path / "run"
    script_path = script_base.with_suffix(".sh")
    script_path.write_text("#!/bin/sh\necho ok\n", encoding="utf-8")

    executor = BatchExecutor(
        "suite",
        output_dir=tmp_path,
        os_name="Linux",
        input_delivery=NoopDelivery()
    )
    monkeypatch.setattr(executor, "_run_script", lambda *_: (0, None))

    batch_configs = [{
        "name": "OkBatch",
        "script": str(script_base),
        "copy_input_file_to": str(tmp_path / "dest"),
        "log_file": "custom.log"
    }]
    success, results = executor.execute_batches(batch_configs, tmp_path / "input.csv")
    assert success
    assert results
    assert results[0]["status"] == "SUCCESS"
    assert results[0]["log_file"].endswith("custom.log")
    assert results[0]["start_time"]
    assert results[0]["end_time"]


def test_execute_batches_integration_flow(tmp_path, monkeypatch):
    class FakeDelivery:
        def deliver(self, input_path, destination):
            Path(destination).mkdir(parents=True, exist_ok=True)
            dest_file = Path(destination) / Path(input_path).name
            dest_file.write_text("x\n", encoding="utf-8")
            return True, None

    input_csv = tmp_path / "input.csv"
    input_csv.write_text("a\n", encoding="utf-8")

    script_base = tmp_path / "run"
    script_path = script_base.with_suffix(".sh")
    script_path.write_text("#!/bin/sh\necho ok\n", encoding="utf-8")

    executor = BatchExecutor(
        "suite",
        output_dir=tmp_path,
        os_name="Linux",
        input_delivery=FakeDelivery()
    )
    monkeypatch.setattr(executor, "_run_script", lambda *_: (0, None))

    batch_configs = [{
        "name": "EndToEnd",
        "script": str(script_base),
        "copy_input_file_to": str(tmp_path / "dest"),
        "log_file": "e2e.log"
    }]
    success, results = executor.execute_batches(batch_configs, input_csv)
    assert success
    assert results
    assert results[0]["status"] == "SUCCESS"
    assert results[0]["log_file"].endswith("e2e.log")
    assert results[0]["start_time"] and results[0]["end_time"]
