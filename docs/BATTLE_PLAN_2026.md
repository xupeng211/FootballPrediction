# V146.3 Production Battle Plan 2026
## 🎯 Operation "总攻" - Final Harvest Strategy

**Document Version**: V146.3
**Classification**: SECRET // PRODUCTION READY
**Effective Date**: 2026-01-06
**Cooling Period**: 24 hours (ending: 2026-01-07 00:00 UTC)

---

## 📋 Executive Summary

This document outlines the complete battle plan for the production data harvest operation. The system has achieved **Build Green status** (533/533 tests passing) and is ready for full-scale deployment.

### Current System Status

| Component | Status | Version | Health |
|-----------|--------|---------|--------|
| **Test Suite** | ✅ GREEN | V146.2 | 533/533 passing |
| **Dependencies** | ✅ FROZEN | V146.3 | 279 packages locked |
| **Security** | ✅ AUDITED | V146.3 | Zero hardcoded credentials |
| **L2 Data Lake** | ✅ OPERATIONAL | V145.1 | JSONB + GIN indexed |
| **Ghost Protocol** | ✅ ACTIVE | V144.2 | 30+ fingerprint pool |
| **Circuit Breaker** | ✅ ARMED | V56.4 | EXIT 99 ready |

---

## 🛡️ Phase 0: Pre-Harvest Checklist

### 0.1 Network Precheck

**Execute 15 minutes before harvest start:**

```bash
#!/bin/bash
# scripts/battle/network_precheck.sh

echo "=== Network Precheck ==="
echo ""

# Check 10 proxy ports
PROXY_PORTS=(8000 8001 8002 8003 8004 8005 8006 8007 8008 8009)
for port in "${PROXY_PORTS[@]}"; do
    if nc -z localhost $port 2>/dev/null; then
        echo "✓ Proxy port $port: OPEN"
    else
        echo "✗ Proxy port $port: CLOSED"
        exit 1
    fi
done

# Check database heartbeat
echo ""
echo "=== Database Heartbeat ==="
docker-compose exec -T db pg_isready -U football_user -d football_db
if [ $? -eq 0 ]; then
    echo "✓ Database: READY"
else
    echo "✗ Database: NOT READY"
    exit 1
fi

# Check Redis heartbeat
echo ""
echo "=== Redis Heartbeat ==="
docker-compose exec -T redis redis-cli ping
if [ $? -eq 0 ]; then
    echo "✓ Redis: READY"
else
    echo "✗ Redis: NOT READY"
    exit 1
fi

# Check disk space (minimum 10GB required)
echo ""
echo "=== Disk Space Check ==="
AVAILABLE=$(df -BG . | tail -1 | awk '{print $4}' | sed 's/G//')
if [ $AVAILABLE -gt 10 ]; then
    echo "✓ Disk space: ${AVAILABLE}GB available"
else
    echo "✗ Disk space: ${AVAILABLE}GB (insufficient)"
    exit 1
fi

echo ""
echo "=== All Prechecks Passed ==="
echo "Ready to initiate harvest sequence."
```

**Usage:**
```bash
chmod +x scripts/battle/network_precheck.sh
./scripts/battle/network_precheck.sh
```

### 0.2 Environment Validation

```bash
# Verify production environment variables
grep -E "DB_HOST|DB_NAME|REDIS_HOST" .env | grep -v "^#"

# Expected output:
# DB_HOST=172.25.16.1
# DB_NAME=football_db
# REDIS_HOST=172.25.16.1
```

---

## ⚔️ Phase 1: First Wave Assault

**Objective**: Test system readiness with small-scale harvest (20 matches total)

### 1.1 Wave Alpha: OddsPortal Final Odds (10 matches)

```bash
# Test OddsPortal extraction with circuit breaker monitoring
python -m src.api.collectors.odds_production_extractor \
    --source oddsportal \
    --limit 10 \
    --mode test \
    --circuit-breaker-enabled \
    --log-level INFO
```

**Success Criteria:**
- [ ] All 10 matches extracted successfully
- [ ] Final odds stored in `metrics_multi_source_data` table
- [ ] Integrity audit score: `0.95 < Score < 1.05`
- [ ] Zero IP hard bans (EXIT 99 not triggered)
- [ ] Average response time < 5 seconds

### 1.2 Wave Bravo: FotMob L2 Details (10 matches)

```bash
# Test FotMob L2 extraction with versioning
python -m src.api.collectors.fotmob_core \
    --source fotmob \
    --limit 10 \
    --mode test \
    --l2-version V145.1 \
    --log-level INFO
```

