// lifecycle: test-fixture
'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');
const path = require('node:path');

const {
    NEXT_PHASE,
    selectTarget,
    buildUrl,
    runPreflight,
    buildManifest,
    parseArgs,
} = require('../../scripts/ops/fotmob_ligue1_adg60_live_fetch_one_target_no_write');

const ROOT = path.resolve(__dirname, '../..');
const DRY_RUN_PATH = 'docs/_manifests/fotmob_ligue1_adg60_payload_acquisition_dry_run_no_write.json';

function loadDryRun() {
    return JSON.parse(require('node:fs').readFileSync(path.join(ROOT, DRY_RUN_PATH), 'utf8'));
}

test('ADG60 one-target no-write selects target_index=1 from dry-run matrix', () => {
    const dryRun = loadDryRun();
    const target = selectTarget(dryRun, 1);

    assert.equal(target.target_index, 1);
    assert.equal(target.target_match_id, '53_20252026_4830473');
    assert.equal(target.expected_home, 'Paris Saint-Germain');
    assert.equal(target.expected_away, 'Angers');
    assert.equal(target.competition, 'Ligue 1');
    assert.ok(target.corrected_hash_id);
    assert.ok(target.corrected_route_hash_pair);
    assert.equal(target.identity_status, 'accepted_suspension_resolved');
});

test('ADG60 one-target no-write refuses target_index > 32', () => {
    const dryRun = loadDryRun();
    assert.throws(() => selectTarget(dryRun, 33), /Target index 33 not found/);
});

test('ADG60 one-target no-write builds valid URL from route_hash_pair', () => {
    const dryRun = loadDryRun();
    const target = selectTarget(dryRun, 1);
    const urlInfo = buildUrl(target);

    assert.ok(urlInfo.url.startsWith('https://www.fotmob.com/matches/'));
    assert.ok(urlInfo.url.includes(urlInfo.routeHash));
    assert.ok(urlInfo.url.includes(urlInfo.matchId));
    assert.equal(urlInfo.routeHashPair, target.corrected_route_hash_pair);
});

test('ADG60 one-target no-write preflight passes for valid target with execute flag', () => {
    const dryRun = loadDryRun();
    const target = selectTarget(dryRun, 1);
    const urlInfo = buildUrl(target);
    const args = { executeLiveFetch: true, targetIndex: 1 };

    const preflight = runPreflight({ target, urlInfo, args });

    assert.equal(preflight.passed, true);
    assert.equal(preflight.selected_target_count, 1);
    assert.equal(preflight.target_count_total, 32);
    assert.equal(preflight.execute_live_fetch_requested, true);
});

test('ADG60 one-target no-write preflight safety checks confirm browser/db/write all blocked', () => {
    const dryRun = loadDryRun();
    const target = selectTarget(dryRun, 1);
    const urlInfo = buildUrl(target);
    const args = { executeLiveFetch: true, targetIndex: 1 };

    const preflight = runPreflight({ target, urlInfo, args });
    const safetyChecks = preflight.checks.filter(c =>
        c.name.startsWith('browser_') || c.name.startsWith('payload_') ||
        c.name.startsWith('db_') || c.name.startsWith('raw_') || c.name.startsWith('adg60_')
    );

    // All safety checks must be false (blocked)
    for (const c of safetyChecks) {
        assert.equal(c.pass, false, `${c.name} must be blocked (pass=false)`);
    }
    assert.ok(safetyChecks.length >= 6);
});

test('ADG60 one-target no-write manifest without fetch sets all execution flags false', () => {
    const dryRun = loadDryRun();
    const target = selectTarget(dryRun, 1);
    const urlInfo = buildUrl(target);
    const args = { executeLiveFetch: false, targetIndex: 1 };
    const preflight = runPreflight({ target, urlInfo, args });

    const manifest = buildManifest({ generatedAt: '2026-06-02T00:00:00.000Z', target, urlInfo, preflight, executionResult: null, args });

    assert.equal(manifest.live_fetch_performed, false);
    assert.equal(manifest.network_fetch_performed, false);
    assert.equal(manifest.browser_automation_performed, false);
    assert.equal(manifest.payload_saved, false);
    assert.equal(manifest.response_body_saved, false);
    assert.equal(manifest.acquisition_execution_performed, false);
    assert.equal(manifest.db_write_performed, false);
    assert.equal(manifest.raw_write_performed, false);
    assert.equal(manifest.raw_match_data_insert_performed, false);
    assert.equal(manifest.schema_migration_performed, false);
    assert.equal(manifest.adg60_write_performed, false);
    assert.equal(manifest.raw_write_ready_marked, false);
});

