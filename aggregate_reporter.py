"""
Aggregate Reporter
Combines results from multiple test suites into a single report
"""

import json
from datetime import datetime
from pathlib import Path


class AggregateReporter:
    """Generates aggregate reports across multiple test suites"""
    
    def __init__(self, reporting_config):
        """
        Initialize aggregate reporter
        
        Args:
            reporting_config: Reporting section from manifest
        """
        output_dir = reporting_config.get('output_dir', 'reports')
        output_file = reporting_config.get('aggregate_report', 'aggregate_summary.json')
        
        # Ensure output directory exists
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Set output file path
        self.output_file = self.output_dir / output_file
        
        # Track results
        self.suite_results = []
        self.start_time = datetime.now()
    
    def add_suite_result(self, name, passed, total_rows, passed_rows, 
                         failed_rows, execution_time, report_file=None, error=None):
        """
        Add results from a single test suite
        
        Args:
            name: Suite name
            passed: Whether suite passed
            total_rows: Total rows validated
            passed_rows: Rows that passed validation
            failed_rows: Rows that failed validation
            execution_time: Execution time in seconds
            report_file: Path to detailed suite report
            error: Error message if suite crashed
        """
        result = {
            'name': name,
            'passed': passed,
            'total_rows': total_rows,
            'passed_rows': passed_rows,
            'failed_rows': failed_rows,
            'pass_rate': (passed_rows / total_rows * 100) if total_rows > 0 else 0,
            'execution_time_seconds': round(execution_time, 2)
        }
        
        if report_file:
            result['report_file'] = report_file
        
        if error:
            result['error'] = error
        
        self.suite_results.append(result)
    
    def get_summary(self):
        """
        Calculate aggregate summary statistics
        
        Returns:
            dict: Summary statistics
        """
        total_suites = len(self.suite_results)
        passed_suites = sum(1 for r in self.suite_results if r['passed'])
        failed_suites = total_suites - passed_suites
        
        total_rows = sum(r['total_rows'] for r in self.suite_results)
        total_passed_rows = sum(r['passed_rows'] for r in self.suite_results)
        total_failed_rows = sum(r['failed_rows'] for r in self.suite_results)
        
        overall_pass_rate = (total_passed_rows / total_rows * 100) if total_rows > 0 else 0
        
        total_time = sum(r['execution_time_seconds'] for r in self.suite_results)
        
        return {
            'total_suites': total_suites,
            'passed_suites': passed_suites,
            'failed_suites': failed_suites,
            'suite_pass_rate': (passed_suites / total_suites * 100) if total_suites > 0 else 0,
            'total_rows_validated': total_rows,
            'total_passed_rows': total_passed_rows,
            'total_failed_rows': total_failed_rows,
            'overall_pass_rate': overall_pass_rate,
            'total_execution_time': round(total_time, 2)
        }
    
    def save_report(self):
        """
        Generate and save aggregate report as JSON
        """
        end_time = datetime.now()
        
        report = {
            'summary': self.get_summary(),
            'execution': {
                'start_time': self.start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'duration_seconds': round((end_time - self.start_time).total_seconds(), 2)
            },
            'suite_results': self.suite_results
        }
        
        with open(self.output_file, 'w') as f:
            json.dump(report, f, indent=2)
    
    def get_failed_suites(self):
        """
        Get list of failed suite names
        
        Returns:
            list: Names of failed suites
        """
        return [r['name'] for r in self.suite_results if not r['passed']]