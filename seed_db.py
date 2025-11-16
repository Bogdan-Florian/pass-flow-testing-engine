import csv
from pathlib import Path
from datetime import date
from dateutil.relativedelta import relativedelta
from sqlalchemy import create_engine, text

# --- Configuration ---
DB_URL = "XXX"
CSV_PATH = Path("flow_tests/bksp32-nb/test.csv")
SCHEMA_PATH = Path("schema.sql")


def execute_schema(conn, schema_sql):
    """
    SQLAlchemy's exec_driver_sql() can execute multi-statement SQL,
    including CREATE TABLE, DROP TABLE, and PL/pgSQL blocks.
    """
    # Some editors add BOM characters. Remove them.
    schema_sql = schema_sql.lstrip("\ufeff")

    # PostgreSQL supports multi-statement execution directly
    conn.exec_driver_sql(schema_sql)


def seed_database():
    """
    Wipes and seeds the entire database.

    Steps:
    1. Executes schema.sql (PostgreSQL-safe execution)
    2. Inserts static party records
    3. Loads CSV and inserts policies, operations, premium schedules
    """
    print(f"Connecting to database: {DB_URL}")
    engine = create_engine(DB_URL)

    with engine.connect() as conn:
        with conn.begin():

            # --- 1. Load schema ---
            print(f"1. Setting up schema from {SCHEMA_PATH}...")
            schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
            execute_schema(conn, schema_sql)

            # --- 2. Static Seed Data ---
            print("2. Seeding static parties...")

            parties = [
                {'id': 'PTY_001', 'first': 'John',  'last': 'Doe',      'dob': '1985-05-20', 'ssn': '111-00-1111'},
                {'id': 'PTY_002', 'first': 'Jane',  'last': 'Smith',    'dob': '1992-11-30', 'ssn': '222-00-2222'},
                {'id': 'PTY_003', 'first': 'Peter', 'last': 'Jones',    'dob': '1978-01-15', 'ssn': '333-00-3333'},
                {'id': 'PTY_004', 'first': 'Mary',  'last': 'Williams', 'dob': '2000-07-22', 'ssn': '444-00-4444'},
                {'id': 'PTY_005', 'first': 'David', 'last': 'Brown',    'dob': '1995-03-12', 'ssn': '333-00-3333'},  # Duplicate SSN
                {'id': 'PTY_006', 'first': 'Susan', 'last': 'Miller',   'dob': '1988-09-05', 'ssn': '555-00-5555'},
            ]

            for p in parties:
                conn.execute(text("""
                    INSERT INTO parties (party_id, first_name, last_name, date_of_birth, ssn)
                    VALUES (:id, :first, :last, :dob, :ssn)
                    ON CONFLICT (party_id) DO NOTHING;
                """), p)

            # --- 3. CSV Seeding ---
            print(f"3. Seeding dynamic data from {CSV_PATH}...")

            with open(CSV_PATH, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter='|')

                for row in reader:
                    policy_number = row['PolicyNumber']
                    print(f"  - Processing Policy: {policy_number}")

                    policy_start = date.fromisoformat(row['PolicyStartDate'])

                    # Special invalid data logic
                    if policy_number == "POL_004":
                        # WRONG on purpose
                        policy_end = policy_start - relativedelta(days=10)
                        print(f"    -> INTENTIONALLY creating invalid end date: {policy_end}")
                    else:
                        policy_end = policy_start + relativedelta(years=1) - relativedelta(days=1)

                    # Insert policies
                    conn.execute(text("""
                        INSERT INTO policies (
                            policy_number, party_id, product_code, status,
                            start_date, end_date, total_premium, num_premiums
                        )
                        VALUES (
                            :policy_number, :party_id, :product_code, :status,
                            :start_date, :end_date, :total_premium, :num_premiums
                        )
                    """), {
                        "policy_number": policy_number,
                        "party_id": row['PartyID'],
                        "product_code": row['ProductCode'],
                        "status": row['Status'],
                        "start_date": policy_start,
                        "end_date": policy_end,
                        "total_premium": float(row['TotalPremium']),
                        "num_premiums": int(row['NumberOfPremiums'])
                    })

                    # Insert operations
                    conn.execute(text("""
                        INSERT INTO operations (policy_number, operation_type, operation_date, description)
                        VALUES (:policy_number, 'POLICY_ISSUED', :op_date, 'New policy created.')
                    """), {
                        "policy_number": policy_number,
                        "op_date": policy_start
                    })

                    # Insert premium schedules
                    num_premiums = int(row['NumberOfPremiums'])
                    premiums_to_gen = num_premiums

                    if policy_number == "POL_006":
                        premiums_to_gen = num_premiums - 1
                        print(f"    -> INTENTIONALLY generating {premiums_to_gen} premiums instead of {num_premiums}")

                    if premiums_to_gen <= 0:
                        continue

                    total_premium = float(row['TotalPremium'])
                    monthly = round(total_premium / num_premiums, 2)

                    sum_so_far = 0.0

                    # All but last
                    for i in range(premiums_to_gen - 1):
                        due = policy_start + relativedelta(months=i)
                        conn.execute(text("""
                            INSERT INTO policy_premiums
                                (policy_number, premium_amount, due_date, status)
                            VALUES (:p, :a, :d, 'DUE')
                        """), {
                            "p": policy_number,
                            "a": monthly,
                            "d": due,
                        })
                        sum_so_far += monthly

                    # Last installment
                    last_amount = round(total_premium - sum_so_far, 2)
                    last_due = policy_start + relativedelta(months=premiums_to_gen - 1)

                    conn.execute(text("""
                        INSERT INTO policy_premiums
                            (policy_number, premium_amount, due_date, status)
                        VALUES (:p, :a, :d, 'DUE')
                    """), {
                        "p": policy_number,
                        "a": last_amount,
                        "d": last_due,
                    })

    print("\nDatabase seeding completed successfully!")


if __name__ == "__main__":
    seed_database()
