import yaml
from pathlib import Path
import psycopg2


def run_sql(conn, sql_path):
    sql = Path(sql_path).read_text(encoding="utf-8")
    with conn.cursor() as cursor:
        cursor.execute(sql)


def main():
    base_dir = Path(__file__).parent
    schema_path = base_dir / "schema.sql"
    seed_path = base_dir / "seed.sql"
    manifest_path = base_dir.parent.parent / "test-manifest-postgres-flow.yaml"

    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    db_url = manifest["database"]["connection_url"]

    conn = psycopg2.connect(db_url)
    try:
        run_sql(conn, schema_path)
        run_sql(conn, seed_path)
        conn.commit()
    finally:
        conn.close()

    print("Initialized Postgres schema and seed data")


if __name__ == "__main__":
    main()
