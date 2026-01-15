"""
Test Suite Runner
Orchestrates execution of multiple validation test suites
"""

import sys
import argparse
import shutil
from pathlib import Path
from datetime import datetime

# Assuming your other modules are available
from manifest_loader import ManifestLoader
from config_loader import ConfigLoader
from file_processor import get_processor, get_modifier  # Unified file handling (CSV + Excel)
from validator import Validator
from reporter import Reporter
from aggregate_reporter import AggregateReporter
from batch_executor import BatchExecutor, LocalCopyDelivery, SftpDelivery, SshRunner

# A sensible default if date_format is ever omitted from a suite's config in the manifest
DEFAULT_DATE_FORMAT = '%Y-%m-%d'

class SuiteRunner:
    """Runs multiple test suites defined in a manifest"""

    def __init__(self, manifest_path, db_url_override=None):
        """
        Initialize suite runner
        """
        self.manifest_path = Path(manifest_path)
        self.manifest = ManifestLoader.load(manifest_path)
        self.db_url = db_url_override or self.manifest.get('database', {}).get('connection_url')
        self.aggregate_reporter = AggregateReporter(self.manifest.get('reporting', {}))

        if not self.db_url:
            raise ValueError("Database connection URL required (in manifest or --db-url)")

    def run_all(self, suite_filter=None, tags_filter=None):
        """
        Run all enabled test suites
        """
        execution_config = self.manifest.get('execution', {})
        stop_on_critical = execution_config.get('stop_on_critical_failure', True)

        suites_to_run = self._filter_suites(suite_filter, tags_filter)

        if not suites_to_run:
            print("No test suites to run (all disabled or filtered out)")
            return True

        all_passed = True

        for i, suite_config in enumerate(suites_to_run, 1):
            suite_name = suite_config['name']
            is_critical = suite_config.get('critical', False)

            print(f"[{i}/{len(suites_to_run)}] {suite_name}")
            print(f"{'-'*70}")

            try:
                passed = self._run_suite(suite_config)

                if not passed:
                    all_passed = False
                    if is_critical and stop_on_critical:
                        print(f"\nERROR CRITICAL suite failed: {suite_name}")
                        print("Stopping execution (stop_on_critical_failure=true)")
                        break

            except Exception as e:
                print(f"ERROR Suite error: {e}")
                all_passed = False
                if is_critical and stop_on_critical:
                    print(f"\nERROR CRITICAL suite errored: {suite_name}")
                    print("Stopping execution")
                    break

            print()

        print(f"{'-'*70}")
        self._print_summary()
        self.aggregate_reporter.save_report()

        return all_passed

    def _run_suite(self, suite_config):
        """
        Run a single test suite, including pre-validation batches.
        """
        start_time = datetime.now()
        suite_name = suite_config['name']
        config_path = self._resolve_path(suite_config['config'])

        try:
            config = ConfigLoader.load(config_path)
            batch_results = []
            source_path = self._resolve_path(config['file']['path'], config_path.parent)

            # Get file settings (works for CSV and Excel)
            has_header = config['file'].get('has_header', True)
            file_settings = {
                'delimiter': config['file'].get('delimiter', ','),
                'encoding': config['file'].get('encoding', 'utf-8'),
                'has_header': has_header,
                'sheet': config['file'].get('sheet'),  # Excel sheet name/index
            }

            # Auto-increment primary key if configured (works for CSV and Excel)
            pk_config = config.get('primary_key', {})
            if pk_config.get('auto_increment'):
                modifier = get_modifier(source_path, **file_settings)
                rows_modified = modifier.increment_primary_key(
                    column=pk_config.get('column'),
                    column_index=pk_config.get('column_index')
                )
                print(f"  Auto-incremented primary key in {rows_modified} row(s)")

            validation_copy_path = config.get('execution', {}).get('validation_copy_path')
            if validation_copy_path:
                validation_copy_path = self._resolve_path(validation_copy_path, config_path.parent)
                validation_copy_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, validation_copy_path)
                file_validation_path = validation_copy_path
            else:
                file_validation_path = source_path

            # Step 1 - Execute batch scripts if configured
            batch_configs = config.get('batches', [])
            if batch_configs:
                print(f"  Found {len(batch_configs)} batch(es) to execute...")
                suite_report_path = self._get_suite_report_path(suite_name, config)
                suite_specific_output_dir = suite_report_path.parent

                print(f"  Batch output directory: {suite_specific_output_dir}")
                input_delivery = self._build_input_delivery()
                remote_runner = self._build_remote_runner()
                os_name = remote_runner.os_name if remote_runner else None
                executor = BatchExecutor(
                        suite_name=suite_name,
                        output_dir=suite_specific_output_dir,
                        input_delivery=input_delivery,
                        os_name=os_name,
                        remote_runner=remote_runner
                    )
                # Batches might need access to the data file path
                file_for_batches = source_path

                success, batch_results = executor.execute_batches(
                    batch_configs,
                    str(file_for_batches)
                )

                if not success:
                    print("  ERROR BATCH EXECUTION FAILED. Skipping validation.")
                    end_time = datetime.now()
                    execution_time = (end_time - start_time).total_seconds()
                    
                    # Generate a report containing only the batch failure information
                    output_file = self._get_suite_report_path(suite_name, config)
                    reporter = Reporter(output_file)
                    reporter.add_batch_results(batch_results)
                    reporter.generate_report()

                    self.aggregate_reporter.add_suite_result(
                        name=suite_name, passed=False,
                        total_rows=0, passed_rows=0, failed_rows=0,
                        execution_time=execution_time,
                        report_file=str(output_file),
                        error="Batch execution failed"
                    )
                    print(f"  Report: {output_file}")
                    return False  # Indicate suite failure
                else:
                    print("  OK All batches completed successfully.")


            # Step 2 - Proceed with data validation (CSV or Excel)
            data_file = file_validation_path
            processor = get_processor(data_file, **file_settings)
            total_rows = processor.count_rows()

            date_format = suite_config.get('date_format', DEFAULT_DATE_FORMAT)
            timeout = config.get('execution', {}).get('timeout_seconds', 30)

            validator = Validator(
                db_url=self.db_url,
                date_format=date_format,
                timeout_seconds=timeout
            )

            output_file = self._get_suite_report_path(suite_name, config)
            reporter = Reporter(output_file)

            # Add successful batch results to the report
            if batch_results:
                reporter.add_batch_results(batch_results)

            print(f"  Data: {data_file.name} ({total_rows} rows)")
            print(f"  Validations: {len(config['validations'])}")
            print(f"  Date Format (for CSV): '{date_format}'")

            stop_on_error = config.get('execution', {}).get('stop_on_first_error', False)

            for row_num, row_data in processor.read_rows():
                row_results = validator.validate_row(
                    row_num=row_num,
                    row_data=row_data,
                    variables_config=config.get('variables', {}),
                    validations=config['validations']
                )

                reporter.add_row_result(row_num, row_data, row_results)

                if stop_on_error and row_results['has_failures']:
                    print(f"  Stopped at row {row_num} (stop_on_first_error)")
                    break

            reporter.generate_report()

            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()

            self.aggregate_reporter.add_suite_result(
                name=suite_name,
                passed=(reporter.failed_rows == 0),
                total_rows=reporter.total_rows,
                passed_rows=reporter.passed_rows,
                failed_rows=reporter.failed_rows,
                execution_time=execution_time,
                report_file=str(output_file)
            )

            status = "OK PASSED" if reporter.failed_rows == 0 else "ERROR FAILED"
            print(f"  {status} - {reporter.passed_rows}/{reporter.total_rows} rows valid")
            print(f"  Time: {execution_time:.2f}s")
            print(f"  Report: {output_file}")

            return reporter.failed_rows == 0

        except Exception as e:
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()

            self.aggregate_reporter.add_suite_result(
                name=suite_name, passed=False,
                total_rows=0, passed_rows=0, failed_rows=0,
                execution_time=execution_time, error=str(e)
            )

            raise

    def _filter_suites(self, suite_filter, tags_filter):
        """Filter which suites to run based on criteria"""
        suites = self.manifest.get('suites', [])
        filtered = []
        for suite in suites:
            if not suite.get('enabled', True): continue
            if suite_filter and suite['name'] not in suite_filter: continue
            if tags_filter:
                suite_tags = suite.get('tags', [])
                if not any(tag in suite_tags for tag in tags_filter): continue
            filtered.append(suite)
        return filtered

    def _resolve_path(self, path, base_path=None):
        """Resolve path relative to manifest or base path"""
        if base_path is None: base_path = self.manifest_path.parent
        path = Path(path)
        return path if path.is_absolute() else (base_path / path).resolve()

    def _get_suite_report_path(self, suite_name, config):
        """Generate output path for suite report inside a dedicated folder."""
        # If a specific output file is configured for the suite, use that path directly.
        # This allows for overrides and preserves existing behavior.
        suite_output = config.get('reporting', {}).get('output_file')
        if suite_output:
            return self._resolve_path(suite_output, self.manifest_path.parent)

        # Get the main reports directory from the manifest (e.g., 'reports')
        base_output_dir = Path(self.manifest.get('reporting', {}).get('output_dir', 'reports'))

        # Create a "safe" version of the suite name to use for the folder and file.
        safe_name = suite_name.lower().replace(' ', '_').replace('/', '_')

        # NEW: Create a dedicated subdirectory for this specific suite's report.
        suite_specific_dir = base_output_dir / safe_name
        suite_specific_dir.mkdir(parents=True, exist_ok=True)

        # Return the full path to the report file inside the new dedicated directory.
        return suite_specific_dir / f"{safe_name}_results.json"

    def _print_summary(self):
        """Print aggregate summary"""
        summary = self.aggregate_reporter.get_summary()
        print("AGGREGATE SUMMARY")
        print(f"{'-'*70}")
        print(f"Total suites run: {summary['total_suites']}")
        print(f"Passed: {summary['passed_suites']}")
        print(f"Failed: {summary['failed_suites']}")
        print(f"Total rows validated: {summary['total_rows_validated']}")
        print(f"Overall pass rate: {summary['overall_pass_rate']:.1f}%")
        print(f"Total execution time: {summary['total_execution_time']:.2f}s")
        print(f"\nAggregate report: {self.aggregate_reporter.output_file}")

    def _mask_db_url(self, url):
        """Mask password in database URL for display"""
        if not url: return "Not configured"
        if '@' in url and ':' in url:
            parts = url.split('@')
            if len(parts) == 2 and '://' in parts[0]:
                protocol, creds = parts[0].split('://')
                user = creds.split(':')[0]
                return f"{protocol}://{user}:****@{parts[1]}"
        return url

    def _build_input_delivery(self):
        """Select input delivery mechanism based on manifest."""
        sftp_cfg = self.manifest.get('sftp')
        if not sftp_cfg:
            return LocalCopyDelivery()
        return SftpDelivery(
            host=sftp_cfg.get('host'),
            port=sftp_cfg.get('port', 22),
            username=sftp_cfg.get('username'),
            password=sftp_cfg.get('password'),
            private_key=sftp_cfg.get('private_key')
        )

    def _build_remote_runner(self):
        """Select remote runner (SSH) if configured."""
        ssh_cfg = self.manifest.get('ssh')
        if not ssh_cfg:
            return None
        return SshRunner(
            host=ssh_cfg.get('host'),
            port=ssh_cfg.get('port', 22),
            username=ssh_cfg.get('username'),
            password=ssh_cfg.get('password'),
            private_key=ssh_cfg.get('private_key'),
            os_name=ssh_cfg.get('os', 'Linux'),
            shell=ssh_cfg.get('shell')
        )

def main():
    """Main entry point for suite runner"""
    parser = argparse.ArgumentParser(
        description='Run multiple validation test suites',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all enabled suites
  python run_suites.py test_manifest.yaml

  # Run specific suites
  python run_suites.py test_manifest.yaml --suite "Orders" --suite "Customers"

  # Run suites with specific tags
  python run_suites.py test_manifest.yaml --tags critical

  # Override database URL
  python run_suites.py test_manifest.yaml --db-url "postgresql://user:pass@host/db"
        """
    )

    parser.add_argument('manifest', help='Path to test manifest YAML file')
    parser.add_argument('--db-url', help='Database connection URL (overrides manifest)')
    parser.add_argument('--suite', action='append', dest='suites', help='Run specific suite(s) by name')
    parser.add_argument('--tags', action='append', help='Run suites with specific tag(s)')

    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"Error: Manifest file not found: {manifest_path}")
        sys.exit(1)

    try:
        runner = SuiteRunner(manifest_path, args.db_url)
        all_passed = runner.run_all(suite_filter=args.suites, tags_filter=args.tags)
        sys.exit(0 if all_passed else 1)

    except Exception as e:
        print(f"\nERROR Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
