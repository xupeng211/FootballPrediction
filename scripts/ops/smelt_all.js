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
 *
 * @module scripts/ops/smelt_all
 * @version V176.1.0
 */

'use strict';

const { FeatureSmelter } = require('../../src/feature_engine/smelter/FeatureSmelter');

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

    return { fullRecalculate, dryRun, noWrite, preview, isNoWrite, limit };
}

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
    console.log('═'.repeat(72));

    for (const entry of result.previewEntries) {
        console.log(`\n┌─ match_id: ${entry.match_id}`);
        console.log(`├─ external_id: ${entry.external_id || '(null)'}`);
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
        }
        console.log(`└─`);
    }
    console.log(`\n✅ NO-WRITE PREVIEW complete. l3_features was NOT modified.`);
}

async function main() {
    const args = parseArgs(process.argv);
    const { fullRecalculate, isNoWrite, limit } = args;

    if (isNoWrite) {
        console.log('🔒 NO-WRITE PREVIEW MODE');
        console.log('   DB writes: DISABLED');
        console.log('   INSERT/UPDATE: suppressed');
        console.log(`   Limit: ${limit}`);
        console.log('');
    } else {
        console.log('⚠️  WRITE MODE — will INSERT/UPDATE l3_features');
        console.log(`   Use --dry-run, --no-write, or --preview for safe preview.`);
        console.log('');
    }

    const smelter = new FeatureSmelter();

    try {
        await smelter.init();
        const result = await smelter.run({
            fullRecalculate,
            limit,
            dryRun: isNoWrite,
            noWrite: isNoWrite,
            preview: isNoWrite,
        });

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
