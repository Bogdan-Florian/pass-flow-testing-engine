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


def test_build_command_with_args_windows():
    command = BatchExecutor.build_command("C:\\scripts\\run.bat", "Windows", args=["a", "b"])
    assert command == ["cmd.exe", "/c", "C:\\scripts\\run.bat", "a", "b"]


def test_build_command_with_args_linux(monkeypatch):
    monkeypatch.setattr(batch_executor.shutil, "which", lambda _: "/bin/bash")
    command = BatchExecutor.build_command("/tmp/run.sh", "Linux", args=["one", "two"])
    assert command == ["bash", "/tmp/run.sh", "one", "two"]


def test_resolve_script_path_windows():
    executor = BatchExecutor("suite", os_name="Windows")
    script_path = executor._resolve_script_path("scripts/run")
    assert isinstance(script_path, str)
    assert script_path.endswith(".bat")


def test_resolve_script_path_non_windows():
    executor = BatchExecutor("suite", os_name="Linux")
    script_path = executor._resolve_script_path("scripts/run")
    assert isinstance(script_path, str)
    assert script_path.endswith(".sh")


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
    monkeypatch.setattr(executor, "_run_script", lambda *args, **kwargs: (2, "bad exit"))

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


def test_execute_batches_with_args_passed_to_runner(tmp_path, monkeypatch):
    script_base = tmp_path / "run"
    script_path = script_base.with_suffix(".sh")
    script_path.write_text("#!/bin/sh\necho ok\n", encoding="utf-8")

    captured = {}

    executor = BatchExecutor(
        "suite",
        output_dir=tmp_path,
        os_name="Linux"
    )

    def fake_run(script, log, args=None, timeout=None):
        captured["script"] = script
        captured["log"] = log
        captured["args"] = args
        captured["timeout"] = timeout
        return 0, None

    monkeypatch.setattr(executor, "_run_script", fake_run)

    batch_configs = [{
        "name": "ArgsBatch",
        "script": str(script_base),
        "args": ["--flag", "value"]
    }]
    success, results = executor.execute_batches(batch_configs, tmp_path / "input.csv")
    assert success
    assert captured["args"] == ["--flag", "value"]
    assert results[0]["status"] == "SUCCESS"


def test_execute_batches_rejects_non_list_args(tmp_path):
    script_base = tmp_path / "run"
    script_path = script_base.with_suffix(".sh")
    script_path.write_text("#!/bin/sh\necho ok\n", encoding="utf-8")

    executor = BatchExecutor("suite", output_dir=tmp_path, os_name="Linux")
    batch_configs = [{
        "name": "BadArgs",
        "script": str(script_base),
        "args": "--not-a-list"
    }]

    success, results = executor.execute_batches(batch_configs, tmp_path / "input.csv")
    assert not success
    assert results[0]["status"] == "FAILED"
    assert "args" in results[0]["error"]


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
    monkeypatch.setattr(executor, "_run_script", lambda *args, **kwargs: (0, None))

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
    monkeypatch.setattr(executor, "_run_script", lambda *args, **kwargs: (0, None))

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


# ===========================================================================
# SSH/Remote Execution Tests
# ===========================================================================

from batch_executor import SshRunner, SftpDelivery, _load_private_key
import socket


class MockSSHClient:
    """Mock SSH client for testing"""

    def __init__(self, exit_code=0, stdout_data="output", stderr_data="", timeout_on_read=False):
        self.exit_code = exit_code
        self.stdout_data = stdout_data
        self.stderr_data = stderr_data
        self.timeout_on_read = timeout_on_read
        self.connected = False
        self.closed = False

    def set_missing_host_key_policy(self, policy):
        pass

    def load_system_host_keys(self):
        pass

    def connect(self, host, port=22, username=None, password=None, pkey=None):
        self.connected = True

    def exec_command(self, command):
        class MockChannel:
            def __init__(self, exit_code, timeout_on_read):
                self._exit_code = exit_code
                self._timeout_on_read = timeout_on_read
                self._timeout = None

            def settimeout(self, t):
                self._timeout = t

            def recv_exit_status(self):
                return self._exit_code

        class MockStream:
            def __init__(self, data, channel, timeout_on_read):
                self._data = data
                self.channel = channel
                self._timeout_on_read = timeout_on_read
                self.closed = False

            def read(self):
                if self._timeout_on_read:
                    raise socket.timeout("timed out")
                return self._data.encode("utf-8")

            def close(self):
                self.closed = True

        channel = MockChannel(self.exit_code, self.timeout_on_read)
        stdin = MockStream("", channel, False)
        stdout = MockStream(self.stdout_data, channel, self.timeout_on_read)
        stderr = MockStream(self.stderr_data, channel, False)
        return stdin, stdout, stderr

    def close(self):
        self.closed = True


