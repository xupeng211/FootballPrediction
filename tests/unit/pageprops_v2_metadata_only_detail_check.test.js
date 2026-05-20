'use strict';
/* eslint-disable max-lines -- L2V3P safety contract stays together for auditability. */

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/pageprops_v2_metadata_only_detail_check.js');

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

function fakePageProps(overrides = {}) {
    return {
        content: { matchFacts: {}, stats: [{ key: 'shots' }] },
        general: {
            matchId: '9000001',
            homeTeam: { name: 'Home FC' },
            awayTeam: { name: 'Away FC' },
            matchTimeUTC: '2025-08-15T18:45:00.000Z',
            status: 'finished',
            pageUrl: '/matches/home-fc-vs-away-fc/safe#9000001',
        },
        header: {
            teams: [{ name: 'Home FC' }, { name: 'Away FC' }],
            status: { utcTime: '2025-08-15T18:45:00.000Z' },
        },
        ...overrides,
    };
}

function fakeHtml(pageProps = fakePageProps()) {
    return `<html><body><script id="__NEXT_DATA__" type="application/json">${JSON.stringify({
        props: { pageProps },
    })}</script></body></html>`;
}

function fetchResult({
    body = fakeHtml(),
    status = 200,
    finalUrl = 'https://www.fotmob.com/matches/home-vs-away/safe#9000001',
} = {}) {
    return {
        ok: status === 200,
        request_url: 'https://www.fotmob.com/match/9000001',
        final_url: finalUrl,
        http_status: status,
        content_type: 'text/html; charset=utf-8',
        body_byte_length: Buffer.byteLength(body, 'utf8'),
        body,
    };
}

function syntheticManifest() {
    return {
        batch_id: 'fotmob-pageprops-v2-ligue1-2025-2026-profile-001',
        source: 'fotmob',
        route: 'html_hydration',
        league: { league_name: 'Ligue 1', season: '2025/2026' },
        candidate_targets: Array.from({ length: 50 }, (_, index) => ({
            match_id: `53_20252026_${9000001 + index}`,
            external_id: String(9000001 + index),
            home_team: 'Home FC',
            away_team: 'Away FC',
            match_date: '2025-08-15T18:45:00.000Z',
            kickoff_time: '2025-08-15T18:45:00.000Z',
            status: 'finished',
            season: '2025/2026',
        })),
    };
}

function syntheticInvestigationArtifact() {
    return {
        proposal_phase: 'Phase 5.21L2V3O',
        checked_unknown_target_count: 42,
        still_unknown_count: 42,
        controlled_metadata_check_performed: false,
        unknown_target_investigation: Array.from({ length: 42 }, (_, index) => ({
            schedule_external_id: String(9000001 + index),
        })),
    };
}

function syntheticVerificationArtifact() {
    return { unknown_count: 42 };
}

async function buildSyntheticRunResult(overrides = {}) {
    return mod.runMetadataOnlyDetailCheck(
        {
            manifest: mod.MANIFEST_PATH,
            investigationArtifact: mod.INVESTIGATION_ARTIFACT_PATH,
            verificationArtifact: mod.VERIFICATION_ARTIFACT_PATH,
            artifactOutput: mod.ARTIFACT_OUTPUT_PATH,
            reportOutput: mod.REPORT_PATH,
            source: 'fotmob',
            route: 'html_hydration',
            leagueId: 53,
            leagueName: 'Ligue 1',
            season: '2025/2026',
            targetCount: 42,
            metadataOnlyPhaseAuthorization: true,
            controlledMetadataOnlyCheckAuthorization: true,
            networkAuthorization: true,
            allowDbWrite: false,
            allowRawMatchDataWrite: false,
            allowMatchesWrite: false,
            allowSchemaMigration: false,
            allowParserImplementation: false,
            allowFeatureExtraction: false,
            allowTraining: false,
            allowPrediction: false,
            allowBrowserRuntime: false,
            allowProxyRuntime: false,
            printFullBody: false,
            saveFullBody: false,
            printFullJson: false,
            saveFullJson: false,
            printFullPageprops: false,
            saveFullPageprops: false,
            retry: 0,
            concurrency: 1,
            requestDelayMs: 0,
            ...overrides.input,
        },
        {
            manifest: syntheticManifest(),
            investigationArtifact: syntheticInvestigationArtifact(),
            verificationArtifact: syntheticVerificationArtifact(),
            fetchResultsByExternalId: Object.fromEntries(
                Array.from({ length: 42 }, (_, index) => [String(9000001 + index), fetchResult()])
            ),
            writeFiles: false,
            ...overrides.dependencies,
        }
    );
}

test('L2V3P artifact records controlled no-write metadata-only detail check', async () => {
    const result = await buildSyntheticRunResult();
    const artifact = result.artifact;
    const manifest = result.updated_manifest;

    assert.equal(artifact.proposal_phase, 'Phase 5.21L2V3P');
    assert.equal(artifact.no_write, true);
    assert.equal(artifact.controlled_metadata_check_performed, true);
    assert.equal(artifact.live_source_check_performed, true);
    assert.equal(artifact.db_write_performed, false);
    assert.equal(artifact.raw_insert_performed, false);
    assert.equal(artifact.matches_write_performed, false);
    assert.equal(artifact.matches_external_id_modified, false);
    assert.equal(artifact.schema_migration_performed, false);
    assert.equal(artifact.identity_mapping_acceptance_performed, false);
    assert.equal(artifact.baseline_acceptance_performed, false);
    assert.equal(artifact.raw_write_retry_performed, false);
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(artifact.accepted_mapping_count, 0);

    assert.equal(manifest.phase_5_21_l2v3p_metadata_check_status, artifact.artifact_status);
    assert.equal(manifest.controlled_metadata_check_performed, true);
    assert.equal(manifest.raw_write_ready_for_execution, false);
    assert.equal(manifest.accepted_mapping_count, 0);
});

