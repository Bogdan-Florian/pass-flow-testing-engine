# PASS Flow Testing Engine - User Guide

## For Business Analysts

---

## Table of Contents

1. [What is This Tool?](#what-is-this-tool)
2. [Quick Start](#quick-start)
3. [Understanding the Folder Structure](#understanding-the-folder-structure)
4. [Creating Your First Test](#creating-your-first-test)
5. [The Manifest File](#the-manifest-file)
6. [The Config File](#the-config-file)
7. [Writing CSV Test Data](#writing-csv-test-data)
8. [Defining Variables](#defining-variables)
9. [Writing SQL Validations](#writing-sql-validations)
10. [Running Batch Scripts](#running-batch-scripts)
11. [Auto-Increment Primary Keys](#auto-increment-primary-keys)
12. [Reading the Reports](#reading-the-reports)
13. [Common Examples](#common-examples)
14. [Troubleshooting](#troubleshooting)

---

## What is This Tool?

The PASS Flow Testing Engine helps you **automatically test batch processes** that work with databases.

**In simple terms:**
1. You provide a CSV file with test data
2. The tool runs your batch scripts (which process that data)
3. The tool checks the database to verify the batches worked correctly
4. You get a report showing what passed and what failed

**Example scenario:**
- You have a batch that imports customer orders into a database
- You want to verify that after the batch runs, the orders appear correctly in the database
- This tool automates that verification process

---

## Quick Start

### Running a Test

Open Command Prompt (cmd) and run:

```
run_suites.exe my-manifest.yaml
```

That's it! The tool will:
1. Read your test configuration
2. Run any batch scripts you specified
3. Check the database
4. Generate a report

### What You Need

1. **run_suites.exe** - The testing tool
2. **A manifest file** (.yaml) - Tells the tool which tests to run
3. **A config file** (.yaml) - Describes what to test
4. **A CSV file** - Your test data
5. **Batch scripts** (.bat or .sh) - The processes you want to test

---

## Understanding the Folder Structure

We recommend organizing your tests like this:

```
my_tests/
│
├── run_suites.exe              <-- The tool
├── test-manifest.yaml          <-- Your manifest file
│
├── orders_test/                <-- A test suite folder
│   ├── config.yaml             <-- Test configuration
│   ├── test_data.csv           <-- Your test data
│   └── batches/                <-- Batch scripts
│       ├── import_orders.bat
│       └── process_orders.bat
│
├── customers_test/             <-- Another test suite
│   ├── config.yaml
│   ├── test_data.csv
│   └── batches/
│       └── import_customers.bat
│
└── reports/                    <-- Reports go here (auto-created)
    └── ...
```

---

## Creating Your First Test

Let's create a simple test step by step.

### Step 1: Create the Test Data (CSV)

Create a file called `test_data.csv`:

```
OrderID|CustomerName|Amount|Status
ORD-0001|John Smith|150.00|NEW
ORD-0002|Jane Doe|275.50|NEW
ORD-0003|Bob Wilson|99.99|NEW
```

**Note:** Use `|` (pipe) as the separator - it's easier to read than commas.

### Step 2: Create the Config File

Create a file called `config.yaml`:

```yaml
file:
  path: test_data.csv
  delimiter: '|'
  has_header: true

variables:
  order_id: ${row.OrderID}
  customer: ${row.CustomerName}
  amount: ${row.Amount}:decimal
  status: ${row.Status}

validations:
  - name: order_exists_in_database
    sql: |
      SELECT order_id, customer_name, amount, status
      FROM orders
      WHERE order_id = :order_id
    expect:
      row_count: 1
      columns:
        customer_name: ${customer}
        amount: ${amount}
        status: "PROCESSED"
```

### Step 3: Create the Manifest File

Create a file called `test-manifest.yaml`:

```yaml
version: 1

database:
  connection_url: postgresql://user:password@server:5432/mydb

suites:
  - name: Order Processing Test
    enabled: true
    config: orders_test/config.yaml

reporting:
  output_dir: reports
```

### Step 4: Run the Test

```
run_suites.exe test-manifest.yaml
```

---

## The Manifest File

The manifest file is your "master control" - it tells the tool:
- Which database to connect to
- Which tests to run
- Where to save reports

### Basic Structure

```yaml
version: 1

database:
  connection_url: postgresql://username:password@server:5432/database_name

suites:
  - name: My First Test
    enabled: true
    config: path/to/config.yaml

  - name: My Second Test
    enabled: true
    config: path/to/another/config.yaml

reporting:
  output_dir: reports
```

### Database Connection URLs

| Database   | Connection URL Format |
|------------|----------------------|
| PostgreSQL | `postgresql://user:pass@server:5432/dbname` |
| MySQL      | `mysql+pymysql://user:pass@server:3306/dbname` |
| SQLite     | `sqlite:///path/to/file.db` |
| SQL Server | `mssql+pyodbc://user:pass@server/dbname?driver=ODBC+Driver+17+for+SQL+Server` |

### Suite Options

```yaml
suites:
  - name: Critical Orders Test      # Display name
    enabled: true                   # Set to false to skip this test
    critical: true                  # If true, stop all tests if this fails
    config: orders/config.yaml      # Path to config file
    tags:                           # Optional tags for filtering
      - orders
      - critical
```

### Running Specific Tests

```bash
# Run only tests with a specific name
run_suites.exe manifest.yaml --suite "Order Processing Test"

# Run only tests with specific tags
run_suites.exe manifest.yaml --tags critical
```

---

## The Config File

The config file describes ONE test suite. It specifies:
- Where to find your test data
- What variables to extract from each row
- What SQL queries to run for validation
- What batch scripts to execute (optional)

### Complete Example

```yaml
# === FILE SETTINGS ===
file:
  path: test_data.csv        # Path to your CSV file
  delimiter: '|'             # Column separator (use ',' for comma)
  encoding: utf-8            # File encoding (usually utf-8)
  has_header: true           # Does the CSV have a header row?

# === PRIMARY KEY AUTO-INCREMENT (Optional) ===
primary_key:
  column: OrderID            # Which column contains the primary key
  auto_increment: true       # Increment before each run

# === BATCH SCRIPTS (Optional) ===
batches:
  - name: Import Orders
    script: batches/import_orders
    args:
      - "--mode=import"
      - "--validate=true"

# === VARIABLES ===
# Extract values from each CSV row
variables:
  order_id: ${row.OrderID}
  amount: ${row.Amount}:decimal
  order_date: ${row.OrderDate}:date

# === VALIDATIONS ===
# SQL queries to verify the data
validations:
  - name: check_order_exists
    sql: |
      SELECT * FROM orders WHERE order_id = :order_id
    expect:
      row_count: 1
      columns:
        amount: ${amount}

# === EXECUTION SETTINGS ===
execution:
  stop_on_first_error: false   # Continue even if a row fails
  timeout_seconds: 30          # Max time per query
```

---

## Writing CSV Test Data

### With Headers (Recommended)

```
OrderID|CustomerName|Amount|OrderDate|Status
ORD-0001|John Smith|150.00|2024-01-15|NEW
ORD-0002|Jane Doe|275.50|2024-01-16|NEW
```

Config:
```yaml
file:
  path: test_data.csv
  delimiter: '|'
  has_header: true

variables:
  order_id: ${row.OrderID}      # Use column name
  customer: ${row.CustomerName}
  amount: ${row.Amount}:decimal
```

### Without Headers

```
ORD-0001|John Smith|150.00|2024-01-15|NEW
ORD-0002|Jane Doe|275.50|2024-01-16|NEW
```

Config:
```yaml
file:
  path: test_data.csv
  delimiter: '|'
  has_header: false

variables:
  order_id: ${row.0}      # Use column number (starting from 0)
  customer: ${row.1}
  amount: ${row.2}:decimal
  order_date: ${row.3}:date
  status: ${row.4}
```

### Tips for CSV Files

1. **Use pipe `|` delimiter** - Easier to read than commas
2. **Avoid special characters** - Quotes, newlines can cause issues
3. **Keep it simple** - One row = one test case
4. **Check encoding** - Save as UTF-8 if using special characters

---

## Defining Variables

Variables let you extract values from your CSV and use them in SQL queries.

### Basic Syntax

```yaml
variables:
  my_variable: ${row.ColumnName}
```

### With Type Conversion

| Type | Syntax | Example |
|------|--------|---------|
| Text (default) | `${row.Column}` | `"ABC123"` |
| Decimal | `${row.Column}:decimal` | `150.00` |
| Integer | `${row.Column}:int` | `42` |
| Date | `${row.Column}:date` | `2024-01-15` |

### Example

CSV:
```
OrderID|Amount|Quantity|OrderDate
ORD-001|150.00|5|2024-01-15
```

Config:
```yaml
variables:
  order_id: ${row.OrderID}           # Text: "ORD-001"
  amount: ${row.Amount}:decimal      # Decimal: 150.00
  qty: ${row.Quantity}:int           # Integer: 5
  order_date: ${row.OrderDate}:date  # Date: 2024-01-15
```

### Using Variables in SQL

Variables become SQL parameters using `:variable_name`:

```yaml
validations:
  - name: check_order
    sql: |
      SELECT * FROM orders
      WHERE order_id = :order_id
      AND amount = :amount
    expect:
      row_count: 1
```

---

## Writing SQL Validations

Validations are SQL queries that check if your batch processed data correctly.

### Basic Structure

```yaml
validations:
  - name: descriptive_name_here
    sql: |
      SELECT column1, column2, column3
      FROM your_table
      WHERE some_column = :your_variable
    expect:
      row_count: 1
      columns:
        column1: expected_value
        column2: ${variable_from_csv}
```

### Expectation Options

#### Check Row Count

```yaml
expect:
  row_count: 1        # Exactly 1 row
  row_count: 0        # No rows (record should NOT exist)
  min_rows: 1         # At least 1 row
  max_rows: 10        # At most 10 rows
```

#### Check Column Values

```yaml
expect:
  columns:
    status: "COMPLETED"           # Exact text match
    amount: ${amount}             # Match variable from CSV
    is_active: 1                  # Numeric value
    processed_date: ${order_date} # Date comparison
```

#### Check NOT NULL

```yaml
expect:
  not_null:
    - transaction_id
    - processed_date
```

### Complete Example

```yaml
validations:
  # Check 1: Order was imported
  - name: order_imported
    sql: |
      SELECT order_id, customer_name, amount, status
      FROM orders
      WHERE order_id = :order_id
    expect:
      row_count: 1
      columns:
        customer_name: ${customer}
        amount: ${amount}
        status: "IMPORTED"

  # Check 2: Payment record was created
  - name: payment_created
    sql: |
      SELECT payment_id, order_id, amount, status
      FROM payments
      WHERE order_id = :order_id
    expect:
      row_count: 1
      columns:
        amount: ${amount}
        status: "PENDING"
      not_null:
        - payment_id

  # Check 3: No duplicate orders
  - name: no_duplicates
    sql: |
      SELECT COUNT(*) as cnt
      FROM orders
      WHERE order_id = :order_id
    expect:
      row_count: 1
      columns:
        cnt: 1
```

---

## Running Batch Scripts

You can run batch scripts (.bat for Windows, .sh for Linux) before validation.

### Basic Configuration

```yaml
batches:
  - name: Import Data
    script: batches/import_data     # No extension! Tool adds .bat or .sh

  - name: Process Data
    script: batches/process_data
```

### With Parameters

```yaml
batches:
  - name: Import Orders
    script: batches/import_orders
    args:
      - "--input-file=orders.csv"
      - "--mode=full"
      - "--validate=true"
```

### With Input File Delivery

If your batch needs the CSV file in a specific location:

```yaml
batches:
  - name: Import Orders
    script: batches/import_orders
    copy_input_file_to: system/input    # Copy CSV here before running
    log_file: import.log                 # Save output to this file
    args:
      - "--source=system/input"
```

### Long-Running Batches (Timeout)

By default, each batch has a **1 hour timeout**. For longer batches, increase the timeout:

```yaml
batches:
  - name: Import Large Dataset
    script: batches/import_large
    timeout: 3600          # 1 hour (default)

  - name: Process All Records
    script: batches/process_all
    timeout: 5400          # 1.5 hours (90 minutes)

  - name: Generate Reports
    script: batches/generate_reports
    timeout: 2700          # 45 minutes
```

**Timeout values are in seconds:**
| Time | Seconds |
|------|---------|
| 15 minutes | 900 |
| 30 minutes | 1800 |
| 45 minutes | 2700 |
| 1 hour | 3600 |
| 1.5 hours | 5400 |
| 2 hours | 7200 |

If a batch exceeds its timeout, it will be **terminated** and marked as failed. The next batch will NOT run (batches are sequential).

### Execution Order

1. **Primary key auto-increment** (if configured)
2. **Batch 1** runs
3. **Batch 2** runs
4. **Batch 3** runs
5. **SQL Validations** run for each CSV row

---

## Auto-Increment Primary Keys

If your test data has primary keys that must be unique each run, use auto-increment.

### How It Works

Before each test run, the tool increments the numeric suffix of your primary key:

```
ORD-0001  -->  ORD-0002  -->  ORD-0003  -->  ...
POL-0099  -->  POL-0100  -->  POL-0101  -->  ...
KEY9999   -->  KEY10000  -->  KEY10001  -->  ...
```

### Configuration

**With header row:**
```yaml
file:
  path: test_data.csv
  has_header: true

primary_key:
  column: OrderID         # Column name
  auto_increment: true
```

**Without header row:**
```yaml
file:
  path: test_data.csv
  has_header: false

primary_key:
  column_index: 0         # First column (0-based)
  auto_increment: true
```

### Important Notes

1. The CSV file is **modified** each time you run the test
2. Make sure your database seed data matches what the CSV will contain after increment
3. Keep a backup of your original CSV if needed

---

## Reading the Reports

After each run, the tool generates reports in the `reports/` folder.

### Report Structure

```
reports/
├── aggregate_summary.json       <-- Overall summary
└── my_test_suite/
    ├── my_test_suite_results.json   <-- Detailed results
    ├── batch1.log                    <-- Batch output
    └── batch2.log
```

### Understanding the Summary

```
AGGREGATE SUMMARY
----------------------------------------------------------------------
Total suites run: 3
Passed: 2
Failed: 1
Total rows validated: 150
Overall pass rate: 96.7%
Total execution time: 12.34s
```

### JSON Report Contents

The detailed JSON report includes:
- Each row that was tested
- Each validation that was run
- Pass/fail status for each check
- The actual SQL that was executed
- The actual vs expected values for failures

### Example Failure Output

```
Row 5: FAILED
  Validation: check_order_status
  Expected: status = "COMPLETED"
  Actual: status = "PENDING"
  SQL: SELECT * FROM orders WHERE order_id = 'ORD-0005'
```

---

## Common Examples

### Example 1: Simple Order Validation

**test_data.csv:**
```
OrderID|Customer|Amount
ORD-001|John|100.00
ORD-002|Jane|200.00
```

**config.yaml:**
```yaml
file:
  path: test_data.csv
  delimiter: '|'
  has_header: true

variables:
  order_id: ${row.OrderID}
  customer: ${row.Customer}
  amount: ${row.Amount}:decimal

validations:
  - name: order_exists
    sql: SELECT * FROM orders WHERE order_id = :order_id
    expect:
      row_count: 1
      columns:
        customer_name: ${customer}
        total_amount: ${amount}
```

### Example 2: Multi-Step Batch Process

**config.yaml:**
```yaml
file:
  path: test_data.csv
  delimiter: '|'
  has_header: true

primary_key:
  column: PolicyNumber
  auto_increment: true

batches:
  - name: Step 1 - Import
    script: batches/import
    copy_input_file_to: system/input
    args: ["--validate=true"]

  - name: Step 2 - Process
    script: batches/process
    args: ["--mode=full"]

  - name: Step 3 - Finalize
    script: batches/finalize

variables:
  policy: ${row.PolicyNumber}
  premium: ${row.Premium}:decimal

validations:
  - name: policy_imported
    sql: SELECT * FROM policies WHERE policy_number = :policy
    expect:
      row_count: 1

  - name: premium_calculated
    sql: SELECT * FROM premiums WHERE policy_number = :policy
    expect:
      row_count: 1
      columns:
        amount: ${premium}
        status: "CALCULATED"
```

### Example 3: No Headers (Column by Index)

**test_data.csv:**
```
John Smith|PROD-001|5|29.99|149.95|ORD-000001
Jane Doe|PROD-002|3|49.99|149.97|ORD-000002
```

**config.yaml:**
```yaml
file:
  path: test_data.csv
  delimiter: '|'
  has_header: false

primary_key:
  column_index: 5    # ORD-000001 is in column 5 (0-based)
  auto_increment: true

variables:
  customer: ${row.0}
  product: ${row.1}
  quantity: ${row.2}:int
  price: ${row.3}:decimal
  total: ${row.4}:decimal
  order_id: ${row.5}

validations:
  - name: order_created
    sql: |
      SELECT * FROM orders
      WHERE order_id = :order_id
    expect:
      row_count: 1
      columns:
        customer_name: ${customer}
        product_code: ${product}
        quantity: ${quantity}
        total_amount: ${total}
```

---

## Troubleshooting

### "File not found" Error

**Problem:** Tool can't find your CSV or config file.

**Solution:**
- Check the path in your config/manifest
- Use forward slashes `/` or double backslashes `\\`
- Make sure the file exists

### "Column not found" Error

**Problem:** Variable references a column that doesn't exist.

**Solution:**
- Check spelling of column names (case-sensitive!)
- If `has_header: false`, use numbers: `${row.0}`, `${row.1}`
- Open CSV in text editor to verify column names

### "Database connection failed" Error

**Problem:** Can't connect to the database.

**Solution:**
- Verify connection URL format
- Check username/password
- Ensure database server is accessible
- Check firewall settings

### Validation Always Fails

**Problem:** SQL returns data but validation fails.

**Solution:**
- Check expected values match actual database values
- Verify data types (string vs number vs date)
- Use `:decimal` for money values
- Check for extra whitespace in data

### Batch Script Doesn't Run

**Problem:** Batch script not executing.

**Solution:**
- Don't include file extension in config (tool adds `.bat` or `.sh`)
- Check script has execute permissions (Linux)
- Verify script path is correct
- Check batch log file for errors

### Primary Key Not Incrementing

**Problem:** Auto-increment not working.

**Solution:**
- Ensure `auto_increment: true` is set
- Check column name/index is correct
- Primary key must end with numbers (e.g., `ORD-0001`)
- File must be writable

### "No numeric suffix" Warning

**Problem:** Primary key doesn't have numbers to increment.

**Solution:**
- Primary key must end with digits: `ORD-001` (good), `ORDER-A` (bad)
- Tool will skip rows without numeric suffix

---

## Getting Help

If you encounter issues:

1. Check the log files in the `reports/` folder
2. Review the JSON report for detailed error messages
3. Verify your YAML syntax (use online YAML validator)
4. Contact your IT team with the error message and log files

---

## Quick Reference Card

### Command Line

```bash
run_suites.exe manifest.yaml                    # Run all tests
run_suites.exe manifest.yaml --suite "Name"     # Run specific test
run_suites.exe manifest.yaml --tags critical    # Run tagged tests
```

### Variable Types

```yaml
${row.Column}           # Text
${row.Column}:decimal   # Decimal number
${row.Column}:int       # Integer
${row.Column}:date      # Date
${row.0}                # Column by index (no header)
```

### Validation Expects

```yaml
expect:
  row_count: 1              # Exact count
  min_rows: 1               # Minimum
  max_rows: 10              # Maximum
  columns:
    name: "value"           # Exact match
    amount: ${var}          # Variable match
  not_null:
    - column_name           # Must not be null
```

### File Delimiters

| Delimiter | Config Value |
|-----------|--------------|
| Pipe      | `delimiter: '\|'` |
| Comma     | `delimiter: ','` |
| Tab       | `delimiter: '\t'` |
| Semicolon | `delimiter: ';'` |

---

*PASS Flow Testing Engine - Making batch testing simple for everyone.*
