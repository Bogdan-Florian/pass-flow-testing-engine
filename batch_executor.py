"""
Batch Executor
Executes shell scripts sequentially before validation tests.
Intelligently selects .bat or .sh script based on the operating system.
"""

import subprocess
import shutil
import platform
from pathlib import Path
from datetime import datetime


class BatchExecutor:
    """Executes batch scripts with logging and error handling"""
    
    def __init__(self, suite_name, output_dir="reports"):
        """
        Initialize batch executor
        
        Args:
            suite_name: Name of the test suite (for logging)
            output_dir: Directory to store batch log files
        """
        self.suite_name = suite_name
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
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
                print(f"  ✗ {error_msg}")
                self._record_failure(batch_name, None, error_msg)
                return False, self.batch_results

            # Determine the correct file extension based on the OS
            if platform.system() == "Windows":
                script_path = Path(script_base_path).with_suffix('.bat')
            else:
                # Assume Linux/macOS for development
                script_path = Path(script_base_path).with_suffix('.sh')

            print(f"\n[{i}/{len(batch_configs)}] Executing: {batch_name}")
            print(f"  Platform: {platform.system()} -> Resolved Script: {script_path}")
            # --- MODIFICATION END ---
            
            # Validate script exists
            if not script_path.exists():
                error_msg = f"Script not found: {script_path}"
                print(f"  ✗ {error_msg}")
                self._record_failure(batch_name, str(script_path), error_msg)
                return False, self.batch_results
            
            # Handle input file copying if required
            if batch_config.get('copy_input_file_to'):
                copy_dest = batch_config['copy_input_file_to']
                success, error_msg = self._copy_input_file(input_csv_path, copy_dest)
                if not success:
                    print(f"  ✗ File copy failed: {error_msg}")
                    self._record_failure(batch_name, str(script_path), f"File copy error: {error_msg}")
                    return False, self.batch_results
                print(f"  ✓ Input file copied to: {copy_dest}")
            
            # Execute the script
            log_file = batch_config.get('log_file', f'batch_{i}_{batch_name.replace(" ", "_")}.log')
            log_path = self.output_dir / log_file
            
            print(f"  Running script (logging to {log_path})...")
            start_time = datetime.now()
            
            exit_code, error_msg = self._run_script(str(script_path), log_path)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Check result
            if exit_code != 0:
                print(f"  ✗ Script failed with exit code: {exit_code}")
                print(f"  Check log for details: {log_path}")
                self._record_failure(
                    batch_name, 
                    str(script_path),
                    f"Script exited with code {exit_code}. See log: {log_path}",
                    exit_code,
                    duration,
                    str(log_path)
                )
                return False, self.batch_results
            
            print(f"  ✓ Completed successfully in {duration:.2f}s")
            self._record_success(batch_name, str(script_path), duration, str(log_path))
        
        print(f"\n✓ All {len(batch_configs)} batch(es) completed successfully")
        return True, self.batch_results
    
    def _copy_input_file(self, source_path, dest_location):
        """
        Copy input CSV file to specified location
        """
        try:
            source = Path(source_path)
            if not source.exists():
                return False, f"Source file not found: {source_path}"
            
            dest_dir = Path(dest_location)
            dest_dir.mkdir(parents=True, exist_ok=True)
            
            dest_file = dest_dir / source.name
            shutil.copy2(source, dest_file)
            
            return True, None
        except Exception as e:
            return False, str(e)
    
    def _run_script(self, script_path, log_path):
        """
        Execute shell script and capture output to log file.
        This no longer modifies script permissions.
        """
        try:
            script = Path(script_path)
            
            with open(log_path, 'w') as log_file:
                log_file.write(f"=== Batch Execution Log ===\n")
                log_file.write(f"Script: {script_path}\n")
                log_file.write(f"Start Time: {datetime.now().isoformat()}\n")
                log_file.write(f"{'='*50}\n\n")
                
                result = subprocess.run(
                    [str(script.absolute())],
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
    
    def _record_success(self, batch_name, script_path, duration, log_file):
        """Record successful batch execution"""
        self.batch_results.append({
            'batch_name': batch_name,
            'script': script_path,
            'status': 'SUCCESS',
            'exit_code': 0,
            'duration_seconds': round(duration, 2),
            'log_file': log_file,
            'timestamp': datetime.now().isoformat()
        })
    
    def _record_failure(self, batch_name, script_path, error_msg, exit_code=-1, duration=0, log_file=None):
        """Record failed batch execution"""
        self.batch_results.append({
            'batch_name': batch_name,
            'script': script_path,
            'status': 'FAILED',
            'exit_code': exit_code,
            'error': error_msg,
            'duration_seconds': round(duration, 2),
            'log_file': log_file,
            'timestamp': datetime.now().isoformat()
        })