test('ADG60 one-target no-write manifest with successful fetch sets fetch=true but write flags false', () => {
    const dryRun = loadDryRun();
    const target = selectTarget(dryRun, 1);
    const urlInfo = buildUrl(target);
    const args = { executeLiveFetch: true, targetIndex: 1 };
    const preflight = runPreflight({ target, urlInfo, args });

    const mockExecution = {
        requestPerformed: true,
        requestCount: 1,
        httpStatus: 200,
        finalUrl: urlInfo.url,
        redirected: false,
        contentType: 'text/html; charset=utf-8',
        byteSize: 123456,
        bodySha256: 'abc123def456',
        payloadLike: true,
        minimalSchemaFlags: { hasNextDataMarker: true, looksLikeHtml: true },
        stopped: false,
        bodyPersisted: false,
        bodyLogged: false,
        bodyCommitted: false,
    };

    const manifest = buildManifest({ generatedAt: '2026-06-02T00:00:00.000Z', target, urlInfo, preflight, executionResult: mockExecution, args });

    assert.equal(manifest.live_fetch_performed, true);
    assert.equal(manifest.network_fetch_performed, true);
    assert.equal(manifest.acquisition_execution_performed, true);
    assert.equal(manifest.execution_result.httpStatus, 200);
    assert.equal(manifest.execution_result.byteSize, 123456);
    assert.equal(manifest.execution_result.bodySha256, 'abc123def456');
    assert.equal(manifest.execution_result.payloadLike, true);
    assert.equal(manifest.execution_result.bodyPersisted, false);
    assert.equal(manifest.execution_result.bodyLogged, false);
    assert.equal(manifest.execution_result.bodyCommitted, false);

    // Write flags must remain false
    assert.equal(manifest.db_write_performed, false);
    assert.equal(manifest.raw_write_performed, false);
    assert.equal(manifest.raw_match_data_insert_performed, false);
    assert.equal(manifest.adg60_write_performed, false);
    assert.equal(manifest.raw_write_ready_marked, false);
    assert.equal(manifest.browser_automation_performed, false);
    assert.equal(manifest.payload_saved, false);
});

test('ADG60 one-target no-write manifest body flags are always false', () => {
    const dryRun = loadDryRun();
    const target = selectTarget(dryRun, 1);
    const urlInfo = buildUrl(target);
    const args = { executeLiveFetch: true, targetIndex: 1 };
    const preflight = runPreflight({ target, urlInfo, args });

    const mockExecution = {
        requestPerformed: true,
        requestCount: 1,
        httpStatus: 200,
        byteSize: 50000,
        bodySha256: 'sha256hash',
        bodyPersisted: false,
        bodyLogged: false,
        bodyCommitted: false,
    };

    const manifest = buildManifest({ generatedAt: '2026-06-02T00:00:00.000Z', target, urlInfo, preflight, executionResult: mockExecution, args });

    assert.equal(manifest.payload_saved, false);
    assert.equal(manifest.response_body_saved, false);
    assert.equal(manifest.execution_result.bodyPersisted, false);
    assert.equal(manifest.execution_result.bodyLogged, false);
    assert.equal(manifest.execution_result.bodyCommitted, false);
});

test('ADG60 one-target no-write recommends review next phase', () => {
    const dryRun = loadDryRun();
    const target = selectTarget(dryRun, 1);
    const urlInfo = buildUrl(target);
    const args = { executeLiveFetch: false, targetIndex: 1 };
    const preflight = runPreflight({ target, urlInfo, args });

    const manifest = buildManifest({ generatedAt: '2026-06-02T00:00:00.000Z', target, urlInfo, preflight, executionResult: null, args });

    assert.equal(manifest.recommended_next_phase, NEXT_PHASE);
    assert.equal(manifest.recommended_next_phase, 'ADG60-PAYLOAD-ACQUISITION-LIVE-FETCH-ONE-TARGET-NO-WRITE-REVIEW');
    assert.ok(manifest.next_phase_boundary.includes('Review'));
    assert.ok(manifest.next_phase_boundary.includes('DB/raw/raw_match_data writes remain prohibited'));
});

test('ADG60 one-target no-write parseArgs defaults to no-execute and target-index=1', () => {
    process.argv = ['node', 'script.js'];
    const args = parseArgs();
    assert.equal(args.executeLiveFetch, false);
    assert.equal(args.targetIndex, 1);
});

test('ADG60 one-target no-write parseArgs enables execute with flag', () => {
    const originalArgv = process.argv;
    process.argv = ['node', 'script.js', '--execute-one-target-live-fetch', '--target-index', '5'];
    const args = parseArgs();
    process.argv = originalArgv;

    assert.equal(args.executeLiveFetch, true);
    assert.equal(args.targetIndex, 5);
});

test('ADG60 one-target no-write parseArgs rejects invalid target index', () => {
    const originalArgv = process.argv;
    process.argv = ['node', 'script.js', '--target-index', '99'];
    assert.throws(() => parseArgs(), /Invalid --target-index/);
    process.argv = originalArgv;
});
