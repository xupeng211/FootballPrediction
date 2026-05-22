'use strict';
/* eslint-disable max-lines -- L2V3AF safety contract is audited together. */

const assert = require('node:assert/strict');
const fs = require('node:fs');
const Module = require('node:module');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/pageprops_v2_baseline_acceptance_plan.js');

function loadFreshModule() {
    delete require.cache[require.resolve(MODULE_PATH)];
    return require(MODULE_PATH);
}

const mod = loadFreshModule();

function readJson(repoPath) {
    return JSON.parse(fs.readFileSync(path.join(PROJECT_ROOT, repoPath), 'utf8'));
}

function readText(repoPath) {
    return fs.readFileSync(path.join(PROJECT_ROOT, repoPath), 'utf8');
}

function acceptedEntry(index, overrides = {}) {
    const externalId = String(9300001 + index);
    return {
        target_id: `fotmob-pageprops-v2-ligue1-2025-2026-profile-001:53_20252026_${externalId}`,
        match_id: `53_20252026_${externalId}`,
        schedule_external_id: externalId,
        source_page_url: `/matches/home-${index}-away-${index}/route-${index}#${externalId}`,
        source_page_url_base: `/matches/home-${index}-away-${index}/route-${index}`,
        source_url_fragment_external_id: externalId,
        schedule_date: '2025-08-15T18:45:00.000Z',
        schedule_home_team: `Home ${index}`,
        schedule_away_team: `Away ${index}`,
        source_inventory_record_key: `l1_api_data_leagues:overview.leagueOverviewMatches.${index}:${externalId}`,
        review_status: 'accepted',
        review_result: 'accepted_identity_mapping',
        acceptance_status: 'accepted_identity_mapping',
        accepted_by: 'codex_test_reviewer',
        accepted_at: '2026-05-22T10:30:00Z',
        acceptance_blockers: [],
        acceptance_evidence_summary: {
            l2v3ac_verification_passed: true,
            source_url_evidence_complete: true,
            raw_write_runner_remains_blocked: true,
            human_review_satisfied: true,
        },
        accepted_mapping_does_not_accept_baseline: true,
        accepted_mapping_does_not_authorize_raw_write: true,
        raw_write_eligible_after_acceptance: false,
        ...overrides,
    };
}

function verificationResult(index, overrides = {}) {
    const entry = acceptedEntry(index);
    return {
        target_id: entry.target_id,
        match_id: entry.match_id,
        schedule_external_id: entry.schedule_external_id,
        source_url_fragment_external_id: entry.source_url_fragment_external_id,
        verification_status: 'verified',
        failure_reasons: [],
        ...overrides,
    };
}

function enrichedTarget(index, overrides = {}) {
    const entry = acceptedEntry(index);
    return {
        target_id: entry.target_id,
        match_id: entry.match_id,
        external_id: entry.schedule_external_id,
        schedule_external_id: entry.schedule_external_id,
        source_page_url: entry.source_page_url,
        source_page_url_base: entry.source_page_url_base,
        source_url_fragment_external_id: entry.source_url_fragment_external_id,
        schedule_date: entry.schedule_date,
        schedule_home_team: entry.schedule_home_team,
        schedule_away_team: entry.schedule_away_team,
        source_inventory_record_key: entry.source_inventory_record_key,
        regeneration_status: 'regenerated_no_write',
        regeneration_blockers: [],
        raw_write_ready_for_execution: false,
        ...overrides,
    };
}

function sourceRecord(index, overrides = {}) {
    const entry = acceptedEntry(index);
    return {
        target_id: entry.target_id,
        match_id: entry.match_id,
        external_id: entry.schedule_external_id,
        source_page_url: entry.source_page_url,
        source_page_url_base: entry.source_page_url_base,
        source_url_fragment_external_id: entry.source_url_fragment_external_id,
        schedule_external_id: entry.schedule_external_id,
        schedule_date: entry.schedule_date,
        schedule_home_team: entry.schedule_home_team,
        schedule_away_team: entry.schedule_away_team,
        source_inventory_record_key: entry.source_inventory_record_key,
        ...overrides,
    };
}

