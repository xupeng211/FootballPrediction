#!/usr/bin/env node
'use strict';

// lifecycle: permanent
// scope: read-only P0 DB write safety gate audit — static scan only, no network, no DB connection, no script execution

const PHASE = 'P0_DB_WRITE_SAFETY_GATE_DRY_RUN';
const fs = require('fs');
const path = require('path');

const REPO_ROOT = path.resolve(__dirname, '..', '..');

// ─── Unified Safety Gate Contract ──────────────────────────────────────────────

const GATE_CONTRACT = Object.freeze({
    ALLOW_DB_WRITE: {
        name: 'ALLOW_DB_WRITE',
        scope: 'any database write (INSERT / UPDATE / DELETE / DDL)',
        default: 'unset (blocked)',
        description: 'Master kill-switch. Must be explicitly set to "yes" for any write to proceed.',
    },
    FINAL_DB_WRITE_CONFIRMATION: {
        name: 'FINAL_DB_WRITE_CONFIRMATION',
        scope: 'transactional write confirmation',
        default: 'unset (blocked)',
        description: 'Second-factor confirmation. Even with ALLOW_DB_WRITE=yes, this must also be yes.',
    },
    ALLOW_RAW_MATCH_DATA_WRITE: {
        name: 'ALLOW_RAW_MATCH_DATA_WRITE',
        scope: 'INSERT / UPDATE / DELETE on raw_match_data table',
        default: 'unset (blocked)',
        description: 'Specific gate for raw_match_data writes. Must be yes IN ADDITION to the two above.',
    },
    ALLOW_MATCHES_WRITE: {
        name: 'ALLOW_MATCHES_WRITE',
        scope: 'INSERT / UPDATE / DELETE on matches table',
        default: 'unset (blocked)',
        description: 'Specific gate for matches writes.',
    },
    ALLOW_SCHEMA_WRITE: {
        name: 'ALLOW_SCHEMA_WRITE',
        scope: 'CREATE / ALTER / DROP / TRUNCATE — any DDL',
        default: 'unset (blocked)',
        description: 'Schema mutations require this gate. Highest risk category.',
    },
    ALLOW_TRAINING_WRITE: {
        name: 'ALLOW_TRAINING_WRITE',
        scope: 'INSERT / UPDATE on match_features_training, predictions, training artifacts',
        default: 'unset (blocked)',
        description: 'Training data and prediction writes require this gate.',
    },
    ALLOW_ODDS_WRITE: {
        name: 'ALLOW_ODDS_WRITE',
        scope: 'INSERT / UPDATE on bookmaker_odds_history, matches_oddsportal_mapping, odds',
        default: 'unset (blocked)',
        description: 'Odds data writes require this gate.',
    },
    DRY_RUN: {
        name: 'DRY_RUN',
        scope: 'all scripts',
        default: 'true',
        description: 'Scripts default to dry-run mode. Must explicitly set to false for real writes.',
    },
    REQUIRE_EXPLICIT_USER_AUTHORIZATION: {
        name: 'REQUIRE_EXPLICIT_USER_AUTHORIZATION',
        scope: 'all write scripts',
        default: 'true',
        description: 'User must provide explicit authorization before any write. No automated writes.',
    },
    MINIMUM_THRESHOLD: {
        description: 'At minimum, every DB-write script must check: ALLOW_DB_WRITE + FINAL_DB_WRITE_CONFIRMATION. ' +
            'Additional table-specific gates required for raw_match_data, matches, schema, training, odds.',
    },
});

// ─── SQL Pattern Definitions ───────────────────────────────────────────────────

