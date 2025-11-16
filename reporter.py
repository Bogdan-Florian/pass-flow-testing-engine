"""
Reporter
Collects validation results and generates output reports
"""

import json
from datetime import datetime


class Reporter:
    """Generates validation reports"""
    
    def __init__(self, output_file):
        """
        Initialize reporter
        
        Args:
            output_file: Path to save JSON report
        """
        self.output_file = output_file
        self.results = []
        self.start_time = datetime.now()
        
        self.total_rows = 0
        self.passed_rows = 0
        self.failed_rows = 0
        
        # NEW: Store batch execution results
        self.batch_results = []
    
    def add_batch_results(self, batch_results):
        """
        Add batch execution results to report
        
        Args:
            batch_results: List of batch execution result dictionaries
        """
        self.batch_results = batch_results
    
    def add_row_result(self, row_num, row_data, validation_results):
        """
        Add validation results for a single CSV row
        
        Args:
            row_num: CSV row number
            row_data: Dictionary of CSV column values
            validation_results: Results from validator
        """
        self.total_rows += 1
        
        if validation_results['has_failures']:
            self.failed_rows += 1
        else:
            self.passed_rows += 1
        
        # Store results
        self.results.append({
            'row_number': row_num,
            'csv_data': row_data,
            'passed': not validation_results['has_failures'],
            'validations': validation_results['validations']
        })
    
    def generate_report(self):
        """
        Generate and save final validation report as JSON
        """
        end_time = datetime.now()
        execution_time = (end_time - self.start_time).total_seconds()
        
        # Build report with batch execution section
        report = {
            'summary': {
                'total_rows': self.total_rows,
                'passed_rows': self.passed_rows,
                'failed_rows': self.failed_rows,
                'pass_rate': (self.passed_rows / self.total_rows * 100) if self.total_rows > 0 else 0,
                'execution_time_seconds': round(execution_time, 2),
                'timestamp': datetime.now().isoformat()
            },
            'failures': self._extract_failures(),
            'all_results': self.results
        }
        
        # NEW: Add batch execution section if batches were run
        if self.batch_results:
            report['batch_execution'] = {
                'total_batches': len(self.batch_results),
                'successful_batches': sum(1 for b in self.batch_results if b['status'] == 'SUCCESS'),
                'failed_batches': sum(1 for b in self.batch_results if b['status'] == 'FAILED'),
                'batches': self.batch_results
            }
        
        # Save to file
        with open(self.output_file, 'w') as f:
            json.dump(report, f, indent=2)
    
    def _extract_failures(self):
        """
        Extract only the failed validations for easy review
        
        Returns:
            list: Failed validation details
        """
        failures = []
        
        for result in self.results:
            if not result['passed']:
                for validation in result['validations']:
                    if not validation['passed']:
                        failure = {
                            'row_number': result['row_number'],
                            'csv_row_data': result['csv_data'],
                            'validation_name': validation['name'],
                            'errors': validation['errors']
                        }
                        
                        # Add SQL if available
                        if 'sql' in validation:
                            failure['sql_executed'] = validation['sql']
                        
                        # Add actual row count if available
                        if 'actual_row_count' in validation:
                            failure['actual_row_count'] = validation['actual_row_count']
                        
                        failures.append(failure)
        
        return failures
    
    @property
    def pass_rate(self):
        """Calculate pass rate percentage"""
        if self.total_rows == 0:
            return 0.0
        return (self.passed_rows / self.total_rows) * 100