function manifest(overrides = {}) {
    return {
        batch_id: 'fotmob-pageprops-v2-ligue1-2025-2026-profile-001',
        next_required_step: 'baseline_acceptance_planning',
        recommended_next_step: 'Phase 5.21L2V3AF: baseline acceptance planning',
        phase_5_21_l2v3ae_accepted_mapping_count: 50,
        baseline_acceptance_performed: false,
        raw_write_retry_performed: false,
        raw_write_ready_for_execution: false,
        requires_separate_baseline_acceptance: true,
        requires_separate_final_db_write_authorization: true,
        hash_drift_review_status: 'completed_no_write',
        hash_drift_classification: 'partial_systemic_stable_content_drift',
        hash_drift_baseline_refresh_needed: true,
        hash_gate_status: 'blocked',
        ...overrides,
    };
}

function l2v3aeArtifact(overrides = {}) {
    return {
        proposal_phase: 'Phase 5.21L2V3AE',
        phase_name: 'identity_mapping_acceptance_review_execution',
        acceptance_review_execution_performed: true,
        accepted_mapping_count: 50,
        blocked_mapping_count: 0,
        human_review_required: true,
        human_review_satisfied: true,
        accepted_by: 'codex_test_reviewer',
        accepted_at: '2026-05-22T10:30:00Z',
        baseline_acceptance_performed: false,
        raw_write_retry_performed: false,
        raw_write_ready_for_execution: false,
        requires_separate_baseline_acceptance: true,
        requires_separate_final_db_write_authorization: true,
        review_entries: Array.from({ length: 50 }, (_, index) => acceptedEntry(index)),
        ...overrides,
    };
}

function l2v3acArtifact(overrides = {}) {
    return {
        proposal_phase: 'Phase 5.21L2V3AC',
        verification_status: 'passed_no_write_source_controlled',
        verified_target_count: 50,
        failed_target_count: 0,
        raw_write_runner_blocked: true,
        raw_write_ready_for_execution: false,
        verification_analysis: {
            target_results: Array.from({ length: 50 }, (_, index) => verificationResult(index)),
        },
        ...overrides,
    };
}

function l2v3aaArtifact(overrides = {}) {
    return {
        proposal_phase: 'Phase 5.21L2V3AA',
        regenerated_target_count: 50,
        raw_write_ready_for_execution: false,
        enriched_targets: Array.from({ length: 50 }, (_, index) => enrichedTarget(index)),
        ...overrides,
    };
}

function l2v3yArtifact(overrides = {}) {
    return {
        proposal_phase: 'Phase 5.21L2V3Y',
        candidate_scope_count: 50,
        raw_write_ready_for_execution: false,
        source_inventory_metadata_records: Array.from({ length: 50 }, (_, index) => sourceRecord(index)),
        ...overrides,
    };
}

function runSynthetic(overrides = {}) {
    return mod.runBaselineAcceptancePlanning({
        manifest: manifest(overrides.manifest || {}),
        l2v3aeArtifact: l2v3aeArtifact(overrides.l2v3aeArtifact || {}),
        l2v3acArtifact: l2v3acArtifact(overrides.l2v3acArtifact || {}),
        l2v3aaArtifact: l2v3aaArtifact(overrides.l2v3aaArtifact || {}),
        l2v3yArtifact: l2v3yArtifact(overrides.l2v3yArtifact || {}),
        l2v3cArtifact: { proposal_phase: 'Phase 5.21L2V3C' },
        l2v3mArtifact: { proposal_phase: 'Phase 5.21L2V3M' },
        l2v3nArtifact: { proposal_phase: 'Phase 5.21L2V3N' },
        writeFiles: false,
    });
}

function installImportGuard(t) {
    const originalLoad = Module._load;
    Module._load = function patchedLoad(request, parent, isMain) {
        if (
            /pg|http|https|playwright|puppeteer|ProductionHarvester|odds_harvest_pipeline|child_process/i.test(request)
        ) {
            throw new Error(`blocked import: ${request}`);
        }
        return originalLoad.call(this, request, parent, isMain);
    };
    t.after(() => {
        Module._load = originalLoad;
    });
}