def test_ssh_runner_success(tmp_path, monkeypatch):
    """Test successful SSH remote execution"""
    mock_client = MockSSHClient(exit_code=0, stdout_data="Script output\n")
    monkeypatch.setattr("paramiko.SSHClient", lambda: mock_client)

    runner = SshRunner(
        host="testhost",
        port=22,
        username="testuser",
        password="testpass",
        os_name="Linux"
    )

    log_path = tmp_path / "test.log"

    def mock_command_builder(script, os_name, shell, args):
        return ["bash", script]

    exit_code, error = runner.run("/path/to/script.sh", log_path, mock_command_builder)

    assert exit_code == 0
    assert error is None
    assert mock_client.connected
    assert mock_client.closed
    assert log_path.exists()

    log_content = log_path.read_text(encoding="utf-8")
    assert "Script output" in log_content
    assert "Exit Code: 0" in log_content


def test_ssh_runner_script_failure(tmp_path, monkeypatch):
    """Test SSH execution when script returns non-zero exit code"""
    mock_client = MockSSHClient(exit_code=1, stderr_data="Error occurred\n")
    monkeypatch.setattr("paramiko.SSHClient", lambda: mock_client)

    runner = SshRunner(host="testhost", username="testuser", password="testpass")
    log_path = tmp_path / "test.log"

    def mock_command_builder(script, os_name, shell, args):
        return ["bash", script]

    exit_code, error = runner.run("/path/to/script.sh", log_path, mock_command_builder)

    assert exit_code == 1
    assert error is None  # Script ran, just returned non-zero
    log_content = log_path.read_text(encoding="utf-8")
    assert "STDERR" in log_content
    assert "Error occurred" in log_content


def test_ssh_runner_timeout(tmp_path, monkeypatch):
    """Test SSH execution timeout"""
    mock_client = MockSSHClient(timeout_on_read=True)
    monkeypatch.setattr("paramiko.SSHClient", lambda: mock_client)

    runner = SshRunner(
        host="testhost",
        username="testuser",
        password="testpass",
        timeout=30
    )
    log_path = tmp_path / "test.log"

    def mock_command_builder(script, os_name, shell, args):
        return ["bash", script]

    exit_code, error = runner.run("/path/to/script.sh", log_path, mock_command_builder)

    assert exit_code == -1
    assert "timeout" in error.lower()


def test_ssh_runner_connection_failure(tmp_path, monkeypatch):
    """Test SSH connection failure"""
    def failing_connect(*args, **kwargs):
        raise Exception("Connection refused")

    class FailingClient(MockSSHClient):
        def connect(self, *args, **kwargs):
            raise Exception("Connection refused")

    monkeypatch.setattr("paramiko.SSHClient", FailingClient)

    runner = SshRunner(host="badhost", username="user", password="pass")
    log_path = tmp_path / "test.log"

    def mock_command_builder(script, os_name, shell, args):
        return ["bash", script]

    exit_code, error = runner.run("/path/to/script.sh", log_path, mock_command_builder)

    assert exit_code == -1
    assert "Connection refused" in error


def test_ssh_runner_private_key_validation(tmp_path):
    """Test that SshRunner validates private key file exists"""
    with pytest.raises(FileNotFoundError) as exc_info:
        SshRunner(
            host="testhost",
            username="testuser",
            private_key="/nonexistent/key"
        )
    assert "Private key file not found" in str(exc_info.value)


def test_ssh_runner_with_args(tmp_path, monkeypatch):
    """Test SSH execution with script arguments"""
    captured_command = []

    class CapturingClient(MockSSHClient):
        def exec_command(self, command):
            captured_command.append(command)
            return super().exec_command(command)

    monkeypatch.setattr("paramiko.SSHClient", CapturingClient)

    runner = SshRunner(host="testhost", username="user", password="pass")
    log_path = tmp_path / "test.log"

    def mock_command_builder(script, os_name, shell, args):
        return ["bash", script] + (args or [])

    runner.run("/path/script.sh", log_path, mock_command_builder, args=["--flag", "value"])

    assert len(captured_command) == 1
    assert "--flag" in captured_command[0]
    assert "value" in captured_command[0]