**Success Criteria:**
- [ ] All 10 matches with L2 data extracted
- [ ] `l2_raw_json` field populated (>10KB per record)
- [ ] `l2_data_version` set to "V145.1"
- [ ] Zero corrupted JSON records
- [ ] Average extraction time < 8 seconds

### 1.3 First Wave Validation

```sql
-- Verify first wave results
SELECT
    COUNT(*) as total_matches,
    COUNT(l2_raw_json) as l2_collected,
    AVG(octet_length(l2_raw_json::text)) as avg_l2_size_kb,
    COUNT(DISTINCT l2_data_version) as data_versions
FROM matches
WHERE match_time > NOW() - INTERVAL '1 hour';
```

**Expected Result:**
- `total_matches`: 20
- `l2_collected`: 10
- `avg_l2_size_kb`: >10
- `data_versions`: 1

---

## 🚀 Phase 2: Full Harvest Operation

### 2.1 Cruise Mode Activation

**Execute ONLY after Phase 1 validation succeeds:**

```bash
# Main harvest command (full production scale)
python scripts/production_harvester.py \
    --mode cruise \
    --source all \
    --circuit-breaker-enabled \
    --max-concurrent 5 \
    --retry-limit 3 \
    --log-level INFO \
    --harvest-id V146.3-PROD-$(date +%Y%m%d-%H%M%S)
```

**Command Parameters Explained:**

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `--mode` | `cruise` | Sustained harvesting with adaptive rate limiting |
| `--source` | `all` | Harvest from both FotMob L2 and OddsPortal L3 |
| `--circuit-breaker-enabled` | flag | Enable EXIT 99 auto-shutdown on IP hard ban |
| `--max-concurrent` | `5` | Maximum parallel browser instances |
| `--retry-limit` | `3` | Automatic retry on transient failures |
| `--harvest-id` | auto | Unique identifier for this harvest session |

### 2.2 Monitoring Dashboard

**Open in separate terminal:**

```bash
# Real-time harvest monitoring
watch -n 5 'python scripts/health_check.py --monitor'
```

**Key Metrics to Watch:**

1. **Harvest Velocity**: Target > 50 matches/hour
2. **Success Rate**: Target > 95%
3. **L2 Data Quality**: Target < 5% corrupted records
4. **IP Health**: Zero hard bans detected
5. **Database Write Latency**: Target < 100ms per insert

### 2.3 Integrity Audit Queries

```sql
-- Monitor L2 collection progress
SELECT
    l2_data_version,
    COUNT(*) as match_count,
    COUNT(l2_raw_json) as l2_collected,
    AVG(octet_length(l2_raw_json::text))/1024 as avg_size_kb,
    COUNT(*) FILTER (WHERE octet_length(l2_raw_json::text) < 10240) as corrupted_count
FROM matches
WHERE l2_raw_json IS NOT NULL
GROUP BY l2_data_version
ORDER BY l2_data_version DESC;

-- Check OddsPortal L3 collection
SELECT
    data_source,
    COUNT(*) as records,
    AVG(final_home_odds) as avg_home_odds,
    AVG(final_draw_odds) as avg_draw_odds,
    AVG(final_away_odds) as avg_away_odds
FROM metrics_multi_source_data
WHERE data_source = 'oddsportal'
GROUP BY data_source;
```

---

## 🚨 Phase 3: Emergency Procedures

### 3.1 Circuit Breaker Response

**IF EXIT 99 is triggered (IP Hard Ban detected):**

```bash
# Immediate actions
echo "⚠️  CIRCUIT BREAKER TRIGGERED - IP HARD BAN DETECTED"

# 1. Kill all browser instances
pkill -9 chromium
pkill -9 playwright

# 2. Stop harvest process
docker-compose stop pipeline_worker

# 3. Check circuit breaker logs
tail -100 logs/app.log | grep "CIRCUIT_BREAKER"

# 4. Verify IP ban with diagnostic
python scripts/exploration/debug_ip_reputation.py

# 5. Enter cooldown period (minimum 6 hours)
echo "Enter 6-hour cooldown period..."
echo "Resume at: $(date -d '+6 hours' '+%Y-%m-%d %H:%M:%S UTC')"
```

**Cooldown Period Activities:**
- Monitor IP reputation hourly
- Test with single URL every 2 hours
- Document ban patterns in `docs/IP_BAN_LOG.md`

### 3.2 Data Corruption Recovery

**IF corrupted L2 data detected:**