test('L2V3AF is baseline acceptance planning-only and does not execute baseline acceptance', () => {
    const result = runSynthetic();
    const artifact = result.artifact;
    const updatedManifest = result.updated_manifest;

    assert.equal(result.ok, true);
    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3AF');
    assert.equal(artifact.phase_name, 'baseline_acceptance_planning');
    assert.equal(artifact.planning_only, true);
    assert.equal(artifact.baseline_acceptance_execution_performed, false);
    assert.equal(artifact.baseline_acceptance_performed, false);
    assert.equal(artifact.live_fetch_performed, false);
    assert.equal(artifact.detail_fetch_performed, false);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_match_data_insert_performed, false);
    assert.equal(artifact.matches_write_performed, false);
    assert.equal(artifact.matches_external_id_modified, false);
    assert.equal(artifact.identity_mapping_accepted_count, 50);
    assert.equal(artifact.baseline_review_candidate_count, 50);
    assert.equal(artifact.baseline_review_ready_count, 50);
    assert.equal(artifact.baseline_review_blocked_count, 0);
    assert.equal(updatedManifest.raw_write_ready_for_execution, false);
});

test('identity mapping accepted and baseline review ready do not imply baseline accepted or raw-write authorization', () => {
    const artifact = runSynthetic().artifact;
    const firstEntry = artifact.baseline_review_entries[0];

    assert.equal(artifact.baseline_accepted_count, 0);
    assert.equal(artifact.raw_write_authorization_performed, false);
    assert.equal(artifact.raw_write_retry_performed, false);
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(artifact.requires_separate_baseline_acceptance_execution, true);
    assert.equal(artifact.requires_separate_final_db_write_authorization, true);
    assert.equal(artifact.safety_contract.identity_mapping_accepted_does_not_imply_baseline_accepted, true);
    assert.equal(artifact.safety_contract.baseline_review_ready_does_not_imply_baseline_accepted, true);
    assert.equal(firstEntry.baseline_review_status, 'baseline_review_ready');
    assert.equal(firstEntry.baseline_acceptance_status, 'not_accepted_planning_only');
    assert.equal(firstEntry.baseline_accepted, false);
    assert.equal(firstEntry.raw_write_eligible_after_baseline_planning, false);
});

test('baseline acceptance subject excludes raw pageProps payloads, old drift hashes, baseline overwrite, and raw write', () => {
    const subject = runSynthetic().artifact.baseline_acceptance_subject;

    assert.equal(subject.accepts_enriched_source_side_identity_and_baseline_metadata, true);
    assert.equal(subject.does_not_accept_raw_pageprops_payload, true);
    assert.equal(subject.does_not_accept_old_drift_baseline_hash, true);
    assert.equal(subject.does_not_overwrite_existing_baseline_hash, true);
    assert.equal(subject.does_not_execute_raw_write, true);
});

test('criteria blockers prevent baseline review readiness without changing raw-write guards', () => {
    const duplicate = acceptedEntry(0);
    const entries = Array.from({ length: 50 }, (_, index) =>
        acceptedEntry(
            index,
            index === 1
                ? { source_inventory_record_key: duplicate.source_inventory_record_key }
                : index === 2
                  ? { source_url_fragment_external_id: 'mismatch' }
                  : index === 3
                    ? { acceptance_status: 'not_accepted' }
                    : {}
        )
    );
    const artifact = runSynthetic({ l2v3aeArtifact: { review_entries: entries } }).artifact;
    const blockers = artifact.baseline_review_entries.flatMap(entry => entry.baseline_acceptance_blockers);

    assert.equal(artifact.baseline_review_ready_count < 50, true);
    assert.equal(artifact.baseline_acceptance_performed, false);
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(blockers.includes('duplicate_source_key'), true);
    assert.equal(blockers.includes('fragment_schedule_mismatch'), true);
    assert.equal(blockers.includes('identity_mapping_not_accepted'), true);
});

