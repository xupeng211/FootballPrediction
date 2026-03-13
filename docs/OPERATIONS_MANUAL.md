# Football Prediction System - Operations Manual

**Version**: V70.300
**Date**: 2026-01-25
**Audience**: Tier-1 Operations Engineers, Site Reliability Engineers

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [System Architecture Overview](#system-architecture-overview)
3. [Status Interpretation](#status-interpretation)
4. [Troubleshooting Guide](#troubleshooting-guide)
5. [Daily Maintenance Procedures](#daily-maintenance-procedures)
6. [Emergency Recovery Procedures](#emergency-recovery-procedures)
7. [Monitoring and Alerting](#monitoring-and-alerting)
8. [Appendices](#appendices)

---

## Quick Start

### 3-Line Quick Start (全自动收割)

```bash
# 1. Start the system
./scripts/ops/control.sh start

# 2. Check status (optional)
./scripts/ops/control.sh status

# 3. View logs (optional)
./scripts/ops/control.sh logs
```

### System Requirements

| Component | Requirement |
|-----------|-------------|
| **Node.js** | v18+ |
| **PostgreSQL** | v15+ |
| **Docker** | v24+ (optional, for containerized DB) |
| **Memory** | 4GB minimum, 8GB recommended |
| **Disk** | 20GB minimum, 50GB+ for production |

### Environment Setup

```bash
# Clone repository
git clone <repository-url>
cd FootballPrediction

# Install dependencies
npm install

# Start database
make up

# Verify environment
./scripts/ops/control.sh health
```

---

## System Architecture Overview

### Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     V69.000 Pipeline Orchestrator                      │
│                     "The Master Switch"                                │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Step A: L2 Enrichment Trigger    │  Step B: Bridge Trigger           │
│  • FotMob Core Collector           │  • Fuzzy Team Matching           │
│  • xG, Lineups, Ratings           │  • oddsportal_hash Discovery     │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Step C: Odds Harvest Trigger                                          │
│  • V66.000 Temporal Data Collection                                   │
│  • 5 Providers × 3 Dimensions (Home/Draw/Away)                         │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  V70.200 Data Sentinel (Quality Gate)                                  │
│  • Completeness Scan • Quality Check • Throughput Tracker             │
└─────────────────────────────────────────────────────────────────────────┘
```

### Core Components

| Component | File | Version | Description |
|-----------|------|---------|-------------|
| **Orchestrator** | `src/ops/v69_000_pipeline_orchestrator.js` | V69.000 | Main pipeline controller |
| **L2 Trigger** | `scripts/ops/v69_010_l2_trigger.py` | V69.010 | Python L2 data enrichment |
| **Bridge Trigger** | `scripts/ops/v69_020_bridge_trigger.js` | V69.020 | URL mapping via fuzzy matching |
| **Data Sentinel** | `src/ops/v70_200_data_sentinel.js` | V70.200 | Quality monitoring |
| **Control Center** | `scripts/ops/control.sh` | V70.300 | CLI control interface |

---

## Status Interpretation

### Pipeline States (match_pipeline_state)

| State | Business Meaning | Transition Condition |
|-------|------------------|---------------------|
| **DISCOVERED** | Match indexed in match_search_queue | Initial state |
| **ENRICHED** | L2 data (xG, lineups, ratings) collected | Step A completed |
| **MAPPED** | oddsportal_hash discovered via fuzzy matching | Step B completed |
| **HARVESTED** | Temporal odds data collected (5 providers × 3 dimensions) | Step C completed |
| **FAILED** | Processing failed at some stage | Manual repair needed |

### State Transition Diagram

```
DISCOVERED ──(Step A: L2 Enrichment)──> ENRICHED ──(Step B: Bridge)──> MAPPED ──(Step C: Harvest)──> HARVESTED
     │                                     │                                │
     └────────────────(repair)──────────────┴────────────────────────(repair)────> FAILED
```

### Health Score Interpretation (V70.200)

| Score Range | Rating | Action Required |
|-------------|--------|-----------------|
| **9.0 - 10.0** | Excellent | No action required |
| **7.0 - 8.9** | Good | Monitor closely |
| **5.0 - 6.9** | Fair | Review quality gate results |
| **0.0 - 4.9** | Poor | Immediate investigation required |

---

## Troubleshooting Guide

### Issue 1: Low Similarity Score in Bridge Mapping

**Symptoms**:

- Bridge Trigger reports "No match found"
- Similarity score < 85.0%
- Status stuck at `ENRICHED`

**Diagnosis**:

```bash
# Check bridge trigger logs
./scripts/ops/control.sh logs | grep -i "bridge"

# Run manual similarity test
node -e "
const { parseUrlTeams } = require('./src/modules/url_parser.js');
const url = 'https://www.oddsportal.com/football/england/premier-league-2024-2025-arsenal-chelsea-7f8a9b2/';
console.log(parseUrlTeams(url));
"
```

**Solutions**:

1. **Update Known Teams List** (if team name changed):

   ```bash
   # Edit src/modules/url_parser.js
   # Add new team to multiWordTeams array
   ```

2. **Adjust Fuzzy Threshold** (temporary):

   ```bash
   # Edit scripts/ops/v69_020_bridge_trigger.js
   # Change fuzzyThreshold: 85.0 to 80.0
   ./scripts/ops/control.sh restart
   ```

3. **Manual Mapping** (for edge cases):

   ```sql
   INSERT INTO matches_mapping (fotmob_id, oddsportal_url, confidence, mapping_method, review_status)
   VALUES ('<fotmob_id>', '<oddsportal_url>', 1.0, 'manual', 'approved');
   ```

### Issue 2: Payout Anomaly Alert

**Symptoms**:

- Data Sentinel reports "Payout Anomalies"
- Payout < 80% or > 100%
- Health score drops below 7.0

**Diagnosis**:

```bash
# Check payout anomalies
psql -h 172.25.16.1 -U football_user -d football_db -c "
SELECT entity_id, provider_name, payout, occurred_at
FROM temporal_metric_records
WHERE payout < 0.80 OR payout > 1.00
ORDER BY occurred_at DESC
LIMIT 20;
"
```

**Solutions**:

1. **Identify Faulty Provider**:

   ```sql
   SELECT provider_name, COUNT(*), AVG(payout)
   FROM temporal_metric_records
   WHERE payout < 0.80 OR payout > 1.00
   GROUP BY provider_name;
   ```

2. **Disable Faulty Provider**:

   ```bash
   # Edit src/config/providers.json
   # Set "enabled": false for the problematic provider
   ```

3. **Delete Corrupted Records**:

   ```sql
   DELETE FROM temporal_metric_records
   WHERE payout < 0.70 OR payout > 1.10;
   ```

### Issue 3: Proxy Connection Failures

**Symptoms**:

- Frequent HTTP 429/403 errors
- "Connection timeout" messages
- Harvest rate drops to 0 MPH

**Diagnosis**:

```bash
# Check proxy status
curl -I https://www.fotmob.com/api

# Test proxy connectivity
export HTTP_PROXY=http://your-proxy:port
curl -I https://www.oddsportal.com
```

**Solutions**:

1. **Update Proxy Configuration**:

   ```bash
   # Edit .env file
   HTTP_PROXY=http://new-proxy:port
   HTTPS_PROXY=http://new-proxy:port
   ```

2. **Rotate User Agents** (Ghost Protocol):

   ```bash
   # V141.0 automatically rotates fingerprints
   # Check src/api/collectors/base_extractor.js
   ```

3. **Add Cooldown Delay**:

   ```bash
   # Edit src/ops/v69_000_pipeline_orchestrator.js
   # Increase cooldownSeconds in l2Enrichment config
   ```

### Issue 4: Database Connection Pool Exhaustion

**Symptoms**:

- "Connection pool exhausted" errors
- Slow query performance
- Services becoming unresponsive

**Diagnosis**:

```bash
# Check active connections
docker exec football_db psql -U football_user -c "
SELECT count(*), state
FROM pg_stat_activity
GROUP BY state;
"
```

**Solutions**:

1. **Increase Pool Size**:

   ```bash
   # Edit .env
   DB_POOL_SIZE=20
   DB_POOL_MAX_OVERFLOW=30
   ```

2. **Kill Long-Running Queries**:

   ```sql
   SELECT pg_terminate_backend(pid)
   FROM pg_stat_activity
   WHERE state = 'active'
   AND query_start < now() - interval '5 minutes';
   ```

3. **Restart Services**:

   ```bash
   ./scripts/ops/control.sh restart
   ```

---

## Daily Maintenance Procedures

### Morning Checklist (Daily 9:00 AM)

```bash
# 1. Check system status
./scripts/ops/control.sh status

# 2. Verify health score ≥ 7.0
./scripts/ops/control.sh health

# 3. Check for failed records
psql -h 172.25.16.1 -U football_user -d football_db -c "
SELECT status, COUNT(*)
FROM match_pipeline_state
GROUP BY status;
"

# 4. Repair failed records (if any)
./scripts/ops/control.sh repair
```

### Weekly Maintenance (Sundays 2:00 AM)

```bash
# 1. Create database backup
./scripts/ops/control.sh backup

# 2. Clean old logs and temp files
./scripts/ops/control.sh clean

# 3. Review throughput trends
node -e "
const { DataSentinel } = require('./src/ops/v70_200_data_sentinel.js');
const sentinel = new DataSentinel();
sentinel.executeScan().then(r => console.log('MPH:', r.throughput.mph));
"

# 4. Check disk space
df -h

# 5. Restart orchestrator (if needed)
./scripts/ops/control.sh restart
```

### Log Cleanup Rules

| Log Type | Retention | Cleanup Command |
|----------|-----------|------------------|
| **Orchestrator Logs** | 7 days | `find logs/ -name "*.log" -mtime +7 -delete` |
| **Database Backups** | Last 5 | Manual cleanup via `control.sh clean` |
| **Temp Files** | 1 day | `find /tmp -name "football_*" -mtime +1 -delete` |

---

## Emergency Recovery Procedures

### Emergency Reset Tool (SQL Templates)

#### Recovery 1: Mass Reset to DISCOVERED

```sql
-- Emergency: Reset all FAILED records to DISCOVERED
BEGIN;

UPDATE match_pipeline_state
SET status = 'DISCOVERED', updated_at = NOW()
WHERE status = 'FAILED';

COMMIT;

-- Verify
SELECT status, COUNT(*) FROM match_pipeline_state GROUP BY status;
```

#### Recovery 2: Selective Re-harvest for League

```sql
-- Emergency: Re-harvest specific league (e.g., Premier League)
BEGIN;

-- Reset to ENRICHED (skip L2, redo bridge + harvest)
UPDATE match_pipeline_state mps
SET status = 'ENRICHED', updated_at = NOW()
FROM matches m
WHERE mps.match_id = m.match_id
  AND m.league_name = 'Premier League'
  AND mps.status IN ('MAPPED', 'HARVESTED', 'FAILED');

COMMIT;
```

#### Recovery 3: Clean Stale Temporal Records

```sql
-- Emergency: Remove records with bad payout (> 110% or < 70%)
BEGIN;

DELETE FROM temporal_metric_records
WHERE payout > 1.10 OR payout < 0.70;

-- Reset affected matches to MAPPED
UPDATE match_pipeline_state
SET status = 'MAPPED', updated_at = NOW()
WHERE match_id IN (
    SELECT DISTINCT entity_id::varchar
    FROM temporal_metric_records
    WHERE payout > 1.10 OR payout < 0.70
);

COMMIT;
```

#### Recovery 4: Full System Reset (⚠️ DANGEROUS)

```sql
-- Emergency: Reset entire pipeline (USE WITH CAUTION)
BEGIN;

-- Reset all to DISCOVERED
UPDATE match_pipeline_state
SET status = 'DISCOVERED', updated_at = NOW();

COMMIT;

-- Confirm reset
SELECT status, COUNT(*) FROM match_pipeline_state GROUP BY status;
```

### Recovery Escalation Matrix

| Scenario | Recovery Time | Escalation |
|----------|---------------|-------------|
| **Single Match Failure** | < 5 min | Auto-retry via `control.sh repair` |
| **League-Wide Failure** | < 30 min | Tier-1 Ops + Selective Reset SQL |
| **System-Wide Failure** | < 2 hours | Tier-2 Ops + Full System Reset |
| **Data Corruption** | < 4 hours | Tier-3 Ops + Database Restore |

---

## Monitoring and Alerting

### Key Metrics to Monitor

| Metric | Healthy Range | Alert Threshold |
|--------|---------------|-----------------|
| **Health Score** | 8.0 - 10.0 | < 7.0 (Warning), < 5.0 (Critical) |
| **MPH** | > 5 | < 2 (Critical) |
| **Failed Records** | 0 | > 10 (Warning), > 50 (Critical) |
| **Database Connections** | < 80% pool | > 90% (Warning) |
| **Disk Space** | > 20% free | < 10% (Critical) |

### Alert Integration

```bash
# Example: Cron-based health check
0 */2 * * * /path/to/FootballPrediction/scripts/ops/control.sh health | jq -r '.health_score' | awk '{if ($1 < 7) print "ALERT: Health score below 7"}' | mail -s "Health Alert" ops@example.com
```

---

## Appendices

### Appendix A: Command Reference

| Command | Description | Example |
|---------|-------------|---------|
| `./control.sh start` | Start orchestrator daemon | `./control.sh start` |
| `./control.sh stop` | Stop orchestrator gracefully | `./control.sh stop` |
| `./control.sh status` | Show system dashboard | `./control.sh status` |
| `./control.sh health` | Quick health check (JSON) | `./control.sh health` |
| `./control.sh repair` | Reset FAILED records | `./control.sh repair` |
| `./control.sh logs [N]` | Show last N log lines | `./control.sh logs 100` |
| `./control.sh backup` | Create database backup | `./control.sh backup` |
| `./control.sh clean` | Clean old files | `./control.sh clean` |
| `./control.sh restart` | Restart orchestrator | `./control.sh restart` |

### Appendix B: Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NODE_BIN` | `node` | Node.js executable path |
| `DB_HOST` | `172.25.16.1` | Database host |
| `DB_PORT` | `5432` | Database port |
| `DB_NAME` | `football_db` | Database name |
| `DB_USER` | `football_user` | Database user |
| `DB_POOL_SIZE` | `20` | Connection pool size |
| `HTTP_PROXY` | - | Proxy server (optional) |

### Appendix C: Contact Information

| Role | Contact | Escalation |
|------|---------|-------------|
| **Tier-1 Ops** | <ops@example.com> | First-line support |
| **Tier-2 Ops** | <senior-ops@example.com> | Complex issues |
| **Tier-3 Ops** | <architect@example.com> | Architecture changes |
| **On-Call Engineer** | +1-555-0123 | Emergency (24/7) |

### Appendix D: Change History

| Version | Date | Changes |
|---------|------|---------|
| V70.300 | 2026-01-25 | Initial operations manual |
| | | |

---

**Document Owner**: Principal Systems Integration Engineer
**Last Updated**: 2026-01-25
**Next Review**: 2026-02-25
