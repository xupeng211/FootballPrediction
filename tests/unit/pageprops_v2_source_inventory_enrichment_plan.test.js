'use strict';
/* eslint-disable max-lines -- L2V3U safety contract is intentionally audited together. */

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/pageprops_v2_source_inventory_enrichment_plan.js');
const rawWrite = require('../../scripts/ops/renewed_pageprops_v2_raw_write_execute');

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

function candidate(index, overrides = {}) {
    return {
        target_id: `batch:53_20252026_${9000001 + index}`,
        batch_id: 'fotmob-pageprops-v2-ligue1-2025-2026-profile-001',
        source: 'fotmob',
        route: 'html_hydration',
        raw_data_version: 'fotmob_pageprops_v2',
        hash_strategy: 'stable_pageprops_payload_v1',
        match_id: `53_20252026_${9000001 + index}`,
        external_id: String(9000001 + index),
        source_path: 'l1_api_data_leagues',
        league_id: 53,
        league_name: 'Ligue 1',
        season: '2025/2026',
        home_team: `Home ${index}`,
        away_team: `Away ${index}`,
        kickoff_time: '2025-08-15T18:45:00.000Z',
        match_date: '2025-08-15T18:45:00.000Z',
        status: 'finished',
        preflight_status: 'hash_baseline_ready',
        baseline_hash: 'c0365494bedfad7f49c59db649dc52d45bd364e7991f518261085349bebd530b',
        raw_write_ready_for_execution: false,
        ...overrides,
    };
}

function syntheticManifest(overrides = {}) {
    return {
        batch_id: 'fotmob-pageprops-v2-ligue1-2025-2026-profile-001',
        source: 'fotmob',
        route: 'html_hydration',
        raw_data_version: 'fotmob_pageprops_v2',
        hash_strategy: 'stable_pageprops_payload_v1',
        candidate_targets: Array.from({ length: 2 }, (_, index) => candidate(index)),
        next_required_step: 'source_inventory_enrichment_planning',
        recommended_next_step: 'Phase 5.21L2V3U: source inventory enrichment planning',
        raw_write_ready_for_execution: false,
        accepted_mapping_count: 0,
        requires_separate_identity_mapping_acceptance: true,
        requires_separate_baseline_acceptance: true,
        requires_separate_final_db_write_authorization: true,
        ...overrides,
    };
}

function syntheticL2V3TArtifact(overrides = {}) {
    return {
        proposal_phase: 'Phase 5.21L2V3T',
        controlled_live_check_performed: false,
        network_request_performed: false,
        previous_endpoint_status: 'blocked_http_403',
        precise_detail_endpoint_found: 'unknown',
        endpoint_avoids_slug_reuse: 'unknown',
        accepted_mapping_count: 0,
        raw_write_ready_for_execution: false,
        endpoint_investigation_result:
            'no_new_safe_public_detail_endpoint_candidate_found_public_api_403_remains_and_source_inventory_pageUrl_metadata_is_missing_from_manifest',
        recommended_strategy: 'Phase 5.21L2V3U: source inventory enrichment planning',
        evidence_summary: {
            source_inventory_page_url_extraction_supported: true,
        },
        ...overrides,
    };
}

function sourceTextByPath() {
    return {
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json':
            'candidate_targets source_inventory',
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.continued_detail_endpoint_investigation.phase521l2v3t.json':
            'source_inventory page_url_base',
        'scripts/ops/single_league_target_discovery_source_inventory_preflight.js':
            'source_inventory pageUrl candidate_targets',
        'src/infrastructure/services/FotMobSourceInventoryAdapter.js': 'source_inventory pageUrl',
        'scripts/ops/pageprops_v2_target_source_inventory_reconciliation_plan.js':
            'source_inventory page_url_base candidate_targets',
        'scripts/ops/pageprops_v2_no_write_preview.js': 'candidate_targets',
        'scripts/ops/pageprops_v2_metadata_only_detail_check.js': 'page_url_base',
        'scripts/ops/single_league_small_batch_target_manifest_plan.js': 'candidate_targets',
    };
}

function existingPaths() {
    return new Set([
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json',
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.continued_detail_endpoint_investigation.phase521l2v3t.json',
        'scripts/ops/single_league_target_discovery_source_inventory_preflight.js',
        'src/infrastructure/services/FotMobSourceInventoryAdapter.js',
        'scripts/ops/pageprops_v2_target_source_inventory_reconciliation_plan.js',
        'scripts/ops/pageprops_v2_no_write_preview.js',
        'scripts/ops/pageprops_v2_metadata_only_detail_check.js',
        'scripts/ops/single_league_small_batch_target_manifest_plan.js',
    ]);
}

