'use strict';

/**
 * Preload script: sets guard env vars for test files that exercise DB write
 * paths guarded by assertDbWriteAllowed (PR #1587).  Env is scoped to the
 * Node.js process — no persistent effect.  Only activates when one of the
 * guarded test files appears in process.argv.
 */

const GUARDED_TEST_FILES = [
    'pageprops_v2_single_target_controlled_write.test.js',
    'remaining_seeded_pageprops_v2_controlled_write.test.js',
    'single_league_pageprops_v2_controlled_write_execute.test.js',
    'l2_guarded_reconciliation_write.test.js',
];

const needsEnv = process.argv.some(arg =>
    GUARDED_TEST_FILES.some(gf => arg.endsWith(gf)));
const needsRawMatchDataWriteEnv = process.argv.some(arg =>
    [
        'pageprops_v2_single_target_controlled_write.test.js',
        'remaining_seeded_pageprops_v2_controlled_write.test.js',
        'single_league_pageprops_v2_controlled_write_execute.test.js',
    ].some(gf => arg.endsWith(gf)));
const needsMatchesWriteEnv = process.argv.some(arg =>
    arg.endsWith('l2_guarded_reconciliation_write.test.js'));

if (needsEnv) {
    process.env.ALLOW_DB_WRITE = 'yes';
    process.env.FINAL_DB_WRITE_CONFIRMATION = 'yes';
    process.env.DRY_RUN = 'false';
    if (needsRawMatchDataWriteEnv) {
        process.env.ALLOW_RAW_MATCH_DATA_WRITE = 'yes';
    }
    if (needsMatchesWriteEnv) {
        process.env.ALLOW_MATCHES_WRITE = 'yes';
    }
}
