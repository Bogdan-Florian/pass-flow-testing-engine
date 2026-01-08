from pathlib import Path
import sqlite3

def run_sql(conn, sql_path):
    sql = Path(sql_path).read_text(encoding="utf-8")
    conn.executescript(sql)


def main():
    base_dir = Path(__file__).parent
    db_path = base_dir / "system_flow_multi.db"
    schema_path = base_dir / "schema.sql"
    seed_path = base_dir / "seed.sql"

    conn = sqlite3.connect(db_path)
    try:
        run_sql(conn, schema_path)
        run_sql(conn, seed_path)
        conn.commit()
    finally:
        conn.close()

    print(f"Initialized {db_path}")


if __name__ == "__main__":
    main()
