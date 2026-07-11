'use strict';
/* eslint-disable max-lines -- L2V3AP audit stays explicit because the phase is governance-heavy. */

const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const Module = require('node:module');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/pageprops_v2_no_write_recapture_blocker_investigation.js');

function loadFreshModule() {
    delete require.cache[require.resolve(MODULE_PATH)];
    return require(MODULE_PATH);
}

const mod = loadFreshModule();

function syntheticManifest() {
    return {
        batch_id: 'fotmob-pageprops-v2-ligue1-2025-2026-profile-001',
        source: 'fotmob',
        route: 'html_hydration',
        raw_data_version: 'fotmob_pageprops_v2',
        hash_strategy: 'stable_pageprops_payload_v1',
        candidate_targets: [
            {
                match_id: '53_20252026_4830466',
                external_id: '4830466',
                home_team: 'Rennes',
                away_team: 'Marseille',
                match_date: '2025-08-15T18:45:00.000Z',
                kickoff_time: '2025-08-15T18:45:00.000Z',
                status: 'finished',
                baseline_hash: 'c0365494bedfad7f49c59db649dc52d45bd364e7991f518261085349bebd530b',
            },
        ],
        no_write_payload_recapture_execution_status: 'blocked_no_write',
        raw_write_execution_ready: false,
    };
}

function syntheticAoArtifact() {
    return {
        attempted_recapture_count: 1,
        blocked_recapture_count: 1,
        per_target_results: [
            {
                target_id: 'fotmob-pageprops-v2-ligue1-2025-2026-profile-001:53_20252026_4830466',
                match_id: '53_20252026_4830466',
                external_id: '4830466',
                observed_detail_external_id: '4830759',
                identity_match_status: 'mismatch',
                date_route_status: 'mismatch',
                date_compatibility_status: 'reverse_fixture_detected',
                page_url_base_match_status: 'match',
                team_date_status_match_status: 'team_date_status_mismatch',
                hash_validation_status: 'hash_mismatch',
                stable_pageprops_payload_v1_hash: 'e068f25fe9a9da863eafbb4fd2bbd84671fc74abea9edca3817a9c2c1704a683',
                blocker_list: [
                    'accepted_schedule_detail_mapping_required',
                    'date_or_route_mismatch',
                    'hash_mismatch_unexplained',
                    'identity_mismatch',
                    'page_url_base_alone_insufficient_for_acceptance',
                    'reverse_fixture_detected',
                    'team_date_status_mismatch',
                ],
            },
        ],
    };
}

function syntheticAaArtifact() {
    return {
        enriched_targets: [
            {
                match_id: '53_20252026_4830466',
                source_page_url: '/matches/marseille-vs-rennes/2t9n7h#4830466',
                source_page_url_base: '/matches/marseille-vs-rennes/2t9n7h',
                source_url_fragment_external_id: '4830466',
            },
        ],
    };
}

function syntheticAeArtifact() {
    return {
        review_entries: [
            {
                match_id: '53_20252026_4830466',
                source_page_url: '/matches/marseille-vs-rennes/2t9n7h#4830466',
                source_page_url_base: '/matches/marseille-vs-rennes/2t9n7h',
                source_url_fragment_external_id: '4830466',
                review_status: 'accepted',
            },
        ],
    };
}

function syntheticAgArtifact() {
    return {
        baseline_entries: [
            {
                match_id: '53_20252026_4830466',
                source_page_url: '/matches/marseille-vs-rennes/2t9n7h#4830466',
                source_page_url_base: '/matches/marseille-vs-rennes/2t9n7h',
                source_url_fragment_external_id: '4830466',
                baseline_acceptance_status: 'accepted_enriched_baseline_metadata',
            },
        ],
    };
}

function syntheticMArtifact() {
    return {
        known_mappings: [
            {
                schedule_external_id: '4830466',
                detail_external_id: '4830759',
                classification: 'reverse_fixture_detected',
                accepted_mapping: false,
                raw_write_blocked: true,
            },
        ],
    };
}

