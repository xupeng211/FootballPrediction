#!/usr/bin/env python3
"""V57.4 Schema Migration Script - Production Audit Fields.

Adds missing production-grade audit fields to metrics_multi_source_data table.
"""

import sys
from pathlib import Path

import psycopg2

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config_unified import get_settings


def migrate():
    """Execute V57.4 schema migration."""
    settings = get_settings()

    print(f"Connecting to database: {settings.database.name}")
    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
    )
    conn.autocommit = True
    cursor = conn.cursor()

    # Define columns to add
    columns = [
        ('is_valid', 'BOOLEAN DEFAULT TRUE'),
        ('validation_error', 'TEXT'),
        ('fully_captured', 'BOOLEAN DEFAULT FALSE'),
        ('data_timestamp', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
    ]

    print("\n=== V57.4 Schema Migration ===\n")

    for col_name, col_def in columns:
        # Check if column exists
        cursor.execute(f"""
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'metrics_multi_source_data'
            AND column_name = '{col_name}'
        """)

        exists = cursor.fetchone() is not None

        if exists:
            print(f"✅ {col_name}: already exists")
        else:
            try:
                sql = f"ALTER TABLE metrics_multi_source_data ADD COLUMN {col_name} {col_def}"
                cursor.execute(sql)
                print(f"✅ {col_name}: added")
            except Exception as e:
                print(f"❌ {col_name}: error - {e}")

    # Verification
    print("\n=== Verification ===")
    cursor.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'metrics_multi_source_data'
        AND column_name IN ('is_valid', 'validation_error', 'fully_captured', 'data_timestamp')
        ORDER BY column_name
    """)

    results = cursor.fetchall()
    for row in results:
        print(f"  {row[0]}: {row[1]}")

    cursor.close()
    conn.close()

    if len(results) == 4:
        print("\n✅ V57.4 Migration Complete!")
        return 0
    else:
        print(f"\n❌ Migration incomplete: {len(results)}/4 columns added")
        return 1


if __name__ == "__main__":
    sys.exit(migrate())