function buildSyntheticRunResult(overrides = {}) {
    return mod.runSourceInventoryEnrichmentPlan({
        manifest: syntheticManifest(),
        l2v3tArtifact: syntheticL2V3TArtifact(),
        l2v3rArtifact: {
            current_url_strategy: 'fotmob_match_external_id_route',
            uses_source_inventory_page_url: false,
        },
        l2v3qArtifact: { missing_pageurl_base_count: 42, detail_url_construction_suspect_count: 42 },
        l2v3pArtifact: { checked_target_count: 42 },
        l2v3nArtifact: { checked_target_count: 50 },
        sourceTextByPath: sourceTextByPath(),
        existingPaths: existingPaths(),
        writeFiles: false,
        ...overrides,
    });
}

test('L2V3U artifact records no-write source inventory enrichment planning', () => {
    const result = buildSyntheticRunResult();
    assert.equal(result.ok, true);

    const artifact = result.artifact;
    const manifest = result.updated_manifest;

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3U');
    assert.equal(artifact.no_write, true);
    assert.equal(artifact.network_request_performed, false);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_insert_performed, false);
    assert.equal(artifact.matches_write_performed, false);
    assert.equal(artifact.matches_external_id_modified, false);
    assert.equal(artifact.identity_mapping_acceptance_performed, false);
    assert.equal(artifact.baseline_acceptance_performed, false);
    assert.equal(artifact.raw_write_retry_performed, false);
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(artifact.accepted_mapping_count, 0);

    assert.equal(manifest.phase_5_21_l2v3u_planning_status, artifact.artifact_status);
    assert.equal(manifest.source_inventory_enrichment_planning_status, artifact.artifact_status);
    assert.equal(manifest.accepted_mapping_count, 0);
    assert.equal(manifest.raw_write_ready_for_execution, false);
});

test('missing requested-side URL evidence remains a blocker and requires follow-up regeneration', () => {
    const result = buildSyntheticRunResult();
    const artifact = result.artifact;

    assert.equal(artifact.missing_source_page_url_count, 2);
    assert.equal(artifact.missing_page_url_base_count, 2);
    assert.equal(artifact.missing_url_fragment_external_id_count, 2);
    assert.equal(artifact.missing_source_record_key_count, 2);
    assert.equal(artifact.current_manifest_gap_summary.source_identity_evidence_field_gap_count, 8);
    assert.equal(artifact.requires_followup_implementation, true);
    assert.equal(artifact.requires_target_regeneration, true);
    assert.equal(artifact.identity_evidence_status, 'blocked_pending_source_inventory_enrichment');
    assert.equal(artifact.safety_contract.missing_page_url_base_remains_blocker, true);
});

test('proposed source inventory fields are explicitly required for future target regeneration', () => {
    const result = buildSyntheticRunResult();
    const fields = new Set(result.artifact.proposed_enrichment_fields.map(item => item.field));

    for (const field of [
        'source_page_url',
        'source_page_url_base',
        'source_url_fragment_external_id',
        'source_slug',
        'source_route_code',
        'schedule_external_id',
        'schedule_date',
        'schedule_home_team',
        'schedule_away_team',
        'source_inventory_record_key',
        'source_inventory_generated_at',
        'identity_evidence_status',
    ]) {
        assert.equal(fields.has(field), true, `${field} should be proposed`);
    }
    assert.equal(result.artifact.proposed_new_field_count, 12);
});

test('existing enriched URL fields remove blocker without implying mapping or raw write readiness', () => {
    const enrichedManifest = syntheticManifest({
        candidate_targets: [
            candidate(0, {
                source_page_url: '/matches/home-vs-away/abcd12#9000001',
                source_page_url_base: '/matches/home-vs-away/abcd12',
                source_url_fragment_external_id: '9000001',
                source_slug: 'home-vs-away',
                source_route_code: 'abcd12',
                source_inventory_record_key: 'overview.matches.allMatches#9000001',
                source_inventory_generated_at: '2026-05-21T08:00:00Z',
                identity_evidence_status: 'ready_for_future_review',
            }),
        ],
    });
    const result = buildSyntheticRunResult({ manifest: enrichedManifest });

    assert.equal(result.artifact.missing_source_page_url_count, 0);
    assert.equal(result.artifact.missing_page_url_base_count, 0);
    assert.equal(result.artifact.missing_url_fragment_external_id_count, 0);
    assert.equal(result.artifact.missing_source_record_key_count, 0);
    assert.equal(result.artifact.requires_followup_implementation, false);
    assert.equal(result.artifact.accepted_mapping_count, 0);
    assert.equal(result.artifact.raw_write_ready_for_execution, false);
    assert.equal(result.artifact.safety_contract.source_inventory_enrichment_plan_is_not_raw_write_authorization, true);
});

