#!/usr/bin/env python3
"""V58.0 Nuclear Clear - Aggressive lock clearance and schema migration.

This script performs a complete database cleanup:
1. Terminates ALL non-system connections to the database
2. Immediately adds missing columns
3. Verifies schema success
"""

import sys
import time
from pathlib import Path

import psycopg2

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config_unified import get_settings


def nuclear_clear_and_migrate():
    """Execute nuclear clearance and migration."""
    settings = get_settings()

    print("=" * 70)
    print("V58.0 NUCLEAR CLEAR - Aggressive Lock Clearance")
    print("=" * 70)

    # Connect with autocommit
    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
    )
    conn.autocommit = True
    cursor = conn.cursor()

    # Get current backend PID
    cursor.execute("SELECT pg_backend_pid()")
    my_pid = cursor.fetchone()[0]
    print(f"\n[INFO] My backend PID: {my_pid}")

    # STEP 1: NUCLEAR CLEAR - Kill ALL other connections
    print("\n[STEP 1] NUCLEAR CLEAR - Terminating ALL other connections...")
    cursor.execute("""
        SELECT pid
        FROM pg_stat_activity
        WHERE datname = %s
        AND pid <> %s
        AND pid <> pg_backend_pid()
    """, (settings.database.name, my_pid))

    pids_to_kill = [row[0] for row in cursor.fetchall()]
    print(f"Found {len(pids_to_kill)} connections to terminate")

    killed_count = 0
    for pid in pids_to_kill:
        try:
            cursor.execute(f"SELECT pg_terminate_backend({pid})")
            if cursor.fetchone()[0]:
                killed_count += 1
                print(f"  Terminated PID {pid}")
        except Exception as e:
            print(f"  Failed to terminate PID {pid}: {e}")

    print(f"Total terminated: {killed_count}/{len(pids_to_kill)}")

    # STEP 2: Wait for locks to clear
    print("\n[STEP 2] Waiting for locks to clear...")
    for i in range(10):
        cursor.execute("""
            SELECT COUNT(*) FROM pg_locks l
            JOIN pg_class c ON l.relation = c.oid
            WHERE c.relname = 'metrics_multi_source_data'
            AND l.granted = false
        """)
        blocking = cursor.fetchone()[0]
        if blocking == 0:
            print(f"  Locks cleared after {i+1} checks")
            break
        print(f"  Check {i+1}: {blocking} blocking locks remaining...")
        time.sleep(1)

    # STEP 3: FORCE MIGRATION
    print("\n[STEP 3] FORCE MIGRATION - Adding missing columns...")
    start_time = time.time()

    migrations = [
        ("is_valid", "BOOLEAN DEFAULT TRUE"),
        ("validation_error", "TEXT"),
        ("fully_captured", "BOOLEAN DEFAULT FALSE"),
        ("data_timestamp", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
    ]

    success_count = 0
    for col_name, col_def in migrations:
        try:
            cursor.execute(
                f"ALTER TABLE metrics_multi_source_data "
                f"ADD COLUMN IF NOT EXISTS {col_name} {col_def}"
            )
            elapsed = time.time() - start_time
            print(f"  ✅ {col_name} added ({elapsed:.2f}s)")
            success_count += 1
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"  ❌ {col_name} FAILED: {str(e)[:60]}")

    total_time = time.time() - start_time
    print(f"\nMigration completed in {total_time:.2f}s")

    # STEP 4: VERIFICATION
    print("\n[STEP 4] VERIFICATION - Checking schema...")
    cursor.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'metrics_multi_source_data'
        AND column_name IN ('is_valid', 'validation_error', 'fully_captured', 'data_timestamp')
        ORDER BY column_name
    """)

    results = cursor.fetchall()
    print(f"Columns found: {len(results)}/4")

    for row in results:
        print(f"  {row[0]}: {row[1]}")

    cursor.close()
    conn.close()

    # FINAL RESULT
    print("\n" + "=" * 70)
    if len(results) == 4:
        print("✅ V58.0 NUCLEAR CLEAR SUCCESSFUL")
        print("=" * 70)
        print("\nSchema is ready for production!")
        return 0
    else:
        print("❌ V58.0 NUCLEAR CLEAR INCOMPLETE")
        print("=" * 70)
        print(f"\nERROR: Only {len(results)}/4 columns added")
        print("Please check database logs and retry")
        return 1


if __name__ == "__main__":
    sys.exit(nuclear_clear_and_migrate())
