#!/usr/bin/env python3
"""
Data Inspection Script - Phase 2 Feature Engineering
==============================================

Connect to the database and inspect the raw data structure
to understand the available features for engineering.

Target: Find one complete match with full L2 details and print
        the JSON structure of stats_json and environment_json.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.database.async_manager import get_db_session, initialize_database
from sqlalchemy import text


async def inspect_data_sample():
    """Connect to DB and inspect one complete match sample."""

    print("🔍 Phase 2: Data Structure Inspection")
    print("=" * 50)

    try:
        print("📊 Connecting to database...")
        initialize_database()

        # Query for one complete match with L2 details
        query = """
        SELECT
            m.id,
            m.fotmob_id,
            m.home_team_id,
            ht.name as home_team_name,
            m.away_team_id,
            at.name as away_team_name,
            m.match_date,
            m.home_score,
            m.away_score,
            m.status,
            m.home_xg,
            m.away_xg,
            m.data_completeness,
            m.stats_json,
            m.environment_json
        FROM matches m
        JOIN teams ht ON m.home_team_id = ht.id
        JOIN teams at ON m.away_team_id = at.id
        WHERE m.status = 'FT'
        AND m.home_xg IS NOT NULL
        AND m.away_xg IS NOT NULL
        AND m.stats_json IS NOT NULL
        AND m.environment_json IS NOT NULL
        ORDER BY m.match_date DESC
        LIMIT 1
        """

        print("🎯 Fetching one complete match sample...")

        async with get_db_session() as session:
            result = await session.execute(text(query))
            match = result.fetchone()

        if not match:
            print("❌ No complete matches found with full L2 data!")
            return

        # Convert to dictionary for easier access
        match = dict(match._mapping)

        print(f"\n🏆 MATCH SAMPLE FOUND:")
        print(f"🆔 ID: {match['id']}")
        print(f"⚽ FotMob ID: {match['fotmob_id']}")
        print(f"🏠 Home Team: {match['home_team_name']} (ID: {match['home_team_id']})")
        print(f"✈️ Away Team: {match['away_team_name']} (ID: {match['away_team_id']})")
        print(f"📅 Match Date: {match['match_date']}")
        print(f"📊 Score: {match['home_score']} - {match['away_score']}")
        print(f"⚡ Status: {match['status']}")
        print(f"🎯 xG: Home {match['home_xg']} - Away {match['away_xg']}")
        print(f"📋 Data Completeness: {match['data_completeness']}")

        print(f"\n" + "="*60)
        print("📊 STATISTICS JSON (stats_json) - 'Gold Mine' Part 1:")
        print("="*60)

        if match['stats_json']:
            # stats_json might already be a dict or a JSON string
            if isinstance(match['stats_json'], dict):
                stats_data = match['stats_json']
            else:
                stats_data = json.loads(match['stats_json'])

            # Print top-level structure
            print(f"🔑 Top-level keys: {list(stats_data.keys())}")
            print()

            # Detailed breakdown of each section
            for key, value in stats_data.items():
                print(f"📈 {key.upper()}:")
                if isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        if isinstance(sub_value, (int, float, str)):
                            print(f"   • {sub_key}: {sub_value}")
                        elif isinstance(sub_value, dict):
                            print(f"   • {sub_key}: (dict with {len(sub_value)} keys)")
                            if len(sub_value) <= 5:  # Show small dicts
                                for sk, sv in sub_value.items():
                                    print(f"     - {sk}: {sv}")
                        elif isinstance(sub_value, list):
                            print(f"   • {sub_key}: (list with {len(sub_value)} items)")
                            if len(sub_value) <= 3:  # Show small lists
                                for i, item in enumerate(sub_value[:3]):
                                    print(f"     [{i}]: {item}")
                        else:
                            print(f"   • {sub_key}: {type(sub_value).__name__}")
                else:
                    print(f"   Value: {value} ({type(value).__name__})")
                print()
        else:
            print("❌ No stats_json data found!")

        print(f"\n" + "="*60)
        print("🌍 ENVIRONMENT JSON (environment_json) - 'Gold Mine' Part 2:")
        print("="*60)

        if match['environment_json']:
            # environment_json might already be a dict or a JSON string
            if isinstance(match['environment_json'], dict):
                env_data = match['environment_json']
            else:
                env_data = json.loads(match['environment_json'])

            # Print top-level structure
            print(f"🔑 Top-level keys: {list(env_data.keys())}")
            print()

            # Detailed breakdown of each section
            for key, value in env_data.items():
                print(f"🌐 {key.upper()}:")
                if isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        if isinstance(sub_value, (int, float, str)):
                            print(f"   • {sub_key}: {sub_value}")
                        elif isinstance(sub_value, dict):
                            print(f"   • {sub_key}: (dict with {len(sub_value)} keys)")
                            if len(sub_value) <= 5:  # Show small dicts
                                for sk, sv in sub_value.items():
                                    print(f"     - {sk}: {sv}")
                        elif isinstance(sub_value, list):
                            print(f"   • {sub_key}: (list with {len(sub_value)} items)")
                            if len(sub_value) <= 3:  # Show small lists
                                for i, item in enumerate(sub_value[:3]):
                                    print(f"     [{i}]: {item}")
                        else:
                            print(f"   • {sub_key}: {type(sub_value).__name__}")
                else:
                    print(f"   Value: {value} ({type(value).__name__})")
                print()
        else:
            print("❌ No environment_json data found!")

        # Feature Engineering suggestions
        print(f"\n" + "="*60)
        print("🧠 FEATURE ENGINEERING INSIGHTS:")
        print("="*60)

        print("🎯 Available Data Categories:")

        if match['stats_json']:
            stats = match['stats_json'] if isinstance(match['stats_json'], dict) else json.loads(match['stats_json'])
            print(f"📊 Statistics: {len(stats)} categories")
            for category in stats.keys():
                print(f"   • {category}")

        if match['environment_json']:
            env = match['environment_json'] if isinstance(match['environment_json'], dict) else json.loads(match['environment_json'])
            print(f"🌍 Environment: {len(env)} categories")
            for category in env.keys():
                print(f"   • {category}")

        print(f"\n💡 Key Features for Engineering:")
        print("   🎯 Core Performance: xG, shots, possession")
        print("   📈 Advanced Metrics: xGOT, big chances, pressures")
        print("   🌍 Context: odds, weather, referee, stadium")
        print("   ⏰ Time: match date, season, form period")

    except Exception as e:
        print(f"❌ Error during inspection: {e}")
        import traceback
        traceback.print_exc()

    print("\n✅ Database connection closed automatically.")


def main():
    """Main execution function."""
    print("🚀 Starting Data Structure Inspection...")

    try:
        asyncio.run(inspect_data_sample())
        print("\n🎉 Data inspection completed successfully!")

    except KeyboardInterrupt:
        print("\n⚠️ Inspection interrupted by user.")

    except Exception as e:
        print(f"\n❌ Inspection failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()