test('updated manifest is still rejected by the raw write runner gate', () => {
    const result = buildSyntheticRunResult();
    const gate = rawWrite.validateManifestGate(result.updated_manifest);

    assert.equal(gate.ok, false);
    assert.match(gate.errors.join('\n'), /required_next_step|write_execution_status|raw_match_data_write_status/i);
});

test('outputs avoid full raw data pageProps and source body payloads', () => {
    const result = buildSyntheticRunResult();
    const texts = [JSON.stringify(result.artifact), result.report, JSON.stringify(result.updated_manifest)];

    for (const text of texts) {
        assert.equal(text.includes('"raw_data":'), false);
        assert.equal(text.includes('"pageProps":'), false);
        assert.equal(text.includes('__NEXT_DATA__'), false);
        assert.equal(text.includes('<!DOCTYPE'), false);
        assert.equal(text.includes('"source_body":'), false);
        assert.equal(text.includes('"full_json":'), false);
    }
});

test('runSourceInventoryEnrichmentPlan can write outputs to explicit temp paths', () => {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'l2v3u-enrichment-'));
    const artifactPath = path.join(tmpDir, 'artifact.json');
    const reportPath = path.join(tmpDir, 'report.md');
    const manifestPath = path.join(tmpDir, 'manifest.json');

    try {
        const result = buildSyntheticRunResult({
            writeFiles: true,
            artifactOutputPath: artifactPath,
            reportOutputPath: reportPath,
            manifestOutputPath: manifestPath,
        });

        assert.equal(result.ok, true);
        assert.equal(JSON.parse(fs.readFileSync(artifactPath, 'utf8')).proposal_phase, 'Phase 5.21L2V3U');
        assert.match(fs.readFileSync(reportPath, 'utf8'), /source inventory enrichment plan is not accepted mapping/i);
        assert.equal(JSON.parse(fs.readFileSync(manifestPath, 'utf8')).raw_write_ready_for_execution, false);
    } finally {
        fs.rmSync(tmpDir, { recursive: true, force: true });
    }
});

test('CLI parsing covers help, unknowns, and write-files option', () => {
    const parsed = mod.parseArgs(['--write-files=false', '--mystery', 'positional', '--h']);
    const splitParsed = mod.parseArgs(['--write-files', 'maybe']);
    const invalid = mod.validateCliOptions({ unknown: ['mystery'] });

    assert.equal(parsed.writeFiles, false);
    assert.equal(parsed.help, true);
    assert.deepEqual(parsed.unknown, ['mystery', 'positional']);
    assert.equal(splitParsed.writeFiles, true);
    assert.equal(invalid.ok, false);
    assert.match(invalid.errors.join('\n'), /unknown arguments/);
});

test('runCli covers help, invalid options, and repository no-write success', () => {
    let helpOutput = '';
    let invalidOutput = '';
    let successOutput = '';

    const helpStatus = mod.runCli(['--help'], { stdout: text => (helpOutput += text) });
    const invalidStatus = mod.runCli(['--unknown'], { stdout: text => (invalidOutput += text) });
    const successStatus = mod.runCli(['--write-files=false'], { stdout: text => (successOutput += text) });

    assert.equal(helpStatus, 0);
    assert.match(helpOutput, /Usage:/);
    assert.equal(invalidStatus, 2);
    assert.match(invalidOutput, /unknown arguments/);
    assert.equal(successStatus, 0);
    assert.match(successOutput, /Phase 5.21L2V3U/);
    assert.match(successOutput, /raw_write_ready_for_execution/);
});