function syntheticNArtifact() {
    return {
        target_summaries: [
            {
                match_id: '53_20252026_4830466',
                schedule_external_id: '4830466',
                observed_detail_external_id: '4830759',
                page_url_base_match_status: 'match',
                team_pair_match_status: 'same_pair_reversed_home_away_order',
                date_rule_status: 'reverse_fixture_detected',
                accepted_mapping: false,
                raw_write_blocked: true,
                safe_error_summary:
                    'source-controlled review metadata indicates same pageUrl base, reversed teams, and large date gap; blocked as identity mismatch',
            },
        ],
    };
}

function syntheticOverrides() {
    return {
        manifest: syntheticManifest(),
        aoArtifact: syntheticAoArtifact(),
        l2v3aa: syntheticAaArtifact(),
        l2v3ac: {},
        l2v3ae: syntheticAeArtifact(),
        l2v3ag: syntheticAgArtifact(),
        l2v3m: syntheticMArtifact(),
        l2v3n: syntheticNArtifact(),
        aoHelperSource: `
            function resolveFetchResultForTarget(target) {
                const requestUrl = buildFotMobMatchUrl(target.external_id);
                return fetchHtml(requestUrl);
            }
        `,
        aoHelperTestSource:
            'source_page_url: `/match/${item.external_id}#${item.external_id}`, source_page_url_base: `/match/${item.external_id}`',
    };
}

test('L2V3AP records blocker investigation semantics without network or write readiness', () => {
    const result = mod.runNoWriteRecaptureBlockerInvestigation({ writeFiles: false }, syntheticOverrides());
    const artifact = result.artifact;
    const manifest = result.updated_manifest;

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3AP');
    assert.equal(artifact.investigation_status, 'completed_no_write_payload_recapture_blocker_investigation');
    assert.equal(artifact.live_fetch_performed, false);
    assert.equal(artifact.detail_fetch_performed, false);
    assert.equal(artifact.network_request_performed, false);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_match_data_insert_performed, false);
    assert.equal(artifact.raw_write_execution_performed, false);
    assert.equal(artifact.raw_write_runner_write_mode_used, false);
    assert.equal(artifact.payload_recapture_retry_ready, false);
    assert.equal(artifact.raw_write_execution_ready, false);
    assert.equal(manifest.phase_5_21_l2v3ap_investigation_status, artifact.investigation_status);
    assert.equal(manifest.payload_recapture_retry_ready, false);
    assert.equal(manifest.raw_write_execution_ready, false);
});

test('L2V3AP preserves identity mismatch, reverse fixture, hash mismatch blocking, and contradiction signals', () => {
    const result = mod.runNoWriteRecaptureBlockerInvestigation({ writeFiles: false }, syntheticOverrides());
    const artifact = result.artifact;

    assert.equal(artifact.blocker_target_match_id, '53_20252026_4830466');
    assert.equal(artifact.requested_external_id, '4830466');
    assert.equal(artifact.observed_detail_external_id, '4830759');
    assert.equal(artifact.identity_mismatch_confirmed, true);
    assert.equal(artifact.reverse_fixture_confirmed, true);
    assert.equal(artifact.date_route_mismatch_confirmed, true);
    assert.equal(artifact.hash_mismatch_classification, 'secondary_to_identity_mismatch_reverse_fixture');
    assert.equal(artifact.hash_mismatch_acceptance_allowed, false);
    assert.equal(artifact.page_url_base_match_status, 'match');
    assert.equal(artifact.page_url_base_identity_evidence_sufficient, false);
    assert.equal(artifact.accepted_mapping_contradiction, true);
    assert.equal(artifact.baseline_acceptance_contradiction, true);
    assert.equal(artifact.runner_input_contract_issue, true);
    assert.equal(artifact.source_url_route_issue, true);
    assert.match(artifact.likely_root_cause, /accepted mapping and baseline accepted schedule-side/i);
    assert.equal(
        artifact.recommended_next_step,
        'Phase 5.21L2V3AQ: accepted mapping and baseline contradiction review planning'
    );
});

