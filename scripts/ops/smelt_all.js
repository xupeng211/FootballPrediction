#!/usr/bin/env node
/**
 * V176 全量熔炼触发器
 * ====================
 *
 * 调用 FeatureSmelter 执行特征熔炼
 *
 * 用法:
 *   node smelt_all.js                     # 仅处理缺失特征的记录（WRITE MODE）
 *   node smelt_all.js --full-recalculate  # 重新计算所有特征（WRITE MODE）
 *   node smelt_all.js --dry-run           # NO-WRITE 预览模式（安全，不写库）
 *   node smelt_all.js --dry-run --limit 1 # 预览 1 条
 *   node smelt_all.js --no-write          # 同上，显式 no-write
 *   node smelt_all.js --preview           # 同上，显式 preview
 *   node smelt_all.js --preview --limit 5 # 预览前 5 条
 *   node smelt_all.js --dry-run --full-recalculate --match-ids 53_aaa,53_bbb  # 精确 match_id no-write 预览
 *
 * @module scripts/ops/smelt_all
 * @version V176.2.0
 */

'use strict';

const { FeatureSmelter } = require('../../src/feature_engine/smelter/FeatureSmelter');
const { assertDbWriteAllowed } = require('./helpers/db_write_guard');

// ═══════════════════════════════════════════════════════════════════════════════
// --match-ids helpers (GOLD-AUDIT-2BB)
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Parse a comma-separated match_id string into a trimmed array.
 * Returns { matchIds: string[] | null, error: string | null }.
 */
function parseMatchIdsArg(raw) {
    if (raw === undefined || raw === null || raw === '') {
        return { matchIds: null, error: '--match-ids requires a comma-separated list of match IDs' };
    }

    const ids = raw.split(',').map(s => s.trim()).filter(s => s.length > 0);

    // Check for empty entries (e.g. "a,,b" or "a, ,b")
    const rawParts = raw.split(',');
    if (rawParts.some(p => p.trim() === '')) {
        return { matchIds: null, error: '--match-ids contains empty entry after trimming' };
    }

    if (ids.length === 0) {
        return { matchIds: null, error: '--match-ids list is empty' };
    }

    return { matchIds: ids, error: null };
}

/**
 * Validate a parsed matchIds array for duplicates. Returns error string or null.
 */
function validateMatchIds(matchIds) {
    if (!Array.isArray(matchIds) || matchIds.length === 0) {
        return 'matchIds must be a non-empty array';
    }

    const seen = new Set();
    for (const id of matchIds) {
        if (seen.has(id)) {
            return `Duplicate match_id "${id}" in --match-ids list`;
        }
        seen.add(id);
    }

    return null;
}

function parseArgs(argv) {
    const fullRecalculate = argv.includes('--full-recalculate');
    const dryRun = argv.includes('--dry-run');
    const noWrite = argv.includes('--no-write');
    const preview = argv.includes('--preview');
    const isNoWrite = dryRun || noWrite || preview;

    let limit = 500; // default batch size
    const limitIdx = argv.indexOf('--limit');
    if (limitIdx !== -1 && limitIdx + 1 < argv.length) {
        const parsed = parseInt(argv[limitIdx + 1], 10);
        if (!Number.isNaN(parsed) && parsed > 0) {
            limit = parsed;
        }
    }

    // --match-ids parsing (GOLD-AUDIT-2BB)
    let matchIds = null;
    let matchIdsError = null;
    const matchIdsIdx = argv.indexOf('--match-ids');
    if (matchIdsIdx !== -1 && matchIdsIdx + 1 < argv.length) {
        const raw = argv[matchIdsIdx + 1];
        const parsed = parseMatchIdsArg(raw);
        if (parsed.error) {
            matchIdsError = parsed.error;
        } else {
            const dupErr = validateMatchIds(parsed.matchIds);
            if (dupErr) {
                matchIdsError = dupErr;
            } else {
                matchIds = parsed.matchIds;
            }
        }
    } else if (matchIdsIdx !== -1) {
        matchIdsError = '--match-ids requires a comma-separated list of match IDs';
    }

    return { fullRecalculate, dryRun, noWrite, preview, isNoWrite, limit, matchIds, matchIdsError };
}