test('validateInputs fails closed on unsafe manifest and L2V3T states', () => {
    const invalidManifest = mod.validateInputs(
        syntheticManifest({
            next_required_step: 'raw_write_retry',
            raw_write_ready_for_execution: true,
            accepted_mapping_count: 1,
        }),
        syntheticL2V3TArtifact()
    );
    const invalidT = mod.validateInputs(
        syntheticManifest(),
        syntheticL2V3TArtifact({
            proposal_phase: 'Phase 5.21L2V3S',
            controlled_live_check_performed: true,
            network_request_performed: true,
            previous_endpoint_status: 'ok',
            precise_detail_endpoint_found: true,
            endpoint_avoids_slug_reuse: true,
            accepted_mapping_count: 1,
            raw_write_ready_for_execution: true,
        })
    );

    assert.equal(invalidManifest.ok, false);
    assert.match(invalidManifest.errors.join('\n'), /next_required_step/);
    assert.match(invalidManifest.errors.join('\n'), /raw_write_ready_for_execution/);
    assert.match(invalidManifest.errors.join('\n'), /accepted_mapping_count/);
    assert.equal(invalidT.ok, false);
    assert.match(invalidT.errors.join('\n'), /L2V3T artifact/);
    assert.match(invalidT.errors.join('\n'), /controlled_live_check_performed/);
    assert.match(invalidT.errors.join('\n'), /network_request_performed/);
    assert.match(invalidT.errors.join('\n'), /blocked_http_403/);
    assert.match(invalidT.errors.join('\n'), /precise_detail_endpoint_found/);
    assert.match(invalidT.errors.join('\n'), /endpoint_avoids_slug_reuse/);
    assert.match(invalidT.errors.join('\n'), /accepted_mapping_count/);
    assert.match(invalidT.errors.join('\n'), /raw_write_ready_for_execution/);
});

test('analyzeInputPaths covers missing files, skipped text reads, and file system path reads', () => {
    const skipped = mod.analyzeInputPaths(
        [{ key: 'source_inventory_missing', path: 'missing-file.js', role: 'source_inventory_test' }],
        {
            existingPaths: new Set(['missing-file.js']),
            skipPathTextRead: true,
        }
    );
    const missing = mod.analyzeInputPaths([{ key: 'plain_missing', path: 'missing-file.js', role: 'plain' }], {
        existingPaths: new Set(),
    });
    const repoRead = mod.analyzeInputPaths([
        {
            key: 'source_inventory_preflight',
            path: 'scripts/ops/single_league_target_discovery_source_inventory_preflight.js',
            role: 'source_inventory_generation_script',
        },
    ]);

    assert.equal(skipped[0].exists, true);
    assert.equal(skipped[0].matched_pattern_count, 0);
    assert.equal(skipped[0].source_inventory_related, true);
    assert.equal(missing[0].exists, false);
    assert.equal(missing[0].source_inventory_related, false);
    assert.equal(repoRead[0].exists, true);
    assert.equal(repoRead[0].matched_pattern_count > 0, true);
});

test('repository L2V3U artifacts preserve planning-only safety when generated', () => {
    const artifactPath =
        'docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.source_inventory_enrichment_plan.phase521l2v3u.json';
    if (!fs.existsSync(path.join(PROJECT_ROOT, artifactPath))) {
        return;
    }

    const manifest = readJson('docs/_manifests/fotmob_pageprops_v2_ligue1_2025_2026_profile_001.proposal.json');
    const artifact = readJson(artifactPath);
    const report = readText('docs/_reports/DATA_ENTRYPOINT_GOVERNANCE_PHASE5_21_L2V3U.md');

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3U');
    assert.equal(artifact.no_write, true);
    assert.equal(artifact.network_request_performed, false);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_insert_performed, false);
    assert.equal(artifact.matches_write_performed, false);
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(artifact.accepted_mapping_count, 0);
    assert.equal(artifact.missing_source_page_url_count, 50);
    assert.equal(artifact.missing_page_url_base_count, 50);
    assert.equal(artifact.missing_url_fragment_external_id_count, 50);
    assert.equal(artifact.missing_source_record_key_count, 50);
    assert.equal(manifest.phase_5_21_l2v3u_planning_status, artifact.artifact_status);
    assert.equal(manifest.raw_write_ready_for_execution, false);
    assert.equal(manifest.accepted_mapping_count, 0);
    assert.ok(
        [
            'Phase 5.21L2V3V: source inventory enrichment implementation',
            'Phase 5.21L2V3W: source inventory acquisition path investigation',
        ].includes(manifest.recommended_next_step)
    );
    assert.match(report, /enrichment does not unblock raw write/i);
});
