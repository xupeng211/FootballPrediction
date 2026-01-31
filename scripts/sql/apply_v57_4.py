#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from src.config_unified import get_settings
import psycopg2

settings = get_settings()

# Connect with explicit settings
conn = psycopg2.connect(
    host='localhost',
    port=5432,
    database='football_prediction_dev',
    user='football_user',
    password=settings.database.password.get_secret_value(),
)
conn.set_session(autocommit=True)
cursor = conn.cursor()

# Add columns
sqls = [
    "ALTER TABLE metrics_multi_source_data ADD COLUMN IF NOT EXISTS is_valid BOOLEAN DEFAULT TRUE",
    "ALTER TABLE metrics_multi_source_data ADD COLUMN IF NOT EXISTS validation_error TEXT",
    "ALTER TABLE metrics_multi_source_data ADD COLUMN IF NOT EXISTS fully_captured BOOLEAN DEFAULT FALSE",
    "ALTER TABLE metrics_multi_source_data ADD COLUMN IF NOT EXISTS data_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
]

print("V57.4 Migration:")
for sql in sqls:
    col = sql.split()[5]
    try:
        cursor.execute(sql)
        print(f"  {col}: OK")
    except Exception as e:
        print(f"  {col}: {e}")

# Verify
cursor.execute("""
    SELECT column_name FROM information_schema.columns
    WHERE table_name = 'metrics_multi_source_data'
    AND column_name IN ('is_valid', 'validation_error', 'fully_captured', 'data_timestamp')
""")
results = cursor.fetchall()
print(f"\nVerification: {len(results)}/4 columns added")

cursor.close()
conn.close()
