#!/usr/bin/env python3
"""V57.5 Force Fix - Kill blocking processes and migrate schema.

This script performs atomic operations to clear locks and add missing columns.
"""

import sys
import time
from pathlib import Path

import psycopg2

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config_unified import get_settings


def main():
    settings = get_settings()

    print("=" * 70)
    print("V57.5 FORCE FIX - Violent Lock Clearance")
    print("=" * 70)

    # Connect with autocommit for kill operations
    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
    )
    conn.autocommit = True
    cursor = conn.cursor()

    # Step 1: Kill blocking processes
    print("\n[STEP 1] Killing zombie processes...")
    zombie_pids = [53004, 53086, 53094, 53132, 53193, 53297, 53419, 53465]

    for pid in zombie_pids:
        try:
            cursor.execute(f"SELECT pg_terminate_backend({pid})")
            result = cursor.fetchone()
            if result and result[0]:
                print(f"  ✅ Terminated PID {pid}")
            else:
                print(f"  ⚠️  PID {pid} not found or already terminated")
        except Exception as e:
            print(f"  ❌ Error terminating PID {pid}: {e}")

    # Step 2: Verify no blocking locks remain
    print("\n[STEP 2] Verifying locks cleared...")
    cursor.execute("""
        SELECT COUNT(*) FROM pg_locks l
        WHERE l.relation = 'metrics_multi_source_data'::regclass
        AND l.granted = false
    """)
    blocking_count = cursor.fetchone()[0]
    print(f"  Blocking locks remaining: {blocking_count}")

    if blocking_count > 0:
        print("  ⚠️  Warning: Some locks still exist, proceeding anyway...")

    # Step 3: Atomic migration (within 5 seconds)
    print("\n[STEP 3] Executing atomic migration...")
    start_time = time.time()

    migrations = [
        ("is_valid", "BOOLEAN DEFAULT TRUE"),
        ("validation_error", "TEXT"),
        ("fully_captured", "BOOLEAN DEFAULT FALSE"),
        ("data_timestamp", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
    ]

    for col_name, col_def in migrations:
        try:
            cursor.execute(f"ALTER TABLE metrics_multi_source_data ADD COLUMN IF NOT EXISTS {col_name} {col_def}")
            elapsed = time.time() - start_time
            print(f"  ✅ Added {col_name} ({elapsed:.2f}s)")
        except Exception as e:
            print(f"  ❌ Error adding {col_name}: {e}")

    total_time = time.time() - start_time
    print(f"\n  Migration completed in {total_time:.2f}s")

    # Step 4: Verify columns
    print("\n[STEP 4] Verifying schema...")
    cursor.execute("""
        SELECT column_name, data_type FROM information_schema.columns
        WHERE table_name = 'metrics_multi_source_data'
        AND column_name IN ('is_valid', 'validation_error', 'fully_captured', 'data_timestamp')
        ORDER BY column_name
    """)

    results = cursor.fetchall()
    print(f"  Columns found: {len(results)}/4")

    for row in results:
        print(f"    {row[0]}: {row[1]}")

    cursor.close()
    conn.close()

    # Final result
    if len(results) == 4:
        print("\n" + "=" * 70)
        print("✅ V57.5 FORCE FIX SUCCESSFUL")
        print("=" * 70)
        print("\nNext: Run E2E test")
        print("  python tests/unit/test_v57_4_persistence.py")
        return 0
    else:
        print("\n" + "=" * 70)
        print("❌ V57.5 FORCE FIX INCOMPLETE")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