```bash
# Run L2 cleanup script
python scripts/maintenance/clean_corrupt_l2.py \
    --dry-run \
    --threshold 10240 \
    --l2-version V145.1

# Review preview, then execute:
python scripts/maintenance/clean_corrupt_l2.py \
    --execute \
    --threshold 10240 \
    --l2-version V145.1
```

### 3.3 Database Connection Failures

**IF database becomes unavailable:**

```bash
# 1. Check database container status
docker-compose ps db

# 2. Restart database if needed
docker-compose restart db

# 3. Verify WSL2 bridge connectivity
ping -c 3 172.25.16.1

# 4. Test database connection
docker-compose exec db pg_isready -U football_user -d football_db

# 5. Check database logs
docker-compose logs db --tail 100
```

---

## 📊 Phase 4: Post-Harvest Analysis

### 4.1 Harvest Statistics

```sql
-- Complete harvest report
SELECT
    'Harvest Summary' as report_type,
    COUNT(*) as total_matches_processed,
    COUNT(l2_raw_json) as l2_collected,
    COUNT(m.final_home_odds) as l3_collected,
    AVG(octet_length(l2_raw_json::text))/1024 as avg_l2_size_kb,
    SUM(CASE WHEN octet_length(l2_raw_json::text) < 10240 THEN 1 ELSE 0 END) as corrupted_l2_count
FROM matches m
LEFT JOIN metrics_multi_source_data mmsd ON m.id = mmsd.match_id
WHERE m.match_time > NOW() - INTERVAL '24 hours';
```

### 4.2 Quality Metrics

```python
# Generate harvest quality report
import psycopg2
from src.config_unified import get_settings

settings = get_settings()
conn = psycopg2.connect(
    host=settings.database.host,
    port=settings.database.port,
    database=settings.database.name,
    user=settings.database.user,
    password=settings.database.password.get_secret_value(),
)

cursor = conn.cursor()

# Execute quality queries
queries = {
    "l2_collection_rate": """
        SELECT ROUND(100.0 * COUNT(l2_raw_json) / COUNT(*), 2)
        FROM matches WHERE match_time > NOW() - INTERVAL '24 hours'
    """,
    "l3_integrity_score": """
        SELECT ROUND(AVG(
            1.0 / final_home_odds +
            1.0 / final_draw_odds +
            1.0 / final_away_odds
        ), 4)
        FROM metrics_multi_source_data
        WHERE data_source = 'oddsportal'
        AND collected_at > NOW() - INTERVAL '24 hours'
    """,
}

for metric, query in queries.items():
    cursor.execute(query)
    result = cursor.fetchone()[0]
    print(f"{metric}: {result}")

cursor.close()
conn.close()
```

---

## 🎯 Success Criteria

### Phase 1 (First Wave)
- [x] Network precheck passed
- [ ] 10/10 OddsPortal extractions successful
- [ ] 10/10 FotMob L2 extractions successful
- [ ] Zero IP hard bans
- [ ] L2 data integrity > 95%

### Phase 2 (Full Harvest)
- [ ] Cruise mode activated successfully
- [ ] Harvest velocity > 50 matches/hour
- [ ] Success rate > 95%
- [ ] Circuit breaker remained inactive (no EXIT 99)
- [ ] Database write latency < 100ms

### Phase 4 (Post-Harvest)
- [ ] L2 collection rate > 90%
- [ ] L3 integrity score: 0.98 < Score < 1.02
- [ ] Corrupted data < 5%
- [ ] Zero data loss

---

## 📞 Emergency Contacts

| Role | Contact | Availability |
|------|---------|--------------|
| **Lead DevOps Engineer** | @system | 24/7 |
| **Database Administrator** | @db-admin | Business hours |
| **Network Security** | @net-sec | Emergency only |

---

## 📝 Change Log

| Date | Version | Changes |
|------|---------|---------|
| 2026-01-06 | V146.3 | Initial production battle plan |
| | | Dependencies frozen (279 packages) |
| | | Security audit completed (100% pass) |
| | | Build Green status achieved (533/533 tests) |

---

## ⚠️ Critical Reminders

1. **NEVER** skip Phase 0 precheck
2. **NEVER** proceed to Phase 2 if Phase 1 fails
3. **ALWAYS** monitor circuit breaker status
4. **IMMEDIATELY** halt if EXIT 99 is triggered
5. **DOCUMENT** all incidents in `docs/INCIDENT_LOG.md`

---

**This document is classified SECRET. Unauthorized distribution is prohibited.**

*Generated by V146.3 Production Freeze Protocol*
*Document Control: V146.3-BATTLE-PLAN-2026*
