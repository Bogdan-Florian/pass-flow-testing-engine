"""
Batch Executor
Executes shell scripts sequentially before validation tests.
Intelligently selects .bat or .sh script based on the operating system.
"""

import subprocess
import shutil
import platform
import os
import stat
import shlex
from pathlib import Path
from datetime import datetime
from typing import Optional

import paramiko

class InputDelivery:
    """Interface for input delivery implementations."""

    def deliver(self, input_path, destination):
        raise NotImplementedError


class LocalCopyDelivery(InputDelivery):
    """Local file copy delivery used by default."""

    def deliver(self, input_path, destination):
        source = Path(input_path)
        if not source.exists():
            return False, f"Source file not found: {input_path}"

        dest_dir = Path(destination)
        dest_dir.mkdir(parents=True, exist_ok=True)

        # Clear existing files in destination
        for item in dest_dir.iterdir():
            try:
                if item.is_file():
                    item.unlink()
            except Exception:
                pass

        dest_file = dest_dir / source.name
        shutil.copy2(source, dest_file)
        return True, None


class SftpDelivery(InputDelivery):
    """SFTP delivery implementation for remote targets."""

    def __init__(
        self,
        host: str,
        port: int = 22,
        username: Optional[str] = None,
        password: Optional[str] = None,
        private_key: Optional[str] = None,
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.private_key = private_key

    def deliver(self, input_path, destination):
        source = Path(input_path)
        if not source.exists():
            return False, f"Source file not found: {input_path}"

        transport = None
        try:
            transport = paramiko.Transport((self.host, self.port))
            if self.private_key:
                key = paramiko.RSAKey.from_private_key_file(self.private_key)
                transport.connect(username=self.username, pkey=key)
            else:
                transport.connect(username=self.username, password=self.password)

            sftp = paramiko.SFTPClient.from_transport(transport)

            remote_dir = Path(destination).as_posix().rstrip('/')
            remote_file = f"{remote_dir}/{source.name}"

            self._ensure_remote_dir(sftp, remote_dir)
            self._clear_remote_dir(sftp, remote_dir)
            sftp.put(str(source), remote_file)
            return True, None
        except Exception as e:
            return False, f"SFTP error: {e}"
        finally:
            if transport:
                transport.close()

    def _ensure_remote_dir(self, sftp, remote_dir: str):
        if not remote_dir:
            return
        parts = remote_dir.strip('/').split('/')
        path_so_far = ''
        for part in parts:
            path_so_far += '/' + part
            try:
                sftp.chdir(path_so_far)
            except IOError:
                sftp.mkdir(path_so_far)

    def _clear_remote_dir(self, sftp, remote_dir: str):
        try:
            for entry in sftp.listdir_attr(remote_dir):
                name = entry.filename
                full_path = f"{remote_dir}/{name}"
                # Remove files only; leave subdirectories intact
                if not stat.S_ISDIR(entry.st_mode):
                    try:
                        sftp.remove(full_path)
                    except Exception:
                        pass
        except Exception:
            pass


class SshRunner:
    """Remote script runner over SSH."""

    def __init__(
        self,
        host: str,
        port: int = 22,
        username: Optional[str] = None,
        password: Optional[str] = None,
        private_key: Optional[str] = None,
        os_name: str = "Linux",
        shell: Optional[str] = None,
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.private_key = private_key
        self.os_name = os_name
        self.shell = shell

    def run(self, script_path, log_path, command_builder, args=None):
        client = None
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            if self.private_key:
                key = paramiko.RSAKey.from_private_key_file(self.private_key)
                client.connect(self.host, port=self.port, username=self.username, pkey=key)
            else:
                client.connect(self.host, port=self.port, username=self.username, password=self.password)

            command = command_builder(script_path, self.os_name, self.shell, args)
            full_command = " ".join(shlex.quote(str(part)) for part in command)

            with open(log_path, 'w') as log_file:
                log_file.write(f"=== Remote Batch Execution Log ===\n")
                log_file.write(f"Host: {self.host}\n")
                log_file.write(f"Script: {script_path}\n")
                log_file.write(f"Command: {full_command}\n")
                log_file.write(f"Start Time: {datetime.now().isoformat()}\n")
                log_file.write(f"{'='*50}\n\n")

                stdin, stdout, stderr = client.exec_command(full_command)
                out_data = stdout.read().decode('utf-8')
                err_data = stderr.read().decode('utf-8')
                if out_data:
                    log_file.write(out_data)
                if err_data:
                    log_file.write("\n-- STDERR --\n")
                    log_file.write(err_data)

                exit_code = stdout.channel.recv_exit_status()

                log_file.write(f"\n{'='*50}\n")
                log_file.write(f"End Time: {datetime.now().isoformat()}\n")
                log_file.write(f"Exit Code: {exit_code}\n")

            return exit_code, None
        except Exception as e:
            try:
                with open(log_path, 'a') as log_file:
                    log_file.write(f"\n\nERROR: {e}\n")
            except Exception:
                pass
            return -1, f"SSH error: {e}"
        finally:
            if client:
                client.close()


class BatchExecutor:
    """Executes batch scripts with logging and error handling"""
    
    def __init__(self, suite_name, output_dir="reports", input_delivery=None, os_name=None, shell=None, remote_runner=None):
        """
        Initialize batch executor
        
        Args:
            suite_name: Name of the test suite (for logging)
            output_dir: Directory to store batch log files
        """
        self.suite_name = suite_name
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.input_delivery = input_delivery or LocalCopyDelivery()
        self.os_name = os_name or platform.system()
        self.shell = shell
        self.remote_runner = remote_runner
        
        self.batch_results = []
    
    def execute_batches(self, batch_configs, input_csv_path):
        """
        Execute all batches in sequence.
        
        This method automatically resolves the correct script (.bat for Windows,
        .sh for other systems) based on the 'script' key in the config, which
        should be provided without a file extension.
        
        Args:
            batch_configs: List of batch configuration dictionaries
            input_csv_path: Path to the CSV file to process
        
        Returns:
            tuple: (success: bool, results: list)
        """
        print(f"Starting batch execution for suite: {self.suite_name}")
        print(f"Input CSV: {input_csv_path}")
        
        for i, batch_config in enumerate(batch_configs, 1):
            batch_name = batch_config.get('name', f'Batch {i}')
            
            script_base_path = batch_config.get('script')
            if not script_base_path:
                error_msg = f"'script' key missing in batch config: {batch_name}"
                print(f"  âœ— {error_msg}")
                self._record_failure(batch_name, None, error_msg)
                return False, self.batch_results

            script_path = self._resolve_script_path(script_base_path)

            print(f"\n[{i}/{len(batch_configs)}] Executing: {batch_name}")
            print(f"  Platform: {self.os_name} -> Resolved Script: {script_path}")
            # --- MODIFICATION END ---
            
            # Validate script exists (local only)
            if not self.remote_runner:
                is_valid, error_msg = self._validate_script(script_path)
                if not is_valid:
                    print(f"  FAIL {error_msg}")
                    self._record_failure(batch_name, str(script_path), error_msg)
                    return False, self.batch_results

            # Handle input file copying if required
            if batch_config.get('copy_input_file_to'):
                copy_dest = batch_config['copy_input_file_to']
                success, error_msg = self._copy_input_file(input_csv_path, copy_dest)
                if not success:
                    print(f"  âœ— File copy failed: {error_msg}")
                    self._record_failure(batch_name, str(script_path), f"File copy error: {error_msg}")
                    return False, self.batch_results
                print(f"  OK Input file copied to: {copy_dest}")

            # Optional script arguments
            args = batch_config.get('args', [])
            if args is None:
                args = []
            if not isinstance(args, (list, tuple)):
                error_msg = f"'args' must be a list for batch: {batch_name}"
                print(f"  FAIL {error_msg}")
                self._record_failure(batch_name, str(script_path), error_msg)
                return False, self.batch_results
            args = [str(a) for a in args]

            # Execute the script
            log_file = batch_config.get('log_file', self._default_log_file(i, batch_name))
            log_path = self.output_dir / log_file
            
            print(f"  Running script (logging to {log_path})...")
            start_time = datetime.now()
            
            exit_code, error_msg = self._run_script(str(script_path), log_path, args)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Check result
            if exit_code != 0:
                print(f"  âœ— Script failed with exit code: {exit_code}")
                print(f"  Check log for details: {log_path}")
                self._record_failure(
                    batch_name,
                    str(script_path),
                    f"Script exited with code {exit_code}. See log: {log_path}",
                    exit_code,
                    duration,
                    str(log_path),
                    start_time,
                    end_time
                )
                return False, self.batch_results
            
            print(f"  OK Completed successfully in {duration:.2f}s")
            self._record_success(
                batch_name,
                str(script_path),
                duration,
                str(log_path),
                start_time,
                end_time
            )
        
        print(f"\nOK All {len(batch_configs)} batch(es) completed successfully")
        return True, self.batch_results
    
    def _copy_input_file(self, source_path, dest_location):
        """
        Copy input CSV file to specified location
        """
        try:
            return self.input_delivery.deliver(source_path, dest_location)
        except Exception as e:
            return False, str(e)

    def _resolve_script_path(self, script_base_path):
        if self.remote_runner and self.os_name != "Windows":
            return str(Path(script_base_path).with_suffix('.sh').as_posix())
        if self.os_name == "Windows":
            return Path(script_base_path).with_suffix('.bat')
        return Path(script_base_path).with_suffix('.sh')

    @staticmethod
    def _default_log_file(index, batch_name):
        safe_name = batch_name.strip().replace(" ", "_").replace("/", "_")
        return f"batch_{index:02d}_{safe_name}.log"

    def _validate_script(self, script_path):
        if not script_path.exists():
            return False, f"Script not found: {script_path}"
        if not script_path.is_file():
            return False, f"Script is not a file: {script_path}"
        if not os.access(script_path, os.R_OK):
            return False, f"Script not readable: {script_path}"
        return True, None
    
    def _run_script(self, script_path, log_path, args=None):
        """
        Execute shell script and capture output to log file.
        This no longer modifies script permissions.
        """
        if self.remote_runner:
            return self.remote_runner.run(script_path, log_path, self.build_command, args)

        try:
            script = Path(script_path)
            
            with open(log_path, 'w') as log_file:
                log_file.write(f"=== Batch Execution Log ===\n")
                log_file.write(f"Script: {script_path}\n")
                log_file.write(f"Start Time: {datetime.now().isoformat()}\n")
                log_file.write(f"{'='*50}\n\n")
                
                command = self.build_command(str(script.absolute()), self.os_name, self.shell, args)
                result = subprocess.run(
                    command,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    cwd=script.parent,
                    text=True
                )
                
                log_file.write(f"\n{'='*50}\n")
                log_file.write(f"End Time: {datetime.now().isoformat()}\n")
                log_file.write(f"Exit Code: {result.returncode}\n")
            
            return result.returncode, None
            
        except Exception as e:
            error_msg = f"Exception running script: {str(e)}"
            try:
                with open(log_path, 'a') as log_file:
                    log_file.write(f"\n\nERROR: {error_msg}\n")
            except:
                pass
            return -1, error_msg
    
    @staticmethod
    def build_command(script_path, os_name, shell=None, args=None):
        args = [str(a) for a in (args or [])]
        if os_name == "Windows":
            return ["cmd.exe", "/c", script_path, *args]
        if shell:
            return [shell, script_path, *args]
        if shutil.which("bash"):
            return ["bash", script_path, *args]
        return ["sh", script_path, *args]

    def _record_success(self, batch_name, script_path, duration, log_file, start_time, end_time):
        """Record successful batch execution"""
        self.batch_results.append({
            'batch_name': batch_name,
            'script': script_path,
            'status': 'SUCCESS',
            'exit_code': 0,
            'duration_seconds': round(duration, 2),
            'log_file': log_file,
            'timestamp': datetime.now().isoformat(),
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat()
        })
    
    def _record_failure(
        self,
        batch_name,
        script_path,
        error_msg,
        exit_code=-1,
        duration=0,
        log_file=None,
        start_time=None,
        end_time=None
    ):
        """Record failed batch execution"""
        start_iso = start_time.isoformat() if start_time else None
        end_iso = end_time.isoformat() if end_time else None
        self.batch_results.append({
            'batch_name': batch_name,
            'script': script_path,
            'status': 'FAILED',
            'exit_code': exit_code,
            'error': error_msg,
            'duration_seconds': round(duration, 2),
            'log_file': log_file,
            'timestamp': datetime.now().isoformat(),
            'start_time': start_iso,
            'end_time': end_iso
        })