test('input validation fails closed on missing acceptance, unsafe writes, and invalid upstream state', () => {
    const alreadyPlanned = mod.validateInputs(
        manifest({
            phase_5_21_l2v3af_planning_status: 'completed_baseline_acceptance_planning',
            next_required_step: 'baseline_acceptance_execution',
        }),
        l2v3aeArtifact(),
        l2v3acArtifact(),
        l2v3aaArtifact(),
        l2v3yArtifact()
    );
    assert.equal(alreadyPlanned.ok, true);

    const validation = mod.validateInputs(
        manifest({
            next_required_step: 'raw_write_retry',
            phase_5_21_l2v3ae_accepted_mapping_count: 49,
            baseline_acceptance_performed: true,
            raw_write_ready_for_execution: true,
        }),
        l2v3aeArtifact({
            proposal_phase: 'Phase 5.21L2V3AF',
            phase_name: 'baseline_acceptance_planning',
            acceptance_review_execution_performed: false,
            accepted_mapping_count: 49,
            blocked_mapping_count: 1,
            human_review_satisfied: false,
            accepted_by: '',
            db_write_performed: true,
        }),
        l2v3acArtifact({
            proposal_phase: 'Phase 5.21L2V3AB',
            verification_status: 'failed',
            verified_target_count: 49,
            failed_target_count: 1,
            raw_write_runner_blocked: false,
        }),
        l2v3aaArtifact({
            regenerated_target_count: 49,
            raw_write_retry_performed: true,
        }),
        l2v3yArtifact({
            candidate_scope_count: 49,
            raw_match_data_insert_performed: true,
        })
    );
    const errors = validation.errors.join('\n');

    assert.equal(validation.ok, false);
    assert.match(errors, /manifest next_required_step/);
    assert.match(errors, /phase_5_21_l2v3ae_accepted_mapping_count must be 50/);
    assert.match(errors, /L2V3AE artifact is required/);
    assert.match(errors, /L2V3AC verification_status/);
    assert.match(errors, /L2V3AA regenerated_target_count must be 50/);
    assert.match(errors, /L2V3Y candidate_scope_count must be 50/);
    assert.match(errors, /raw-write, or raw-ready state/);
});

test('helper refuses baseline execution, DB write, live/detail fetch, raw write, final authorization, and payload flags', () => {
    const parsed = mod.parseArgs([
        '--allow-db-write=yes',
        '--allow-network=yes',
        '--allow-live-fetch=yes',
        '--allow-detail-fetch=yes',
        '--allow-raw-match-data-write=yes',
        '--allow-matches-write=yes',
        '--allow-matches-external-id-write=yes',
        '--execute-baseline-acceptance=yes',
        '--accept-baseline=yes',
        '--allow-raw-write-retry=yes',
        '--execute-raw-write=yes',
        '--authorize-final-db-write=yes',
        '--print-full-pageprops=yes',
    ]);
    const validation = mod.validateCliOptions(parsed);

    assert.equal(validation.ok, false);
    assert.match(validation.errors.join('\n'), /allow-db-write=yes is blocked/);
    assert.match(validation.errors.join('\n'), /allow-live-fetch=yes is blocked/);
    assert.match(validation.errors.join('\n'), /allow-detail-fetch=yes is blocked/);
    assert.match(validation.errors.join('\n'), /execute-baseline-acceptance=yes is blocked/);
    assert.match(validation.errors.join('\n'), /accept-baseline=yes is blocked/);
    assert.match(validation.errors.join('\n'), /allow-raw-write-retry=yes is blocked/);
    assert.match(validation.errors.join('\n'), /authorize-final-db-write=yes is blocked/);
    assert.match(validation.errors.join('\n'), /print-full-pageprops=yes is blocked/);
});

test('argument parsing, continuation outcome, and blocked outcome stay explicit', () => {
    const parsed = mod.parseArgs(['--write_files', 'off', '--allow-network', '0', 'positional']);
    assert.equal(parsed.writeFiles, false);
    assert.equal(parsed.allowNetwork, false);
    assert.deepEqual(parsed.unknown, ['positional']);
    assert.match(mod.validateCliOptions(parsed).errors.join('\n'), /unknown arguments: positional/);

    const continued = mod.buildArtifact({
        loaded: {},
        plan: {
            identity_mapping_accepted_count: 49,
            baseline_review_candidate_count: 49,
            baseline_review_ready_count: 49,
            baseline_review_blocked_count: 0,
            baseline_review_blocker_count: 0,
            baseline_review_entries: [],
            known_prior_hash_drift_context: {},
        },
    });
    assert.equal(continued.recommended_next_step, 'Phase 5.21L2V3AG: continued baseline acceptance planning');

    const blocked = mod.buildArtifact({
        loaded: {},
        plan: {
            identity_mapping_accepted_count: 50,
            baseline_review_candidate_count: 50,
            baseline_review_ready_count: 49,
            baseline_review_blocked_count: 1,
            baseline_review_blocker_count: 1,
            baseline_review_entries: [],
            known_prior_hash_drift_context: {},
        },
    });
    assert.equal(blocked.recommended_next_step, 'Phase 5.21L2V3AG: baseline acceptance blocker investigation');
});

