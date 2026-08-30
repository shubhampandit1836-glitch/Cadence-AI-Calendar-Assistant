import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def run_migrations():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL environment variable is missing.")

    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()

    sql_dir = os.path.join(os.path.dirname(__file__), "..", "sql")
    sql_files = sorted([f for f in os.listdir(sql_dir) if f.endswith(".sql")])

    for file in sql_files:
        path = os.path.join(sql_dir, file)
        with open(path, "r", encoding="utf-8") as f:
            sql = f.read()
        print(f"Running migration: {file}")
        cursor.execute(sql)

    conn.commit()
    cursor.close()
    conn.close()
    print("All migrations executed successfully.")

if __name__ == "__main__":
    run_migrations()