test('L2V3AP surfaces runner input contract planning when contradictions are absent but route contract is still wrong', () => {
    const overrides = syntheticOverrides();
    overrides.l2v3ae = {
        review_entries: [
            {
                match_id: '53_20252026_4830466',
                source_page_url: '/matches/marseille-vs-rennes/2t9n7h#4830466',
                source_page_url_base: '/matches/marseille-vs-rennes/2t9n7h',
                source_url_fragment_external_id: '4830466',
                review_status: 'blocked',
            },
        ],
    };
    overrides.l2v3ag = {
        baseline_entries: [
            {
                match_id: '53_20252026_4830466',
                source_page_url: '/matches/marseille-vs-rennes/2t9n7h#4830466',
                source_page_url_base: '/matches/marseille-vs-rennes/2t9n7h',
                source_url_fragment_external_id: '4830466',
                baseline_acceptance_status: 'blocked',
            },
        ],
    };

    const artifact = mod.runNoWriteRecaptureBlockerInvestigation({ writeFiles: false }, overrides).artifact;

    assert.equal(artifact.accepted_mapping_contradiction, false);
    assert.equal(artifact.baseline_acceptance_contradiction, false);
    assert.equal(artifact.runner_input_contract_issue, true);
    assert.equal(artifact.source_url_route_issue, true);
    assert.match(artifact.likely_root_cause, /recapture runner rebuilt \/match\/\{schedule_external_id\}/i);
    assert.equal(
        artifact.recommended_next_step,
        'Phase 5.21L2V3AQ: recapture runner identity input contract fix planning'
    );
});

test('L2V3AP falls back to continued investigation when neither contradictions nor runner contract issue can be confirmed', () => {
    const overrides = syntheticOverrides();
    overrides.l2v3aa = {
        enriched_targets: [
            {
                match_id: '53_20252026_4830466',
                source_page_url: '/match/4830466#4830466',
                source_page_url_base: '/match/4830466',
                source_url_fragment_external_id: '4830466',
            },
        ],
    };
    overrides.l2v3ae = {
        review_entries: [
            {
                match_id: '53_20252026_4830466',
                source_page_url: '/match/4830466#4830466',
                source_page_url_base: '/match/4830466',
                source_url_fragment_external_id: '4830466',
                review_status: 'blocked',
            },
        ],
    };
    overrides.l2v3ag = {
        baseline_entries: [
            {
                match_id: '53_20252026_4830466',
                source_page_url: '/match/4830466#4830466',
                source_page_url_base: '/match/4830466',
                source_url_fragment_external_id: '4830466',
                baseline_acceptance_status: 'blocked',
            },
        ],
    };

    const artifact = mod.runNoWriteRecaptureBlockerInvestigation({ writeFiles: false }, overrides).artifact;

    assert.equal(artifact.accepted_mapping_contradiction, false);
    assert.equal(artifact.baseline_acceptance_contradiction, false);
    assert.equal(artifact.runner_input_contract_issue, false);
    assert.equal(artifact.source_url_route_issue, false);
    assert.match(artifact.likely_root_cause, /blocker remains unresolved from source-controlled artifacts alone/i);
    assert.equal(
        artifact.recommended_next_step,
        'Phase 5.21L2V3AQ: continued no-write recapture blocker investigation'
    );
});

test('L2V3AP report, artifact, and manifest do not contain full raw payload markers', () => {
    const result = mod.runNoWriteRecaptureBlockerInvestigation({ writeFiles: false }, syntheticOverrides());
    const texts = [JSON.stringify(result.artifact), result.report, JSON.stringify(result.updated_manifest)];

    for (const text of texts) {
        assert.equal(text.includes('"raw_data":'), false);
        assert.equal(text.includes('"pageProps":'), false);
        assert.equal(text.includes('__NEXT_DATA__'), false);
        assert.equal(text.includes('<!DOCTYPE'), false);
        assert.equal(text.includes('"source_body":'), false);
    }
});

test('L2V3AP can write artifact, report, and manifest through injected writers', () => {
    const writes = [];
    const result = mod.runNoWriteRecaptureBlockerInvestigation(
        {},
        {
            ...syntheticOverrides(),
            writeJsonFile: (targetPath, value) => writes.push(['json', targetPath, value]),
            writeTextFile: (targetPath, value) => writes.push(['text', targetPath, value]),
        }
    );

    assert.equal(result.ok, true);
    assert.equal(writes.length, 3);
    assert.deepEqual(
        writes.map(([kind, targetPath]) => [kind, targetPath]),
        [
            ['json', mod.ARTIFACT_OUTPUT_PATH],
            ['text', mod.REPORT_OUTPUT_PATH],
            ['json', mod.PROPOSAL_MANIFEST_PATH],
        ]
    );
});

