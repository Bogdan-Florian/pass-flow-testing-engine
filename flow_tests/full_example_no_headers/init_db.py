"""
Initialize the SQLite database for the Full Example flow test.

Usage:
    python init_db.py

This script:
1. Creates the database file (full_example.db)
2. Runs schema.sql to create tables
3. Runs seed.sql to populate test data
"""

import sqlite3
from pathlib import Path


def init_database():
    """Initialize the database with schema and seed data."""
    base_dir = Path(__file__).parent
    db_path = base_dir / "full_example.db"
    schema_path = base_dir / "schema.sql"
    seed_path = base_dir / "seed.sql"

    # Remove existing database
    if db_path.exists():
        db_path.unlink()
        print(f"Removed existing database: {db_path}")

    # Create new database and run scripts
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Run schema
    print(f"Running schema from: {schema_path}")
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_sql = f.read()
    cursor.executescript(schema_sql)
    print("Schema created successfully.")

    # Run seed data
    print(f"Running seed data from: {seed_path}")
    with open(seed_path, 'r', encoding='utf-8') as f:
        seed_sql = f.read()
    cursor.executescript(seed_sql)
    print("Seed data inserted successfully.")

    conn.commit()
    conn.close()

    print(f"\nDatabase initialized: {db_path}")
    print("Tables created: orders, payments")
    print("Sample records: 5 orders, 5 payments")


if __name__ == "__main__":
    init_database()
