#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from src.config_unified import get_settings
import psycopg2

settings = get_settings()
conn = psycopg2.connect(
    host=settings.database.host,
    port=settings.database.port,
    database=settings.database.name,
    user=settings.database.user,
    password=settings.database.password.get_secret_value(),
)
conn.autocommit = True
cursor = conn.cursor()

# Check columns
cursor.execute("""
    SELECT column_name FROM information_schema.columns
    WHERE table_name = 'metrics_multi_source_data'
    AND column_name IN ('is_valid', 'validation_error', 'fully_captured', 'data_timestamp')
""")
existing = set(row[0] for row in cursor.fetchall())

needed = {'is_valid', 'validation_error', 'fully_captured', 'data_timestamp'}
missing = needed - existing

if missing:
    print(f"Missing columns: {missing}")
    print("Adding...")

    if 'is_valid' in missing:
        cursor.execute("ALTER TABLE metrics_multi_source_data ADD COLUMN is_valid BOOLEAN DEFAULT TRUE")
        print("  Added: is_valid")
    if 'validation_error' in missing:
        cursor.execute("ALTER TABLE metrics_multi_source_data ADD COLUMN validation_error TEXT")
        print("  Added: validation_error")
    if 'fully_captured' in missing:
        cursor.execute("ALTER TABLE metrics_multi_source_data ADD COLUMN fully_captured BOOLEAN DEFAULT FALSE")
        print("  Added: fully_captured")
    if 'data_timestamp' in missing:
        cursor.execute("ALTER TABLE metrics_multi_source_data ADD COLUMN data_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        print("  Added: data_timestamp")

# Final verification
cursor.execute("""
    SELECT column_name, data_type FROM information_schema.columns
    WHERE table_name = 'metrics_multi_source_data'
    AND column_name IN ('is_valid', 'validation_error', 'fully_captured', 'data_timestamp')
    ORDER BY column_name
""")
print("\n=== Final Schema ===")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]}")

cursor.close()
conn.close()
print("\nDone!")