test('helper does not import network, DB, browser, proxy, harvest, odds, or child process modules on load', t => {
    installImportGuard(t);
    const loaded = loadFreshModule();
    assert.equal(typeof loaded.runBaselineAcceptancePlanning, 'function');
});

test('outputs avoid full raw data, pageProps, source body, and HTML payloads', () => {
    const result = runSynthetic();
    for (const text of [JSON.stringify(result.artifact), result.report, JSON.stringify(result.updated_manifest)]) {
        assert.equal(text.includes('"raw_data":'), false);
        assert.equal(text.includes('"pageProps":'), false);
        assert.equal(text.includes('__NEXT_DATA__'), false);
        assert.equal(text.includes('<!DOCTYPE'), false);
        assert.equal(text.includes('"source_body":'), false);
        assert.equal(text.includes('"full_json":'), false);
    }
});

test('runBaselineAcceptancePlanning can write planning outputs to explicit temp paths', () => {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'l2v3af-baseline-acceptance-plan-'));
    const artifactPath = path.join(tmpDir, 'artifact.json');
    const reportPath = path.join(tmpDir, 'report.md');
    const manifestPath = path.join(tmpDir, 'manifest.json');

    try {
        const result = mod.runBaselineAcceptancePlanning({
            manifest: manifest(),
            l2v3aeArtifact: l2v3aeArtifact(),
            l2v3acArtifact: l2v3acArtifact(),
            l2v3aaArtifact: l2v3aaArtifact(),
            l2v3yArtifact: l2v3yArtifact(),
            writeFiles: true,
            artifactOutputPath: artifactPath,
            reportOutputPath: reportPath,
            manifestOutputPath: manifestPath,
        });

        assert.equal(result.ok, true);
        assert.equal(JSON.parse(fs.readFileSync(artifactPath, 'utf8')).proposal_phase, 'Phase 5.21L2V3AF');
        assert.match(fs.readFileSync(reportPath, 'utf8'), /baseline_review_ready is not baseline accepted/i);
        assert.equal(JSON.parse(fs.readFileSync(manifestPath, 'utf8')).raw_write_ready_for_execution, false);
    } finally {
        fs.rmSync(tmpDir, { recursive: true, force: true });
    }
});

test('CLI covers help, invalid options, and planning output without writes', () => {
    let helpOutput = '';
    let invalidOutput = '';
    let successOutput = '';

    const helpStatus = mod.runCli(['--help'], { stdout: text => (helpOutput += text) });
    const invalidStatus = mod.runCli(['--unknown'], { stdout: text => (invalidOutput += text) });
    const successStatus = mod.runCli(['--write-files=false'], { stdout: text => (successOutput += text) });

    assert.equal(helpStatus, 0);
    assert.match(helpOutput, /baseline acceptance planning only/);
    assert.equal(invalidStatus, 2);
    assert.match(invalidOutput, /unknown arguments/);
    assert.equal(successStatus, 0);
    assert.match(successOutput, /"baseline_review_ready_count": 50/);
    assert.match(successOutput, /"baseline_acceptance_performed": false/);
});

test('repository L2V3AF artifacts preserve planning-only safety when generated', () => {
    const artifactPath =
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.baseline_acceptance_plan.phase521l2v3af.json';
    if (!fs.existsSync(path.join(PROJECT_ROOT, artifactPath))) return;

    const manifestJson = readJson('docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json');
    const artifact = readJson(artifactPath);
    const report = readText('docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3AF.md');

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3AF');
    assert.equal(artifact.baseline_acceptance_planning_only, true);
    assert.equal(artifact.identity_mapping_accepted_count, 50);
    assert.equal(artifact.baseline_review_candidate_count, 50);
    assert.equal(artifact.baseline_review_ready_count, 50);
    assert.equal(artifact.baseline_review_blocked_count, 0);
    assert.equal(artifact.baseline_acceptance_execution_performed, false);
    assert.equal(artifact.baseline_acceptance_performed, false);
    assert.equal(artifact.raw_write_retry_performed, false);
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(manifestJson.phase_5_21_l2v3af_baseline_review_ready_count, 50);
    assert.equal(manifestJson.baseline_acceptance_performed, false);
    assert.equal(manifestJson.raw_write_ready_for_execution, false);
    assert.equal(manifestJson.requires_separate_final_db_write_authorization, true);
    assert.match(report, /identity mapping accepted is not baseline acceptance/i);
});
