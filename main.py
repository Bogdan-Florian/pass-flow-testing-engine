"""
Data Validation Testing Framework
Main entry point - orchestrates the validation process
"""

import sys
import argparse
from pathlib import Path
from config_loader import ConfigLoader
from csv_processor import CSVProcessor
from validator import Validator
from reporter import Reporter


def main():
    """
    Main execution flow:
    1. Load YAML config
    2. Connect to database
    3. Process each CSV row
    4. Generate report
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Validate database records against CSV data')
    parser.add_argument('config', help='Path to YAML configuration file')
    parser.add_argument('--db-url', help='Database connection URL (e.g., postgresql://user:pass@host/db)')
    args = parser.parse_args()
    
    # Check if config file exists
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}")
        sys.exit(1)
    
    print(f"Loading configuration from: {config_path}")
    
    try:
        # Step 1: Load and parse YAML configuration
        config = ConfigLoader.load(config_path)
        print(f"✓ Configuration loaded successfully")
        print(f"  CSV file: {config['file']['path']}")
        print(f"  Validations: {len(config['validations'])}")
        
        # Step 2: Initialize CSV processor
        csv_file = config['file']['path']
        delimiter = config['file'].get('delimiter', ',')
        encoding = config['file'].get('encoding', 'utf-8')
        
        processor = CSVProcessor(csv_file, delimiter, encoding)
        total_rows = processor.count_rows()
        print(f"✓ CSV file loaded: {total_rows} rows to validate")
        
        # Step 3: Initialize validator with database connection
        db_url = args.db_url or config.get('database', {}).get('connection_url')
        if not db_url:
            print("Error: Database connection URL required (--db-url or in config)")
            sys.exit(1)
        
        timeout = config.get('execution', {}).get('timeout_seconds', 30)
        validator = Validator(db_url, timeout)
        print(f"✓ Connected to database")
        
        # Step 4: Initialize reporter
        output_file = config.get('reporting', {}).get('output_file', 'validation_results.json')
        reporter = Reporter(output_file)
        
        # Step 5: Process each CSV row
        print(f"\nProcessing rows...")
        stop_on_error = config.get('execution', {}).get('stop_on_first_error', False)
        
        for row_num, row_data in processor.read_rows():
            print(f"  Row {row_num}/{total_rows}...", end='\r')
            
            # Run all validations for this row
            row_results = validator.validate_row(
                row_num=row_num,
                row_data=row_data,
                variables_config=config.get('variables', {}),
                validations=config['validations']
            )
            
            # Record results
            reporter.add_row_result(row_num, row_data, row_results)
            
            # Check if we should stop on failure
            if stop_on_error and row_results['has_failures']:
                print(f"\n✗ Stopping on first error at row {row_num}")
                break
        
        print(f"\n✓ Validation complete")
        
        # Step 6: Generate and save report
        reporter.generate_report()
        print(f"\n{'='*60}")
        print(f"SUMMARY")
        print(f"{'='*60}")
        print(f"Total rows processed: {reporter.total_rows}")
        print(f"Passed: {reporter.passed_rows} ({reporter.pass_rate:.1f}%)")
        print(f"Failed: {reporter.failed_rows}")
        print(f"Report saved to: {output_file}")
        
        # Exit with error code if any validations failed
        sys.exit(0 if reporter.failed_rows == 0 else 1)
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()