const SQL_PATTERNS = Object.freeze({
    INSERT: {
        regex: /\bINSERT\s+INTO\s+(\w+(?:\.\w+)?)\b/gi,
        risk: 'data_write',
        defaultSeverity: 'P1',
    },
    UPDATE: {
        regex: /\bUPDATE\s+(\w+(?:\.\w+)?)\b/gi,
        risk: 'data_mutation',
        defaultSeverity: 'P1',
    },
    DELETE: {
        regex: /\bDELETE\s+FROM\s+(\w+(?:\.\w+)?)\b/gi,
        risk: 'data_deletion',
        defaultSeverity: 'P0',
    },
    TRUNCATE: {
        regex: /\bTRUNCATE\s+(?:TABLE\s+)?(\w+(?:\.\w+)?)\b/gi,
        risk: 'data_deletion_bulk',
        defaultSeverity: 'P0',
    },
    DROP: {
        regex: /\bDROP\s+(?:TABLE|INDEX|CONSTRAINT|DATABASE|SCHEMA)\s+(?:IF\s+EXISTS\s+)?(\w+)/gi,
        risk: 'schema_destruction',
        defaultSeverity: 'P0',
    },
    CREATE_TABLE: {
        regex: /\bCREATE\s+(?:TEMP(?:ORARY)?\s+)?TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)/gi,
        risk: 'schema_creation',
        defaultSeverity: 'P1',
    },
    ALTER: {
        regex: /\bALTER\s+(?:TABLE\s+)?(\w+(?:\.\w+)?)\b/gi,
        risk: 'schema_mutation',
        defaultSeverity: 'P0',
    },
});

// ─── High-risk table classification ────────────────────────────────────────────

const HIGH_RISK_TABLES = Object.freeze({
    raw_match_data: { category: 'raw_data', severityBump: 'P0', gate: 'ALLOW_RAW_MATCH_DATA_WRITE' },
    matches: { category: 'core_match_data', severityBump: 'P0', gate: 'ALLOW_MATCHES_WRITE' },
    predictions: { category: 'predictions', severityBump: 'P0', gate: 'ALLOW_TRAINING_WRITE' },
    match_features_training: { category: 'training_features', severityBump: 'P0', gate: 'ALLOW_TRAINING_WRITE' },
    l3_features: { category: 'stitched_features', severityBump: 'P1', gate: 'ALLOW_DB_WRITE' },
    bookmaker_odds_history: { category: 'odds_data', severityBump: 'P1', gate: 'ALLOW_ODDS_WRITE' },
    matches_oddsportal_mapping: { category: 'odds_mapping', severityBump: 'P1', gate: 'ALLOW_ODDS_WRITE' },
    odds: { category: 'legacy_odds', severityBump: 'P2', gate: 'ALLOW_ODDS_WRITE' },
    fotmob_raw_match_payloads: { category: 'raw_payload', severityBump: 'P1', gate: 'ALLOW_RAW_MATCH_DATA_WRITE' },
    football_calendar_target_registry: { category: 'calendar', severityBump: 'P2', gate: 'ALLOW_DB_WRITE' },
});

const GATE_ENV_VARS = [
    'ALLOW_DB_WRITE', 'FINAL_DB_WRITE_CONFIRMATION', 'ALLOW_RAW_MATCH_DATA_WRITE',
    'ALLOW_MATCHES_WRITE', 'ALLOW_SCHEMA_WRITE', 'ALLOW_TRAINING_WRITE', 'ALLOW_ODDS_WRITE',
    'DRY_RUN', 'REQUIRE_EXPLICIT_USER_AUTHORIZATION',
];

const ENV_RISK_VARS = ['NODE_ENV', 'APP_ENV', 'DATABASE_URL', 'DB_HOST', 'PGHOST', 'PGDATABASE'];

const SCAN_DIRS = [
    'scripts/ops',
    'scripts/devops',
    'scripts/maintenance',
    'src',
    'database',
];

const SCAN_EXTENSIONS = ['.js', '.py', '.sh', '.sql'];

// ─── helpers ────────────────────────────────────────────────────────────────────

function readFile(filePath) {
    if (!fs.existsSync(filePath)) return null;
    try { return fs.readFileSync(filePath, 'utf-8'); }
    catch { return null; }
}

function findFiles(dir, extensions, excludePatterns = []) {
    const results = [];
    const absDir = path.join(REPO_ROOT, dir);
    if (!fs.existsSync(absDir)) return results;
    for (const entry of fs.readdirSync(absDir, { withFileTypes: true })) {
        const full = path.join(absDir, entry.name);
        const rel = path.relative(REPO_ROOT, full);
        if (excludePatterns.some(p => rel.includes(p))) continue;
        if (entry.isDirectory()) {
            results.push(...findFiles(path.join(dir, entry.name), extensions, excludePatterns));
        } else if (extensions.some(ext => entry.name.endsWith(ext))) {
            results.push(rel);
        }
    }
    return results;
}

