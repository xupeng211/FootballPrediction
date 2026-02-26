#!/bin/bash
###############################################################################
# V43.200 Production Entry Script
# =================================
#
# Production-ready entry point for temporal data synchronization
#
# Usage:
#   ./run_sync.sh <TARGET_URL> <SOURCE_ID>
#
# Environment Variables (optional):
#   DB_HOST         - Database host (default: 172.25.16.1)
#   DB_PORT         - Database port (default: 5432)
#   DB_NAME         - Database name (default: football_db)
#   DB_USER         - Database user (default: football_user)
#   DB_PASSWORD     - Database password (default: football_pass)
#   DEBUG           - Enable debug logging (default: false)
#
# Author: Senior DevOps & Systems Engineer
# Version: V43.200
# Date: 2026-01-24
###############################################################################

set -e  # Exit on error

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Default values
TARGET_URL="${1:-}"
SOURCE_ID="${2:-}"

# Validate arguments
if [ -z "$TARGET_URL" ] || [ -z "$SOURCE_ID" ]; then
    echo "[ERROR] Missing required arguments"
    echo ""
    echo "Usage: $0 <TARGET_URL> <SOURCE_ID>"
    echo ""
    echo "Example:"
    echo "  $0 \"https://www.oddsportal.com/football/spain/laliga/match-id/\" \"4507132\""
    echo ""
    exit 1
fi

# Log startup
echo "[INFO] [$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)] [run_sync] Temporal Sync Engine starting..."
echo "[INFO] [$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)] [run_sync] Target: $SOURCE_ID"
echo "[INFO] [$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)] [run_sync]"

# Run the sync engine
node temporal_sync_engine.js "$TARGET_URL" "$SOURCE_ID"

# Check exit code
if [ $? -eq 0 ]; then
    echo "[INFO] [$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)] [run_sync] Temporal Sync Engine completed successfully"
    exit 0
else
    echo "[ERROR] [$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)] [run_sync] Temporal Sync Engine failed with exit code $?"
    exit 1
fi