def test_sftp_delivery_private_key_validation(tmp_path):
    """Test that SftpDelivery validates private key file exists"""
    with pytest.raises(FileNotFoundError) as exc_info:
        SftpDelivery(
            host="testhost",
            username="testuser",
            private_key="/nonexistent/key"
        )
    assert "Private key file not found" in str(exc_info.value)


def test_resolve_script_path_remote_linux():
    """Test script path resolution for remote Linux execution"""
    class MockRunner:
        os_name = "Linux"

    executor = BatchExecutor("suite", os_name="Linux", remote_runner=MockRunner())
    script_path = executor._resolve_script_path("scripts/run")

    assert isinstance(script_path, str)
    assert script_path.endswith(".sh")
    assert "/" in script_path  # POSIX path


def test_resolve_script_path_remote_windows():
    """Test script path resolution for remote Windows execution"""
    class MockRunner:
        os_name = "Windows"

    executor = BatchExecutor("suite", os_name="Windows", remote_runner=MockRunner())
    script_path = executor._resolve_script_path("scripts/run")

    assert isinstance(script_path, str)
    assert script_path.endswith(".bat")


def test_batch_executor_with_remote_runner(tmp_path, monkeypatch):
    """Test BatchExecutor integration with remote runner"""
    run_calls = []

    class MockRemoteRunner:
        os_name = "Linux"
        timeout = 3600  # Default timeout (required by BatchExecutor)

        def run(self, script_path, log_path, command_builder, args=None):
            run_calls.append({
                "script": script_path,
                "log": str(log_path),
                "args": args
            })
            # Write a minimal log file
            with open(log_path, "w") as f:
                f.write("Remote execution log\n")
            return 0, None

    executor = BatchExecutor(
        "suite",
        output_dir=tmp_path,
        os_name="Linux",
        remote_runner=MockRemoteRunner()
    )

    batch_configs = [{
        "name": "RemoteBatch",
        "script": "path/to/script",
        "args": ["--arg1", "value1"]
    }]

    success, results = executor.execute_batches(batch_configs, tmp_path / "input.csv")

    assert success
    assert len(run_calls) == 1
    assert run_calls[0]["script"].endswith(".sh")
    assert run_calls[0]["args"] == ["--arg1", "value1"]
    assert results[0]["status"] == "SUCCESS"


def test_validate_script_accepts_string_path(tmp_path):
    """Test that _validate_script works with both Path and str inputs"""
    executor = BatchExecutor("suite")

    script_path = tmp_path / "test.sh"
    script_path.write_text("#!/bin/sh\necho ok\n", encoding="utf-8")

    # Test with Path object
    is_valid, error = executor._validate_script(script_path)
    assert is_valid

    # Test with string
    is_valid, error = executor._validate_script(str(script_path))
    assert is_valid


def test_ssh_runner_utf8_error_handling(tmp_path, monkeypatch):
    """Test that SSH runner handles non-UTF-8 output gracefully"""

    class BinaryChannel:
        def __init__(self):
            self._timeout = None

        def settimeout(self, t):
            self._timeout = t

        def recv_exit_status(self):
            return 0

    class BinaryStream:
        def __init__(self, data, channel):
            self._data = data
            self.channel = channel
            self.closed = False

        def read(self):
            return self._data

        def close(self):
            self.closed = True

    class BinaryOutputClient:
        def __init__(self):
            self.connected = False
            self.closed = False

        def set_missing_host_key_policy(self, policy):
            pass

        def load_system_host_keys(self):
            pass

        def connect(self, host, port=22, username=None, password=None, pkey=None):
            self.connected = True

        def exec_command(self, command):
            channel = BinaryChannel()
            stdin = BinaryStream(b"", channel)
            # Return bytes with invalid UTF-8 sequence
            stdout = BinaryStream(b"Valid text \xff\xfe invalid bytes", channel)
            stderr = BinaryStream(b"", channel)
            return stdin, stdout, stderr

        def close(self):
            self.closed = True

    # Patch at batch_executor module level
    monkeypatch.setattr(batch_executor.paramiko, "SSHClient", BinaryOutputClient)

    runner = SshRunner(host="testhost", username="user", password="pass")
    log_path = tmp_path / "test.log"

    def mock_command_builder(script, os_name, shell, args):
        return ["bash", script]

    # Should not raise UnicodeDecodeError
    exit_code, error = runner.run("/path/to/script.sh", log_path, mock_command_builder)

    assert exit_code == 0
    assert error is None
    # The replacement character should be in the log
    log_content = log_path.read_text(encoding="utf-8")
    assert "Valid text" in log_content