// eslint-disable-next-line complexity
function printPreview(result) {
    if (!result.previewEntries || result.previewEntries.length === 0) {
        console.log('\n📋 No preview entries produced.');
        return;
    }

    console.log('\n' + '═'.repeat(72));
    console.log('📋 NO-WRITE PREVIEW — FeatureSmelter extractor output summary');
    console.log('═'.repeat(72));
    console.log(`   Mode:           DRY-RUN / NO-WRITE`);
    console.log(`   Total checked:  ${result.total}`);
    console.log(`   Preview count:  ${result.preview}`);
    console.log(`   Success:        ${result.success}`);
    console.log(`   Failed:         ${result.failed}`);
    console.log(`   Skipped:        ${result.skipped}`);
    console.log(`   DB writes:      NONE (INSERT/UPDATE suppressed)`);
    if (result.matchIds) {
        console.log(`   --match-ids:    ${result.matchIds.join(', ')} (${result.matchIds.length} rows)`);
    }
    console.log('═'.repeat(72));

    for (const entry of result.previewEntries) {
        console.log(`\n┌─ match_id: ${entry.match_id}`);
        console.log(`├─ external_id: ${entry.external_id || '(null)'}`);
        console.log(`├─ data_version: ${entry.data_version || '(unknown)'}`);
        console.log(`├─ teams: ${entry.home_team || '?'} vs ${entry.away_team || '?'}`);
        console.log(`├─ has_raw_data: ${entry.has_raw_data}`);
        console.log(`├─ would_write: ${entry.would_write_l3_features}`);
        console.log(`├─ actual_db_write: ${entry.actual_db_write}`);

        if (entry.error) {
            console.log(`├─ ❌ ERROR: ${entry.error}`);
            continue;
        }

        console.log(`├─ extractors:`);
        for (const [name, info] of Object.entries(entry.extractors)) {
            const icon = info.empty ? '⚠️ EMPTY' : '✅ ';
            const reason = info.reason ? ` (${info.reason})` : '';
            const keyInfo = info.data_keys !== undefined
                ? `data_keys=${info.data_keys}/${info.keys}`
                : `keys=${info.keys}`;
            console.log(`│  ${icon} ${name}: ${keyInfo}${reason}`);
            // 2AU: show numeric Elo values when available
            if (name === 'elo_features' && typeof info.home_elo === 'number') {
                console.log(`│     home_elo=${info.home_elo}`);
                console.log(`│     away_elo=${info.away_elo}`);
                console.log(`│     elo_diff=${info.elo_diff}`);
                console.log(`│     _is_default=${info._is_default}`);
                if (info._source) console.log(`│     _source=${info._source}`);
                // 2BB: show would_change signal
                const wouldChange = info._is_default === false ? 'no (already real)' : 'yes (default → real)';
                console.log(`│     would_change=${wouldChange}`);
            }
        }
        console.log(`└─`);
    }
    console.log(`\n✅ NO-WRITE PREVIEW complete. l3_features was NOT modified.`);
}

async function main() {
    const args = parseArgs(process.argv);
    const { fullRecalculate, isNoWrite, limit, matchIds, matchIdsError } = args;

    // ── Validate --match-ids parsing errors ──────────────────────────────────
    if (matchIdsError) {
        console.error(`❌ Invalid --match-ids argument: ${matchIdsError}`);
        process.exit(1);
    }

    // ── --match-ids + --limit mutual exclusion ───────────────────────────────
    if (matchIds !== null && process.argv.includes('--limit')) {
        console.error('❌ --match-ids and --limit are mutually exclusive. Use --match-ids for exact selection.');
        process.exit(1);
    }

    // ── 2BB: --match-ids only allowed in dry-run/no-write mode ───────────────
    if (matchIds !== null && !isNoWrite) {
        console.error(
            '❌ --match-ids is currently allowed only in dry-run/no-write mode.\n' +
            '   Use --dry-run, --no-write, or --preview with --match-ids.\n' +
            '   Write mode with --match-ids is blocked until a future task explicitly authorizes it.'
        );
        process.exit(1);
    }

    if (isNoWrite) {
        console.log('🔒 NO-WRITE PREVIEW MODE');
        console.log('   DB writes: DISABLED');
        console.log('   INSERT/UPDATE: suppressed');
        if (matchIds) {
            console.log(`   Match IDs: ${matchIds.join(', ')} (${matchIds.length} rows)`);
        } else {
            console.log(`   Limit: ${limit}`);
        }
        console.log('');
    } else {
        assertDbWriteAllowed({
            script: 'smelt_all',
            tables: ['l3_features'],
            operations: ['INSERT', 'UPDATE'],
        });
        console.log('⚠️  WRITE MODE — will INSERT/UPDATE l3_features');
        console.log(`   Use --dry-run, --no-write, or --preview for safe preview.`);
        console.log('');
    }

    const smelter = new FeatureSmelter();

    try {
        await smelter.init();
        const runOpts = {
            fullRecalculate,
            limit,
            dryRun: isNoWrite,
            noWrite: isNoWrite,
            preview: isNoWrite,
        };
        if (matchIds !== null) {
            runOpts.matchIds = matchIds;
        }
        const result = await smelter.run(runOpts);

        if (isNoWrite && result.previewEntries) {
            printPreview(result);
        }
    } finally {
        await smelter.close();
    }
}

main().catch(err => {
    console.error('❌ 致命错误:', err.message);
    process.exit(1);
});