test('L2V3AP URL helpers reject invalid IDs and preserve fallback path parsing', () => {
    assert.throws(() => mod.buildFotMobMatchUrl('48x30466'), /INVALID_EXTERNAL_ID/);
    assert.equal(mod.urlPath('/matches/marseille-vs-rennes/2t9n7h#4830466'), '/matches/marseille-vs-rennes/2t9n7h');
    assert.equal(mod.urlPath('http://%zz?from=bad#fragment'), 'http://%zz');
});

test('L2V3AP leaves unresolved identity evidence empty instead of inventing detail metadata', () => {
    const overrides = syntheticOverrides();
    overrides.aoArtifact = {
        attempted_recapture_count: 1,
        blocked_recapture_count: 1,
        per_target_results: [
            {
                target_id: 'fotmob-pageprops-v2-ligue1-2025-2026-profile-001:53_20252026_4830466',
                match_id: '53_20252026_4830466',
                external_id: '4830466',
                observed_detail_external_id: '',
                identity_match_status: 'mismatch',
                date_route_status: '',
                date_compatibility_status: '',
                page_url_base_match_status: '',
                team_date_status_match_status: '',
                hash_validation_status: '',
                stable_pageprops_payload_v1_hash: '',
                blocker_list: ['identity_mismatch'],
            },
        ],
    };
    overrides.l2v3aa = {
        enriched_targets: [
            {
                match_id: '53_20252026_4830466',
            },
        ],
    };
    overrides.l2v3ae = {
        review_entries: [
            {
                match_id: '53_20252026_4830466',
                review_status: 'blocked',
            },
        ],
    };
    overrides.l2v3ag = {
        baseline_entries: [
            {
                match_id: '53_20252026_4830466',
                baseline_acceptance_status: 'blocked',
            },
        ],
    };
    overrides.l2v3m = {};
    overrides.l2v3n = {};

    const artifact = mod.runNoWriteRecaptureBlockerInvestigation({ writeFiles: false }, overrides).artifact;

    assert.equal(artifact.observed_detail_external_id, null);
    assert.equal(artifact.accepted_source_page_url, null);
    assert.equal(artifact.accepted_source_page_url_base, null);
    assert.equal(artifact.source_url_fragment_external_id, null);
    assert.equal(artifact.page_url_base_match_status, null);
    assert.equal(artifact.team_date_status_match_status, null);
    assert.equal(artifact.date_compatibility_status, null);
    assert.equal(artifact.hash_validation_status, 'not_evaluated');
    assert.equal(
        artifact.safe_error_summary,
        'local artifact investigation only; reverse fixture blocker remains unresolved'
    );
});

test('L2V3AP loadContext can read repository artifacts through default file helpers', () => {
    const context = mod.loadContext();

    assert.equal(context.blockerTargetCount, 1);
    assert.equal(context.identityMismatchConfirmed, true);
    assert.equal(context.reverseFixtureConfirmed, true);
    assert.equal(context.dateRouteMismatchConfirmed, true);
    assert.equal(context.proposalTarget.match_id, '53_20252026_4830466');
    assert.equal(context.l2v3mKnownMapping.detail_external_id, '4830759');
});

test('L2V3AP internal file writers can be exercised without persisting to disk', () => {
    const writes = [];
    const originalWriteFileSync = fs.writeFileSync;

    fs.writeFileSync = function patchedWriteFileSync(filePath, value, encoding) {
        writes.push([String(filePath), String(value), encoding]);
    };

    try {
        const result = mod.runNoWriteRecaptureBlockerInvestigation();
        assert.equal(result.ok, true);
        assert.equal(writes.length, 3);
        assert.equal(writes[0][0].endsWith(mod.ARTIFACT_OUTPUT_PATH), true);
        assert.equal(writes[1][0].endsWith(mod.REPORT_OUTPUT_PATH), true);
        assert.equal(writes[2][0].endsWith(mod.PROPOSAL_MANIFEST_PATH), true);
    } finally {
        fs.writeFileSync = originalWriteFileSync;
    }
});