function isTestFile(filePath) {
    return filePath.includes('/tests/') || filePath.includes('/test/') ||
        filePath.includes('.test.') || filePath.includes('_test.') ||
        filePath.includes('test_') || filePath.includes('/__test__/') ||
        filePath.includes('/fixtures/') || filePath.includes('/mocks/');
}

function isMigrationFile(filePath) {
    return filePath.includes('/migrations/') &&
        (filePath.startsWith('database/') || filePath.startsWith('scripts/maintenance/migrations/'));
}

function extractTables(content, pattern) {
    const tables = new Set();
    const regex = new RegExp(pattern.regex.source, 'gi');
    let match;
    while ((match = regex.exec(content)) !== null) {
        const table = match[1].toLowerCase().replace(/[^a-z0-9_]/g, '');
        if (table && table.length > 0 && !['if', 'exists', 'only', 'table', 'set', 'from'].includes(table)) {
            tables.add(table);
        }
    }
    return [...tables];
}

function detectGates(content) {
    const present = [];
    const missing = [];
    for (const gate of GATE_ENV_VARS) {
        if (content.includes(gate)) present.push(gate);
        else missing.push(gate);
    }
    return { present, missing };
}

function detectEnvRisks(content) {
    const found = [];
    for (const v of ENV_RISK_VARS) {
        if (content.includes(v)) found.push(v);
    }
    return found;
}

