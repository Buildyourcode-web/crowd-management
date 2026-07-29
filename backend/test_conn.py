import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

host = os.getenv("DB_HOST", "db.vedrsfqvqvgnsrlrrblq.supabase.co")
port = os.getenv("DB_PORT", "5432")
database = os.getenv("DB_DATABASE", "postgres")
user = os.getenv("DB_USERNAME", "postgres")
password = os.getenv("DB_PASSWORD", "Byc@2026$%")

print(f"Testing connection to Supabase ({host})...")

for p in [5432, 6543]:
    try:
        print(f"Trying port {p}...")
        conn = psycopg2.connect(
            host=host,
            port=p,
            dbname=database,
            user=user,
            password=password,
            sslmode="require",
            connect_timeout=5
        )
        cursor = conn.cursor()
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public';")
        tables = cursor.fetchall()
        
        print(f"[SUCCESS] Connected on port {p}!")
        print("Existing Tables:")
        for t in tables:
            print(f"  - {t[0]}")
            
        cursor.close()
        conn.close()
        break
    except Exception as e:
        print(f"[ERROR] Port {p} failed: {e}")