test('L2V3P metadata-only results keep all targets blocked from acceptance and raw write', async () => {
    const result = await buildSyntheticRunResult();
    const artifact = result.artifact;

    assert.equal(artifact.requested_unknown_target_count, 42);
    assert.equal(artifact.attempted_unknown_target_count, 42);
    assert.equal(artifact.raw_write_blocked_count, 42);
    assert.equal(artifact.identity_mapping_acceptance_blocked_count, 42);
    assert.equal(artifact.accepted_mapping_count, 0);

    for (const entry of artifact.metadata_only_target_summaries) {
        assert.equal(entry.accepted_mapping, false, entry.schedule_external_id);
        assert.equal(entry.raw_write_blocked, true, entry.schedule_external_id);
        assert.equal(entry.identity_mapping_acceptance_blocked, true, entry.schedule_external_id);
        assert.notEqual(entry.raw_write_blocker_status, 'not_blocked', entry.schedule_external_id);
    }
});

test('metadata-only success and safe review signals do not imply acceptance', async () => {
    const result = await buildSyntheticRunResult();
    const artifact = result.artifact;

    assert.equal(artifact.safety_contract.metadata_only_result_is_not_accepted_mapping, true);
    assert.equal(artifact.safety_contract.metadata_check_success_does_not_equal_accepted_mapping, true);
    assert.equal(artifact.safety_contract.metadata_check_success_does_not_equal_raw_write_ready, true);
    assert.equal(artifact.safety_contract.date_match_is_not_accepted_mapping, true);
    assert.equal(artifact.safety_contract.same_utc_day_is_not_accepted_mapping, true);
    assert.equal(artifact.safety_contract.safe_to_consider_for_future_review_is_not_accepted_mapping, true);
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(artifact.accepted_mapping_count, 0);
});

test('controlled metadata check guard refuses any DB write intent', () => {
    assert.equal(mod.assertMetadataOnlyCheckNoWrite(), true);
    assert.throws(() => mod.assertMetadataOnlyCheckNoWrite({ dbWriteRequested: true }), /must remain no-write/);
    assert.throws(() => mod.assertMetadataOnlyCheckNoWrite({ rawInsertRequested: true }), /must remain no-write/);
    assert.throws(() => mod.assertMetadataOnlyCheckNoWrite({ matchesWriteRequested: true }), /must remain no-write/);
    assert.throws(
        () => mod.assertMetadataOnlyCheckNoWrite({ matchesExternalIdModified: true }),
        /must remain no-write/
    );
});

test('block or captcha detection stops execution immediately', async () => {
    const result = await buildSyntheticRunResult({
        dependencies: {
            fetchResultsByExternalId: {
                9000001: fetchResult({
                    body: '<html><body><h1>Captcha</h1></body></html>',
                    status: 200,
                }),
            },
        },
    });

    assert.equal(result.ok, true);
    assert.equal(result.artifact.stopped_early, true);
    assert.equal(result.artifact.stop_category, 'block_or_captcha');
    assert.equal(result.artifact.attempted_unknown_target_count, 1);
    assert.equal(result.artifact.metadata_check_blocked_count, 1);
});

test('synthetic date_match result stays blocked and unaccepted', async () => {
    const result = await buildSyntheticRunResult({
        input: { targetExternalIds: ['9000001'] },
        dependencies: {
            fetchResultsByExternalId: {
                9000001: fetchResult(),
            },
        },
    });

    const entry = result.artifact.metadata_only_target_summaries[0];
    assert.equal(entry.date_rule_status, 'date_match');
    assert.equal(entry.parsed, true);
    assert.equal(entry.safe_to_consider_for_future_review, true);
    assert.equal(entry.accepted_mapping, false);
    assert.equal(entry.raw_write_blocked, true);
    assert.equal(result.artifact.accepted_mapping_count, 0);
    assert.equal(result.artifact.raw_write_ready_for_execution, false);
});

test('L2V3P artifacts avoid full raw_data pageProps and source body payloads', async () => {
    const result = await buildSyntheticRunResult();
    const texts = [JSON.stringify(result.artifact), result.report, JSON.stringify(result.updated_manifest)];

    for (const text of texts) {
        assert.equal(text.includes('"raw_data":'), false);
        assert.equal(text.includes('"pageProps":'), false);
        assert.equal(text.includes('__NEXT_DATA__'), false);
        assert.equal(text.includes('<!DOCTYPE'), false);
        assert.equal(text.includes('"source_body":'), false);
    }
});

test('L2V3P unresolved artifact cannot be used by raw write runner to bypass guards', async () => {
    const result = await buildSyntheticRunResult();
    const artifact = result.artifact;
    const manifest = result.updated_manifest;

    assert.equal(artifact.accepted_mapping_count, 0);
    assert.equal(artifact.raw_write_ready_for_execution, false);
    assert.equal(manifest.phase_5_21_l2v3p_accepted_mapping_count, 0);
    assert.equal(manifest.phase_5_21_l2v3p_raw_write_ready_for_execution, false);
    assert.equal(manifest.raw_write_ready_for_execution, false);
});