test('L2V3AP runCli prints safe blocker investigation summary', async () => {
    let output = '';
    const writes = [];
    const originalWriteFileSync = fs.writeFileSync;
    const originalWrite = process.stdout.write;
    process.stdout.write = text => {
        output += text;
        return true;
    };
    fs.writeFileSync = (...args) => {
        writes.push(args);
    };

    try {
        await mod.runCli();
    } finally {
        process.stdout.write = originalWrite;
        fs.writeFileSync = originalWriteFileSync;
    }

    assert.equal(writes.length, 3);
    const parsed = JSON.parse(output);
    assert.equal(parsed.ok, true);
    assert.equal(parsed.phase, 'Phase 5.21L2V3AP');
    assert.equal(parsed.requested_external_id, '4830466');
    assert.equal(parsed.observed_detail_external_id, '4830759');
    assert.equal(parsed.raw_write_execution_ready, false);
});

test('L2V3AP CLI main entrypoint catch path reports failures safely', () => {
    const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'l2v3ap-cli-catch-'));
    const tempModulePath = path.join(tempDir, path.basename(MODULE_PATH));
    const originalSource = fs.readFileSync(MODULE_PATH, 'utf8');
    const forcedFailureSource = originalSource.replace(
        'async function runCli() {',
        "async function runCli() {\n    throw new Error('FORCED_CLI_FAILURE');"
    );

    fs.writeFileSync(tempModulePath, forcedFailureSource, 'utf8');

    try {
        const result = spawnSync(process.execPath, [tempModulePath], {
            cwd: PROJECT_ROOT,
            encoding: 'utf8',
        });

        assert.equal(result.status, 1);
        assert.match(result.stderr, /FORCED_CLI_FAILURE/);
    } finally {
        fs.rmSync(tempDir, { recursive: true, force: true });
    }
});

test('module load avoids DB, network, browser, proxy, and child process imports', () => {
    const seen = [];
    const originalLoad = Module._load;
    Module._load = function wrapped(request, parent, isMain) {
        seen.push(request);
        return originalLoad.call(this, request, parent, isMain);
    };
    try {
        delete require.cache[require.resolve(MODULE_PATH)];
        require(MODULE_PATH);
    } finally {
        Module._load = originalLoad;
        delete require.cache[require.resolve(MODULE_PATH)];
    }

    const joined = seen.join('\n');
    assert.doesNotMatch(joined, /\bpg\b|psql|postgres|child_process|playwright|puppeteer|axios|undici/i);
    assert.doesNotMatch(joined, /BrowserProvider|proxy/i);
});

test('repository L2V3AP artifacts preserve blocker investigation semantics', () => {
    const artifact = JSON.parse(
        fs.readFileSync(
            path.join(
                PROJECT_ROOT,
                'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.no_write_payload_recapture_blocker_investigation.phase521l2v3ap.json'
            ),
            'utf8'
        )
    );
    const manifest = JSON.parse(
        fs.readFileSync(
            path.join(PROJECT_ROOT, 'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json'),
            'utf8'
        )
    );
    const report = fs.readFileSync(
        path.join(PROJECT_ROOT, 'docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AP.md'),
        'utf8'
    );

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3AP');
    assert.equal(artifact.live_fetch_performed, false);
    assert.equal(artifact.detail_fetch_performed, false);
    assert.equal(artifact.network_request_performed, false);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_match_data_insert_performed, false);
    assert.equal(artifact.raw_write_execution_ready, false);
    assert.equal(artifact.payload_recapture_retry_ready, false);
    assert.equal(artifact.identity_mismatch_confirmed, true);
    assert.equal(artifact.reverse_fixture_confirmed, true);
    assert.equal(artifact.page_url_base_identity_evidence_sufficient, false);
    assert.ok(
        [
            'Phase 5.21L2V3AQ: accepted mapping and baseline contradiction review planning',
            'Phase 5.21L2V3AQ: recapture runner identity input contract fix planning',
            'Phase 5.21L2V3AQ: continued no-write recapture blocker investigation',
        ].includes(artifact.recommended_next_step)
    );

    assert.equal(
        manifest.phase_5_21_l2v3ap_investigation_status,
        'completed_no_write_payload_recapture_blocker_investigation'
    );
    assert.equal(manifest.payload_recapture_retry_ready, false);
    assert.equal(manifest.raw_write_execution_ready, false);
    assert.match(report, /requested_external_id=4830466/);
    assert.match(report, /observed_detail_external_id=4830759/);
    assert.match(report, /accepted_mapping_contradiction=true/);
    assert.match(report, /baseline_acceptance_contradiction=true/);
});