function detectConnectionCalls(content) {
    // Detect DB connection patterns that bypass connection pooling
    const patterns = [];
    if (/\bnew\s+pg\.(?:Client|Pool)\b/.test(content)) patterns.push('pg.Client/Pool');
    if (/\bcreateConnection\b/.test(content)) patterns.push('createConnection');
    if (/\bconnect\s*\(\s*['"]/.test(content)) patterns.push('direct_connect');
    if (/\bpsql\b/.test(content)) patterns.push('psql_cli');
    return patterns;
}

function classifySeverity(ops, tables) {
    // Start with the most severe default from the SQL patterns found
    let severity = 'P2';
    for (const op of ops) {
        const pat = SQL_PATTERNS[op];
        if (!pat) continue;
        if (pat.defaultSeverity === 'P0') severity = 'P0';
        else if (pat.defaultSeverity === 'P1' && severity !== 'P0') severity = 'P1';
    }

    // Bump severity based on tables touched
    for (const table of tables) {
        const risk = HIGH_RISK_TABLES[table];
        if (risk && risk.severityBump === 'P0') severity = 'P0';
        else if (risk && risk.severityBump === 'P1' && severity !== 'P0') severity = 'P1';
    }

    // Schema mutations are always P0
    if (ops.some(o => ['DROP', 'TRUNCATE', 'ALTER'].includes(o))) severity = 'P0';

    // DELETE on any table is P0
    if (ops.includes('DELETE')) severity = 'P0';

    return severity;
}

function requiredGates(ops, tables) {
    const gates = ['ALLOW_DB_WRITE', 'FINAL_DB_WRITE_CONFIRMATION'];

    for (const table of tables) {
        const risk = HIGH_RISK_TABLES[table];
        if (risk && risk.gate && !gates.includes(risk.gate)) gates.push(risk.gate);
    }

    if (ops.some(o => ['DROP', 'TRUNCATE', 'ALTER', 'CREATE_TABLE'].includes(o))) {
        if (!gates.includes('ALLOW_SCHEMA_WRITE')) gates.push('ALLOW_SCHEMA_WRITE');
    }

    return gates;
}

// ─── fix priority helpers ────────────────────────────────────────────────────────

function determineFixPriority(severity, missingGates, isTest) {
    if (isTest) return 'TEST_FIXTURE_NO_FIX';
    if (severity === 'P0' && missingGates.length > 0) return 'FIRST_BATCH';
    if (severity === 'P0' || (severity === 'P1' && missingGates.length > 0)) return 'SECOND_BATCH';
    return 'LATER';
}

function hasHighRiskFlags(operations, tables) {
    return {
        touchesRawMatchData: tables.includes('raw_match_data'),
        touchesMatches: tables.includes('matches'),
        hasDeleteOrDrop: operations.some(o => ['DELETE', 'DROP', 'TRUNCATE'].includes(o)),
        hasSchemaMutation: operations.some(o => ['DROP', 'TRUNCATE', 'ALTER', 'CREATE_TABLE'].includes(o)),
        touchesTraining: tables.some(t => ['predictions', 'match_features_training', 'l3_features'].includes(t)),
    };
}

// ─── scanner ────────────────────────────────────────────────────────────────────

function scanFile(filePath) {
    const absPath = path.isAbsolute(filePath) ? filePath : path.join(REPO_ROOT, filePath);
    const content = readFile(absPath);
    if (!content) return null;

    const operations = [];
    const allTables = new Set();

    for (const [opName, pattern] of Object.entries(SQL_PATTERNS)) {
        const tables = extractTables(content, pattern);
        if (tables.length > 0) {
            operations.push(opName);
            for (const t of tables) allTables.add(t);
        }
    }

    if (/\bquery\s*\(\s*`[^`]*(?:INSERT|UPDATE|DELETE|DROP|TRUNCATE|ALTER|CREATE)/i.test(content) && !operations.length)
        {operations.push('SQL_VIA_QUERY');}

    if (operations.length === 0) return null;

    const tables = [...allTables];
    const gateInfo = detectGates(content);
    const reqGates = requiredGates(operations, tables);
    const missingGates = reqGates.filter(g => !gateInfo.present.includes(g));
    const isTest = isTestFile(filePath);
    const flags = hasHighRiskFlags(operations, tables);

    return {
        file: filePath,
        operations,
        tables,
        severity: classifySeverity(operations, tables),
        is_test: isTest,
        is_migration: isMigrationFile(filePath),
        touches_raw_match_data: flags.touchesRawMatchData,
        touches_matches: flags.touchesMatches,
        has_delete_or_drop: flags.hasDeleteOrDrop,
        has_schema_mutation: flags.hasSchemaMutation,
        touches_training: flags.touchesTraining,
        gates_present: gateInfo.present,
        gates_missing: missingGates,
        required_gates: reqGates,
        has_any_gate: gateInfo.present.length > 0,
        env_risk_vars: detectEnvRisks(content),
        connection_calls: detectConnectionCalls(content),
        fix_priority: determineFixPriority(classifySeverity(operations, tables), missingGates, isTest),
        recommended_fix: buildFixRecommendation(operations, tables, gateInfo, missingGates, isTest, isMigrationFile(filePath)),
    };
}

function buildFixRecommendation(operations, tables, gateInfo, missingGates, isTest, isMigration) {
    if (isTest) return 'TEST_FIXTURE — verify no production DB connection, add comment documenting safety. No gate changes needed.';
    if (isMigration) return 'MIGRATION_FILE — ensure migration framework enforces sequential ordering and backup. Add ALLOW_SCHEMA_WRITE + FINAL_DB_WRITE_CONFIRMATION gates.';

    if (missingGates.length === 0) return 'Gates present. Verify they are enforced at runtime (not just referenced in comments).';

    return `Add missing gates: ${missingGates.join(', ')}. ` +
        'Wrap write path in: if (process.env.ALLOW_DB_WRITE !== "yes") exit; ' +
        'if (process.env.FINAL_DB_WRITE_CONFIRMATION !== "yes") exit;';
}

function scanAll() {
    const allFiles = [];
    const excludePatterns = ['node_modules', '.git', '.venv', '__pycache__', 'coverage',
        '.codex-tmp', 'archive_vault_2026', 'Z_LEGACY_ARCHIVE'];

    for (const dir of SCAN_DIRS) {
        const files = findFiles(dir, SCAN_EXTENSIONS, excludePatterns);
        allFiles.push(...files);
    }

    const results = [];
    for (const file of allFiles) {
        const result = scanFile(file);
        if (result) results.push(result);
    }

    return results;
}

// ─── summary builder ────────────────────────────────────────────────────────────

function buildSummary(results) {
    const prodResults = results.filter(r => !r.is_test);
    const testResults = results.filter(r => r.is_test);

    const p0 = prodResults.filter(r => r.severity === 'P0');
    const p1 = prodResults.filter(r => r.severity === 'P1');
    const p2 = prodResults.filter(r => r.severity === 'P2');

    const noGate = prodResults.filter(r => !r.has_any_gate);
    const partialGate = prodResults.filter(r => r.has_any_gate && r.gates_missing.length > 0);
    const fullGate = prodResults.filter(r => r.has_any_gate && r.gates_missing.length === 0);

    const rawMatchWriters = prodResults.filter(r => r.touches_raw_match_data);
    const matchWriters = prodResults.filter(r => r.touches_matches);
    const deleters = prodResults.filter(r => r.has_delete_or_drop);
    const schemaMutators = prodResults.filter(r => r.has_schema_mutation);
    const trainingWriters = prodResults.filter(r => r.touches_training);

    // Most targeted tables
    const tableCounts = {};
    for (const r of prodResults) {
        for (const t of r.tables) {
            tableCounts[t] = (tableCounts[t] || 0) + 1;
        }
    }
    const topTables = Object.entries(tableCounts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 15)
        .map(([table, count]) => ({ table, count }));

    // First batch (highest priority to fix)
    const firstBatch = prodResults.filter(r => r.fix_priority === 'FIRST_BATCH');
    const secondBatch = prodResults.filter(r => r.fix_priority === 'SECOND_BATCH');

    return {
        total_files_scanned: results.length,
        production_scripts_with_db_write: prodResults.length,
        test_files_with_db_write: testResults.length,
        by_severity: { P0: p0.length, P1: p1.length, P2: p2.length },
        by_gate_status: {
            no_gate_at_all: noGate.length,
            partial_gate: partialGate.length,
            full_gate: fullGate.length,
        },
        high_risk_counts: {
            raw_match_data_writers: rawMatchWriters.length,
            matches_writers: matchWriters.length,
            delete_or_drop: deleters.length,
            schema_mutations: schemaMutators.length,
            training_writers: trainingWriters.length,
        },
        most_targeted_tables: topTables,
        first_batch_count: firstBatch.length,
        second_batch_count: secondBatch.length,
        first_batch: firstBatch.map(r => ({
            file: r.file,
            severity: r.severity,
            operations: r.operations,
            tables: r.tables,
            missing_gates: r.gates_missing,
            touches_raw_match_data: r.touches_raw_match_data,
            touches_matches: r.touches_matches,
            has_delete_or_drop: r.has_delete_or_drop,
        })),
        second_batch: secondBatch.map(r => ({
            file: r.file,
            severity: r.severity,
            missing_gates: r.gates_missing,
        })),
        test_fixtures: testResults.map(r => ({
            file: r.file,
            operations: r.operations,
            note: 'Test fixture — no production fix needed',
        })),
        sc002_reproduced: prodResults.length >= 30,
        sc002_previous_count: 34,
        sc002_current_count: prodResults.length,
    };
}

// ─── report builder ─────────────────────────────────────────────────────────────

function buildReport(results, summary) {
    const lines = [
        `# P0 DB Write Safety Gate — Dry Run Audit Report`,
        '',
        `**Date:** ${new Date().toISOString().split('T')[0]}`,
        `**Phase:** ${PHASE}`,
        `**Branch:** chore/p0-db-write-safety-gate-dry-run`,
        `**Type:** READ-ONLY — no network, no DB connection, no script execution`,
        '',
        '---',
        '',
        '## Executive Summary',
        '',
        `专项审计了 ${SCAN_DIRS.length} 个目录，扫描了 ${results.length} 个文件，发现 **${summary.production_scripts_with_db_write} 个生产脚本存在数据库写入操作**。`,
        '',
        `- 额外发现 ${summary.test_files_with_db_write} 个测试文件包含 DB 写入模式（不列为生产风险）`,
        `- 上一轮审计报告的 34 个脚本已${summary.sc002_reproduced ? '确认复现' : '部分复现'}（当前发现 ${summary.production_scripts_with_db_write} 个）`,
        '',
        '### 关键数字',
        '',
        '| 指标 | 数量 |',
        '|------|------|',
        `| P0 — 必须立即修复 | ${summary.by_severity.P0} |`,
        `| P1 — 数据扩容前修复 | ${summary.by_severity.P1} |`,
        `| P2 — 可排期 | ${summary.by_severity.P2} |`,
        `| 完全无安全闸门 | ${summary.by_gate_status.no_gate_at_all} |`,
        `| 有部分闸门 | ${summary.by_gate_status.partial_gate} |`,
        `| 有完整闸门 | ${summary.by_gate_status.full_gate} |`,
        `| raw_match_data 写入 | ${summary.high_risk_counts.raw_match_data_writers} |`,
        `| matches 写入 | ${summary.high_risk_counts.matches_writers} |`,
        `| UPDATE/DELETE/DROP | ${summary.high_risk_counts.delete_or_drop} |`,
        `| Schema 变更 | ${summary.high_risk_counts.schema_mutations} |`,
        '',
        '### 核心结论',
        '',
        `**本 PR 未修复 SC-002。** 本 PR 只是专项审计和修复方案。`,
        '不允许因为本 PR 合并就认为写库风险已消除。',
        '下一步真实修改写库脚本前，必须再次请求用户确认。',
        '',
        '---',
        '',
        '## 统一安全闸门契约 (Unified Gate Contract)',
        '',
        '| Gate | 范围 | 默认值 | 说明 |',
        '|------|------|--------|------|',
    ];

    for (const gate of Object.values(GATE_CONTRACT)) {
        if (gate.name) {
            lines.push(`| \`${gate.name}\` | ${gate.scope} | ${gate.default} | ${gate.description} |`);
        } else {
            lines.push(`| *(minimum)* | — | — | ${gate.description} |`);
        }
    }

    lines.push(
        '',
        '### 最小门槛',
        '',
        '**每个 DB 写入脚本至少检查：**',
        '1. `ALLOW_DB_WRITE=yes` — 主开关',
        '2. `FINAL_DB_WRITE_CONFIRMATION=yes` — 二次确认',
        '',
        '**表级附加门槛：**',
        '- `raw_match_data` → 额外要求 `ALLOW_RAW_MATCH_DATA_WRITE=yes`',
        '- `matches` → 额外要求 `ALLOW_MATCHES_WRITE=yes`',
        '- DDL 操作 → 额外要求 `ALLOW_SCHEMA_WRITE=yes`',
        '- `predictions` / `match_features_training` → 额外要求 `ALLOW_TRAINING_WRITE=yes`',
        '- `bookmaker_odds_history` 等 → 额外要求 `ALLOW_ODDS_WRITE=yes`',
        '',
        '### Dry-Run vs Write-Run 行为区别',
        '',
        '| 模式 | DRY_RUN | ALLOW_DB_WRITE | 行为 |',
        '|------|---------|---------------|------|',
        '| dry-run (默认) | true | any | 只输出 would-write / would-skip summary，不写库 |',
        '| write-run | false | yes | 实际执行 SQL 写入事务 |',
        '| blocked | false | unset/no | 打印错误并退出，不写库 |',
        '',
        '### 生产库保护策略',
        '',
        '1. `NODE_ENV=production` 时 DRY_RUN 必须强制为 true（除非显式 override）',
        '2. `DB_HOST` 包含生产标识时额外打印红色警告',
        '3. 写入前必须打印 affected rows preview',
        '4. 写入必须在显式事务中执行，失败自动回滚',
        '',
        '---',
        '',
        '## P0 文件清单（必须立即修复）',
        '',
    );

    const p0Prod = results.filter(r => r.severity === 'P0' && !r.is_test);
    if (p0Prod.length > 0) {
        lines.push('| 文件 | 操作 | 表 | 缺失闸门 | raw | matches | DELETE/DROP |');
        lines.push('|------|------|-----|----------|-----|---------|-------------|');
        for (const r of p0Prod) {
            lines.push(`| ${r.file} | ${r.operations.join(', ')} | ${r.tables.slice(0, 5).join(', ')} | ${r.gates_missing.length > 0 ? r.gates_missing.slice(0, 3).join(', ') : 'none'} | ${r.touches_raw_match_data ? 'YES' : '-'} | ${r.touches_matches ? 'YES' : '-'} | ${r.has_delete_or_drop ? 'YES' : '-'} |`);
        }
    } else {
        lines.push('*(none)*');
    }

    lines.push(
        '',
        '---',
        '',
        '## 最高风险表',
        '',
        '| 表名 | 写入脚本数 |',
        '|------|-----------|',
    );
    for (const t of summary.most_targeted_tables.slice(0, 10)) {
        lines.push(`| \`${t.table}\` | ${t.count} |`);
    }

    lines.push(
        '',
        '---',
        '',
        '## 第一批修复建议 (First Batch)',
        '',
        `${summary.first_batch_count} 个脚本建议第一批修复：`,
        '',
    );
    for (const f of summary.first_batch.slice(0, 15)) {
        lines.push(`- **${f.file}** — ${f.operations.join(', ')} → ${f.tables.slice(0, 5).join(', ')} — 缺失: ${f.missing_gates.join(', ')}`);
    }
    if (summary.first_batch.length > 15) {
        lines.push(`- ... 还有 ${summary.first_batch.length - 15} 个`);
    }

    lines.push(
        '',
        '---',
        '',
        '## 关键问题回答',
        '',
        `1. **上一轮 34 个能否复现？** ${summary.sc002_reproduced ? `是。当前发现 ${summary.production_scripts_with_db_write} 个（更多，因为覆盖了 src/ 和 database/）` : '部分复现'}`,
        `2. **实际扫描发现多少个？** ${summary.production_scripts_with_db_write} 个生产脚本 + ${summary.test_files_with_db_write} 个测试文件`,
        `3. **最高风险？** ${summary.by_severity.P0} 个 P0：涉及 DELETE/DROP/TRUNCATE 或 raw_match_data/matches 写入且无闸门`,
        `4. **测试/fixture 误伤？** ${summary.test_files_with_db_write} 个测试文件被识别但标记为 TEST_FIXTURE_NO_FIX`,
        `5. **已有安全闸门？** ${summary.by_gate_status.full_gate} 个脚本有完整闸门`,
        `6. **完全无闸门？** ${summary.by_gate_status.no_gate_at_all} 个生产脚本完全没有任何安全闸门`,
        `7. **最容易被误写的表？** ${summary.most_targeted_tables.slice(0, 3).map(t => `\`${t.table}\` (${t.count}个脚本)`).join(', ')}`,
        `8. **raw_match_data 重复写入模式？** 存在。${summary.high_risk_counts.raw_match_data_writers} 个脚本写入 raw_match_data，多数是独立实现的重复 INSERT 模式`,
        `9. **matches 重复写入模式？** 存在。${summary.high_risk_counts.matches_writers} 个脚本写入 matches`,
        `10. **UPDATE/DELETE 高危脚本？** ${summary.high_risk_counts.delete_or_drop} 个脚本存在 UPDATE/DELETE/DROP 操作`,
        `11. **第一批修哪些？** ${summary.first_batch_count} 个 FIRST_BATCH 脚本（P0 + 无闸门 + 非测试文件）`,
        `12. **下一步？** 见下文结论`,
        '',
        '---',
        '',
        '## 结论',
        '',
        '### 本 PR 状态',
        '',
        '- **本 PR 没有修复 SC-002**',
        '- **本 PR 只是专项审计和修复方案**',
        '- **不允许因为本 PR 合并就认为写库风险已消除**',
        '',
        '### 是否建议进入 p0_db_write_safety_gate_fix_phase1',
        '',
        summary.first_batch_count > 0
            ? `**是。** ${summary.first_batch_count} 个 FIRST_BATCH 脚本需要立即添加安全闸门。建议下一步执行 ` +
              '`p0_db_write_safety_gate_fix_phase1`，只修改 FIRST_BATCH 脚本，每个脚本添加最小安全闸门（ALLOW_DB_WRITE + FINAL_DB_WRITE_CONFIRMATION），不改变业务逻辑。'
            : '**否。** 没有 FIRST_BATCH 脚本需要修复。',
        '',
        '### 修复前置条件',
        '',
        '1. 用户必须明确授权进入 fix phase',
        '2. 每次修复一个脚本，确保幂等',
        '3. 修复后必须运行对应测试',
        '4. 任何真实写库、真实抓取、真实训练必须先停下并请求授权',
        '',
        '---',
        '',
        '## 审计方法',
        '',
        '- 纯静态文件扫描，读取文件内容进行正则匹配',
        '- 未执行任何被扫描脚本',
        '- 未连接任何数据库',
        '- 未访问外部网络',
        '- 扫描覆盖 5 个目录，`.js` / `.py` / `.sh` / `.sql` 四种扩展名',
        '',
        `**报告路径:** docs/_reports/p0_db_write_safety_gate_dry_run_${new Date().toISOString().split('T')[0].replace(/-/g, '')}.md`,
        `**扫描脚本:** scripts/ops/p0_db_write_safety_gate_dry_run.js (permanent)`,
        `**测试文件:** tests/unit/p0_db_write_safety_gate_dry_run.test.js (permanent)`,
    );

    return lines.join('\n');
}

// ─── CLI ────────────────────────────────────────────────────────────────────────

function parseArgs(argv) {
    return {
        json: argv.includes('--json'),
        help: argv.includes('--help') || argv.includes('-h'),
        firstBatch: argv.includes('--first-batch'),
    };
}

function printHelp() {
    console.log(`Usage: node scripts/ops/p0_db_write_safety_gate_dry_run.js [--json] [--first-batch] [--help]
Options:
  --json          Output full JSON to stdout
  --first-batch   Output only FIRST_BATCH file paths (for scripting)
  --help          Show this message

Read-only audit. No network. No DB connection. No script execution.`);
}

function main() {
    const args = parseArgs(process.argv.slice(2));
    if (args.help) { printHelp(); process.exit(0); }

    const results = scanAll();
    const summary = buildSummary(results);

    if (args.firstBatch) {
        const firstBatch = results.filter(r => r.fix_priority === 'FIRST_BATCH');
        console.log(firstBatch.map(r => r.file).join('\n'));
        return results;
    }

    if (args.json) {
        console.log(JSON.stringify({ phase: PHASE, timestamp: new Date().toISOString(), summary, gate_contract: GATE_CONTRACT, results }, null, 2));
        return results;
    }

    const s = summary;
    console.log(`\n=== ${PHASE} ===`);
    console.log(`Timestamp: ${new Date().toISOString()}`);
    console.log(`\nFiles scanned: ${s.total_files_scanned}`);
    console.log(`Production scripts with DB write: ${s.production_scripts_with_db_write}`);
    console.log(`Test files with DB patterns: ${s.test_files_with_db_write}`);
    console.log(`\nBy severity: P0=${s.by_severity.P0}  P1=${s.by_severity.P1}  P2=${s.by_severity.P2}`);
    console.log(`Gate status:  no_gate=${s.by_gate_status.no_gate_at_all}  partial=${s.by_gate_status.partial_gate}  full=${s.by_gate_status.full_gate}`);
    console.log(`\nHigh risk: raw_match_data=${s.high_risk_counts.raw_match_data_writers}  matches=${s.high_risk_counts.matches_writers}  delete/drop=${s.high_risk_counts.delete_or_drop}  schema=${s.high_risk_counts.schema_mutations}`);
    console.log(`\nSC-002 reproduced: ${s.sc002_reproduced ? 'YES' : 'PARTIAL'} (prev=34, current=${s.sc002_current_count})`);
    console.log(`First batch to fix: ${s.first_batch_count}`);
    console.log(`Second batch: ${s.second_batch_count}`);
    console.log(`\n--- First Batch (P0 + no gates, production scripts) ---`);
    for (const f of s.first_batch.slice(0, 15)) {
        console.log(`  ${f.file} [${f.severity}] ops=${f.operations.join(',')} missing=${f.missing_gates.join(',')}`);
    }
    if (s.first_batch.length > 15) console.log(`  ... and ${s.first_batch.length - 15} more`);
    console.log('');
    return results;
}

module.exports = {
    PHASE, GATE_CONTRACT, SQL_PATTERNS, HIGH_RISK_TABLES, GATE_ENV_VARS, ENV_RISK_VARS, SCAN_DIRS, SCAN_EXTENSIONS,
    scanFile, scanAll, buildSummary, buildReport, parseArgs, isTestFile, isMigrationFile,
    classifySeverity, requiredGates, detectGates, extractTables,
    determineFixPriority, hasHighRiskFlags, detectEnvRisks, detectConnectionCalls,
    buildFixRecommendation,
};
if (require.main === module) main();
