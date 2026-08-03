'use strict';

/* eslint-disable max-lines */

// lifecycle: permanent
// Retention + REPLAY tests for the bounded FotMob detail capture pipeline.
// Fully offline: no network (structurally forbidden), no database.
//
// Retention contract: the persisted unit is a stable allowlisted payload
// (<ordinal>-<source_match_id>.payload.json) + capture manifest. The full
// HTML body never reaches disk (P1-1); manifest self-hash is required and
// recomputed (P2-1); replay is deterministic and payload-based (P2-2);
// every directory write rejects symlinked descendants (P2-3); replay binds
// candidate identity to the run plan snapshot (P2-6); resume pair checks
// bind the exact run/plan/artifact/authorization context (P1-5).

global.fetch = () => {
    throw new Error('REAL_NETWORK_FORBIDDEN_IN_TEST');
};

const { test } = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');

const {
    writeCapturePair,
    defaultRunState,
    writeRunState,
    readRunState,
    writePlanSnapshot,
    readPlanSnapshot,
    checkCompletedPair,
    replayCapturePair,
    writeDetailArtifact,
    buildRunSummary,
    sha256Bytes,
} = require('../../src/infrastructure/fotmob/FotMobDetailCaptureRetention');
const {
    sha256Text,
    canonicalJsonHash,
    computeCaptureManifestSelfHash,
    validateAndRecomputeCapturePlan,
    validateCaptureManifest,
    buildCapturePayload,
} = require('../../src/infrastructure/fotmob/FotMobDetailCaptureContract');
const {
    buildDeterministicCapturePlan,
    writePlanDocument,
} = require('../../src/infrastructure/fotmob/FotMobDetailCapturePlan');
const {
    computeBusinessContentHash,
} = require('../../src/infrastructure/fotmob/FotMobCandidateExporter');
const NextDataParser = require('../../src/parsers/fotmob/NextDataParser');
const FotMobRawParser = require('../../src/parsers/fotmob/FotMobRawParser');

const TEST_REVISION = 'a7da729fd29675c6f16e1bfc49511772d2bd590d';
const FIXED_CLOCK = '2026-08-02T12:00:00.000Z';
const RUN_ID = 'run-retention';
const AUTH_ID = 'auth-test';

function tmpDir(prefix) {
    return fs.mkdtempSync(path.join(os.tmpdir(), prefix));
}

function sha256Hex(buf) {
    return crypto.createHash('sha256').update(buf).digest('hex');
}

function makeCandidate({ id, season, home, away, kickoff }) {
    return {
        id: String(id),
        source_provider: 'FotMob',
        source_match_id: String(id),
        competition: 'Premier League',
        season,
        home_team: home,
        away_team: away,
        kickoff_at: kickoff,
    };
}

function makeV1Artifact(candidates) {
    return {
        schema_version: 'candidate-match-identity/v1',
        extracted_at: '2026-07-17T18:51:14.657Z',
        snapshot: {
            source_provider: 'FotMob',
            league_id: 47,
            competition: 'Premier League',
            seasons: [...new Set(candidates.map(c => c.season))].sort(),
            candidate_count: candidates.length,
            business_content_sha256: computeBusinessContentHash(candidates),
        },
        candidates,
    };
}

function makePlanFixture(dir, candidates, { seasons, matchIds, limit } = {}) {
    const artifactPath = path.join(dir, 'artifact.json');
    fs.writeFileSync(artifactPath, JSON.stringify(makeV1Artifact(candidates), null, 2));
    const result = buildDeterministicCapturePlan({
        artifactPath,
        seasons: seasons || [],
        matchIds: matchIds || [],
        limit,
        generatedAt: FIXED_CLOCK,
        collectorCodeRevision: TEST_REVISION,
    });
    const planPath = path.join(dir, 'plan.json');
    writePlanDocument(result.plan, planPath);
    return { plan: result.plan, planPath };
}

function makePageHtml({ matchId, homeTeam, awayTeam, kickoffAt, content }) {
    const safeContent = content !== undefined
        ? content
        : { stats: { periods: ['x'] }, lineup: { lineups: [{ team: homeTeam }] }, shotmap: { shots: [{ x: 1 }] }, liveticker: [] };
    const general = {
        matchId: String(matchId),
        homeTeam: { name: homeTeam },
        awayTeam: { name: awayTeam },
        matchTimeUTC: kickoffAt,
        season: '2024/2025',
    };
    const header = {
        homeTeam: { name: homeTeam },
        awayTeam: { name: awayTeam },
        status: { utcTime: kickoffAt },
    };
    const nextData = { props: { pageProps: { content: safeContent, general, header, ssr: true } } };
    return `<!doctype html><html><body><script id="__NEXT_DATA__" type="application/json">${JSON.stringify(nextData)}</script>${'x'.repeat(300)}</body></html>`;
}

/**
 * In-memory parse chain mirroring the capture pipeline: HTML → __NEXT_DATA__
 * → API format → FotMobRawParser. The HTML itself is never persisted.
 */
function rawDataFromHtml(html, externalId) {
    const extracted = NextDataParser.extractFromHtml(html);
    if (!extracted || extracted.success !== true) return null;
    return NextDataParser.transformToApiFormat(extracted.data, String(externalId));
}

function makePayload({ candidate, html, observedOverride }) {
    const rawData = rawDataFromHtml(html, candidate.source_match_id);
    const parsed = FotMobRawParser.parseFotMobRaw(rawData, candidate.source_match_id);
    assert.equal(parsed.ok, true, 'fixture parse must succeed');
    const g = rawData.general || {};
    const observedIdentity = {
        home_team: g.homeTeam ? g.homeTeam.name : '',
        away_team: g.awayTeam ? g.awayTeam.name : '',
        observed_match_id: String(rawData.matchId),
        // R3-P1: the fixture page's raw hydration carries
        // pageProps.general.matchId — the response-derived source.
        observed_match_id_source: 'general.matchId',
        observed_match_id_is_response_derived: true,
        observed_match_id_conflict: false,
        ...(observedOverride || {}),
    };
    const payload = buildCapturePayload({
        candidate,
        parsedData: parsed.data,
        observedIdentity,
    });
    return { payload, rawData, parsedData: parsed.data };
}

const CANDIDATE = makeCandidate({
    id: 4506263,
    season: '2024/2025',
    home: 'Manchester United',
    away: 'Fulham',
    kickoff: '2024-08-16T19:00:00Z',
});

function makePageHtmlForCandidate() {
    return makePageHtml({
        matchId: CANDIDATE.source_match_id,
        homeTeam: CANDIDATE.home_team,
        awayTeam: CANDIDATE.away_team,
        kickoffAt: CANDIDATE.kickoff_at,
    });
}

/**
 * Build a fully valid payload + manifest pair fixture for one candidate.
 * The manifest self-hash is computed LAST over the assembled document, so
 * the fixture always satisfies the required/recomputed contract (P2-1).
 */
function makePairFixture(plan, overrides = {}) {
    const html = makePageHtmlForCandidate();
    const { payload } = makePayload({ candidate: plan.candidates[0], html });
    const payloadBody = JSON.stringify(payload, null, 2) + '\n';
    const candidate = plan.candidates[0];
    const manifest = {
        schema_version: 'fotmob-match-detail-capture-manifest/v1',
        source_provider: 'FotMob',
        source_kind: 'match_detail_page',
        candidate_id: candidate.candidate_id,
        source_match_id: candidate.source_match_id,
        competition: candidate.competition,
        league_id: 47,
        season: candidate.season,
        home_team: candidate.home_team,
        away_team: candidate.away_team,
        kickoff_at: candidate.kickoff_at,
        candidate_identity_sha256: candidate.candidate_identity_sha256,
        source_plan_sha256: plan.plan_business_sha256,
        source_artifact_sha256: plan.source_artifact_sha256,
        capture_run_id: RUN_ID,
        authorization_id: AUTH_ID,
        request_ordinal: 1,
        request_budget: 1,
        delay_ms: 60000,
        request_method: 'GET',
        request_url: `https://www.fotmob.com/match/${candidate.source_match_id}`,
        request_attempted_at: FIXED_CLOCK,
        response_received_at: FIXED_CLOCK,
        http_status: 200,
        content_type: 'text/html; charset=utf-8',
        response_body_byte_size: html.length,
        response_body_sha256: sha256Hex(Buffer.from(html, 'utf8')),
        observed_match_id: candidate.source_match_id,
        observed_match_id_source: 'general.matchId',
        observed_match_id_is_response_derived: true,
        observed_match_id_match: true,
        observed_match_id_conflict: false,
        hydration_parse_ok: true,
        transformed_api_format: true,
        looks_like_valid_match_detail: true,
        has_stats: true,
        has_lineup: true,
        has_shotmap: true,
        stable_raw_payload_sha256: 'e'.repeat(64),
        stable_payload_sha256: payload.stable_payload_sha256,
        payload_file_sha256: sha256Bytes(Buffer.from(payloadBody, 'utf8')),
        payload_file_relative_path: `1-${candidate.source_match_id}.payload.json`,
        parser_component: 'NextDataParser+FotMobRawParser',
        parser_version: 'V174.0.0',
        collector_component: 'FotMobDetailCapturePipeline',
        collector_code_revision: TEST_REVISION,
        network_authorization_mode: 'explicit_network_authorization',
        ...overrides,
    };
    manifest.capture_manifest_sha256 = computeCaptureManifestSelfHash(manifest);
    return { payloadBody, payload, manifest, html };
}

/**
 * Build a complete captured run: run plan snapshot (P2-6) + captures pair.
 * No .html file is ever written to disk.
 */
function buildCapturedRun(dir, overrides = {}) {
    const { plan, planPath } = makePlanFixture(dir, [CANDIDATE], { seasons: ['2024/2025'] });
    writePlanSnapshot({ runDir: dir, plan });
    const captures = path.join(dir, 'captures');
    fs.mkdirSync(captures, { recursive: true });
    const pair = makePairFixture(plan, overrides);
    writeCapturePair({
        payloadBody: pair.payloadBody,
        manifest: pair.manifest,
        payloadFileName: `1-${CANDIDATE.source_match_id}.payload.json`,
        manifestFileName: `1-${CANDIDATE.source_match_id}.manifest.json`,
        pairDir: captures,
    });
    return { plan, planPath, ...pair };
}

// ─────────────────────────────────────────────────────────────
// E. Retention
// ─────────────────────────────────────────────────────────────

test('RETENTION: atomic payload+manifest pair write succeeds with readback; no .html ever written', () => {
    const dir = tmpDir('fotmob-ret-pair-');
    try {
        const { plan } = makePlanFixture(dir, [CANDIDATE], { seasons: ['2024/2025'] });
        const pair = makePairFixture(plan);
        const result = writeCapturePair({
            payloadBody: pair.payloadBody,
            manifest: pair.manifest,
            payloadFileName: `1-${CANDIDATE.source_match_id}.payload.json`,
            manifestFileName: `1-${CANDIDATE.source_match_id}.manifest.json`,
            pairDir: dir,
        });
        assert.equal(result.idempotent, false);
        const payloadPath = path.join(dir, `1-${CANDIDATE.source_match_id}.payload.json`);
        const manifestPath = path.join(dir, `1-${CANDIDATE.source_match_id}.manifest.json`);
        assert.ok(fs.existsSync(payloadPath));
        assert.ok(fs.existsSync(manifestPath));
        // P1-1: the retained unit is the stable payload — no raw HTML file,
        // no __NEXT_DATA__, no pageProps, no raw_data inside the outputs.
        assert.equal(fs.readdirSync(dir).some(f => f.endsWith('.html')), false);
        assert.equal(sha256Bytes(fs.readFileSync(payloadPath)), pair.manifest.payload_file_sha256);
        const writtenManifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
        assert.equal(writtenManifest.payload_file_relative_path, `1-${CANDIDATE.source_match_id}.payload.json`);
        assert.equal(validateCaptureManifest(writtenManifest).ok, true);
        const writtenPayload = JSON.parse(fs.readFileSync(payloadPath, 'utf8'));
        const serialized = JSON.stringify(writtenPayload);
        for (const marker of ['__NEXT_DATA__', 'pageProps', 'raw_data', '<!doctype']) {
            assert.ok(!serialized.includes(marker), `payload must not contain ${marker}`);
        }
        assert.equal(writtenPayload.schema_version, 'fotmob-match-detail-capture-payload/v1');
        assert.equal(writtenPayload.stable_payload_sha256, writtenManifest.stable_payload_sha256);
        assert.ok(writtenPayload.normalized.match_external_id, '4506263');
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('RETENTION: partial existing pair rejected', () => {
    const dir = tmpDir('fotmob-ret-partial-');
    try {
        const { plan } = makePlanFixture(dir, [CANDIDATE], { seasons: ['2024/2025'] });
        const pair = makePairFixture(plan);
        fs.writeFileSync(path.join(dir, `1-${CANDIDATE.source_match_id}.payload.json`), pair.payloadBody);
        assert.throws(
            () => writeCapturePair({
                payloadBody: pair.payloadBody,
                manifest: pair.manifest,
                payloadFileName: `1-${CANDIDATE.source_match_id}.payload.json`,
                manifestFileName: `1-${CANDIDATE.source_match_id}.manifest.json`,
                pairDir: dir,
            }),
            (e) => e.code === 'SAFETY_ERROR' && /pair integrity/.test(e.message)
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('RETENTION: symlink rejected', () => {
    const dir = tmpDir('fotmob-ret-symlink-');
    try {
        const targetDir = tmpDir('fotmob-ret-symtarget-');
        try {
            const { plan } = makePlanFixture(dir, [CANDIDATE], { seasons: ['2024/2025'] });
            const pair = makePairFixture(plan);
            const payloadName = `1-${CANDIDATE.source_match_id}.payload.json`;
            const manifestName = `1-${CANDIDATE.source_match_id}.manifest.json`;
            fs.writeFileSync(path.join(targetDir, payloadName), pair.payloadBody);
            fs.writeFileSync(path.join(targetDir, manifestName), JSON.stringify(pair.manifest));
            fs.symlinkSync(path.join(targetDir, payloadName), path.join(dir, payloadName));
            fs.symlinkSync(path.join(targetDir, manifestName), path.join(dir, manifestName));
            assert.throws(
                () => writeCapturePair({
                    payloadBody: pair.payloadBody,
                    manifest: pair.manifest,
                    payloadFileName: payloadName,
                    manifestFileName: manifestName,
                    pairDir: dir,
                }),
                (e) => e.code === 'SAFETY_ERROR' && /symlink|regular file/.test(e.message)
            );
        } finally {
            fs.rmSync(targetDir, { recursive: true, force: true });
        }
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

function failingFs(base, failOn, injected) {
    const proxy = Object.create(base);
    return new Proxy(base, {
        get(target, prop) {
            if (prop === 'renameSync' && failOn === 'rename') {
                return (from, to) => {
                    if (injected.after) injected.after(from, to);
                    throw new Error('injected rename failure');
                };
            }
            if (prop === 'readFileSync' && failOn === 'readback') {
                return (p, enc) => {
                    if (injected.after) injected.after(p, enc);
                    return 'CORRUPTED READBACK';
                };
            }
            return target[prop];
        },
    });
}

function assertNoPairFilesRemain(dir) {
    const names = fs.readdirSync(dir);
    assert.deepEqual(
        names.filter(n => n.endsWith('.payload.json') || n.endsWith('.manifest.json')),
        []
    );
}

test('RETENTION: payload rename failure rolls back (no files remain)', () => {
    const dir = tmpDir('fotmob-ret-rollpayload-');
    try {
        const { plan } = makePlanFixture(dir, [CANDIDATE], { seasons: ['2024/2025'] });
        const pair = makePairFixture(plan);
        const fsImpl = failingFs(fs, 'rename', {});
        assert.throws(
            () => writeCapturePair({
                payloadBody: pair.payloadBody,
                manifest: pair.manifest,
                payloadFileName: `1-${CANDIDATE.source_match_id}.payload.json`,
                manifestFileName: `1-${CANDIDATE.source_match_id}.manifest.json`,
                pairDir: dir,
                fsImpl,
            }),
            (e) => e.code === 'SAFETY_ERROR'
        );
        assertNoPairFilesRemain(dir);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('RETENTION: manifest rename failure rolls back the payload file', () => {
    const dir = tmpDir('fotmob-ret-rollmanifest-');
    try {
        const { plan } = makePlanFixture(dir, [CANDIDATE], { seasons: ['2024/2025'] });
        const pair = makePairFixture(plan);
        let renamedCount = 0;
        const throwingFs = new Proxy(fs, {
            get(target, prop) {
                if (prop === 'renameSync') {
                    return (from, to) => {
                        renamedCount += 1;
                        if (renamedCount === 2) throw new Error('injected manifest rename failure');
                        return target.renameSync(from, to);
                    };
                }
                return target[prop];
            },
        });
        assert.throws(
            () => writeCapturePair({
                payloadBody: pair.payloadBody,
                manifest: pair.manifest,
                payloadFileName: `1-${CANDIDATE.source_match_id}.payload.json`,
                manifestFileName: `1-${CANDIDATE.source_match_id}.manifest.json`,
                pairDir: dir,
                fsImpl: throwingFs,
            }),
            (e) => e.code === 'SAFETY_ERROR'
        );
        assertNoPairFilesRemain(dir);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('RETENTION: final readback failure rolls back both files', () => {
    const dir = tmpDir('fotmob-ret-readback-');
    try {
        const { plan } = makePlanFixture(dir, [CANDIDATE], { seasons: ['2024/2025'] });
        const pair = makePairFixture(plan);
        const fsImpl = failingFs(fs, 'readback', {});
        assert.throws(
            () => writeCapturePair({
                payloadBody: pair.payloadBody,
                manifest: pair.manifest,
                payloadFileName: `1-${CANDIDATE.source_match_id}.payload.json`,
                manifestFileName: `1-${CANDIDATE.source_match_id}.manifest.json`,
                pairDir: dir,
                fsImpl,
            }),
            (e) => e.code === 'SAFETY_ERROR'
        );
        assertNoPairFilesRemain(dir);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('RETENTION: identical pair is idempotent; different content never overwritten', () => {
    const dir = tmpDir('fotmob-ret-idem-');
    try {
        const { plan } = makePlanFixture(dir, [CANDIDATE], { seasons: ['2024/2025'] });
        const pair = makePairFixture(plan);
        const opts = {
            payloadBody: pair.payloadBody,
            manifest: pair.manifest,
            payloadFileName: `1-${CANDIDATE.source_match_id}.payload.json`,
            manifestFileName: `1-${CANDIDATE.source_match_id}.manifest.json`,
            pairDir: dir,
        };
        const first = writeCapturePair(opts);
        assert.equal(first.idempotent, false);
        const second = writeCapturePair(opts);
        assert.equal(second.idempotent, true);

        const different = makePairFixture(plan, { request_url: 'https://www.fotmob.com/match/999999' });
        assert.throws(
            () => writeCapturePair({
                ...opts,
                payloadBody: different.payloadBody,
                manifest: different.manifest,
            }),
            (e) => e.code === 'SAFETY_ERROR' && /different content/.test(e.message)
        );
        // Original content untouched.
        assert.equal(sha256Bytes(fs.readFileSync(path.join(dir, `1-${CANDIDATE.source_match_id}.payload.json`))), pair.manifest.payload_file_sha256);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('RETENTION: manifest never contains secrets', () => {
    const dir = tmpDir('fotmob-ret-secrets-');
    try {
        const { plan } = makePlanFixture(dir, [CANDIDATE], { seasons: ['2024/2025'] });
        const pair = makePairFixture(plan);
        writeCapturePair({
            payloadBody: pair.payloadBody,
            manifest: pair.manifest,
            payloadFileName: `1-${CANDIDATE.source_match_id}.payload.json`,
            manifestFileName: `1-${CANDIDATE.source_match_id}.manifest.json`,
            pairDir: dir,
        });
        const written = fs.readFileSync(path.join(dir, `1-${CANDIDATE.source_match_id}.manifest.json`), 'utf8').toLowerCase();
        for (const secret of ['cookie', 'token', 'authorization header', 'password', 'apikey', 'secret']) {
            assert.ok(!written.includes(secret), `manifest must not contain ${secret}`);
        }
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('RETENTION: manifest validation rejects missing required fields', () => {
    const dir = tmpDir('fotmob-ret-invalid-');
    try {
        const { plan } = makePlanFixture(dir, [CANDIDATE], { seasons: ['2024/2025'] });
        const pair = makePairFixture(plan);
        delete pair.manifest.source_match_id;
        assert.throws(
            () => writeCapturePair({
                payloadBody: pair.payloadBody,
                manifest: pair.manifest,
                payloadFileName: `1-${CANDIDATE.source_match_id}.payload.json`,
                manifestFileName: `1-${CANDIDATE.source_match_id}.manifest.json`,
                pairDir: dir,
            }),
            (e) => e.code === 'SAFETY_ERROR' && /manifest validation failed/.test(e.message)
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('RETENTION: manifest self-hash is required and recomputed; tampering fails closed', () => {
    const dir = tmpDir('fotmob-ret-selfhash-');
    try {
        const { plan } = makePlanFixture(dir, [CANDIDATE], { seasons: ['2024/2025'] });
        const pair = makePairFixture(plan);

        // Missing self-hash → rejected (no lenient derive-and-accept).
        const noHash = JSON.parse(JSON.stringify(pair.manifest));
        delete noHash.capture_manifest_sha256;
        assert.throws(
            () => writeCapturePair({
                payloadBody: pair.payloadBody,
                manifest: noHash,
                payloadFileName: `1-${CANDIDATE.source_match_id}.payload.json`,
                manifestFileName: `1-${CANDIDATE.source_match_id}.manifest.json`,
                pairDir: dir,
            }),
            (e) => e.code === 'SAFETY_ERROR' && /capture_manifest_sha256/.test(e.message)
        );

        // Tampered field → recomputed self-hash no longer matches.
        const tampered = JSON.parse(JSON.stringify(pair.manifest));
        tampered.http_status = 500;
        assert.throws(
            () => writeCapturePair({
                payloadBody: pair.payloadBody,
                manifest: tampered,
                payloadFileName: `1-${CANDIDATE.source_match_id}.payload.json`,
                manifestFileName: `1-${CANDIDATE.source_match_id}.manifest.json`,
                pairDir: dir,
            }),
            (e) => e.code === 'SAFETY_ERROR' && /self-hash|does not match/.test(e.message)
        );
        assertNoPairFilesRemain(dir);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('RETENTION: run state round-trips and binds plan SHA + collector revision', () => {
    const dir = tmpDir('fotmob-ret-runstate-');
    try {
        const { plan } = makePlanFixture(dir, [CANDIDATE], { seasons: ['2024/2025'] });
        const state = defaultRunState(plan, {
            runId: RUN_ID,
            authorizationId: AUTH_ID,
            maxRequests: 3,
            delayMs: 60000,
            collectorCodeRevision: TEST_REVISION,
            startedAt: FIXED_CLOCK,
        });
        writeRunState(dir, state);
        const loaded = readRunState(dir);
        assert.equal(loaded.plan_sha256, plan.plan_business_sha256);
        assert.equal(loaded.source_artifact_sha256, plan.source_artifact_sha256);
        assert.equal(loaded.authorization_id, AUTH_ID);
        assert.equal(loaded.collector_code_revision, TEST_REVISION);
        assert.equal(loaded.network_requests_attempted, 0);
        assert.equal(loaded.schema_version, 'fotmob-detail-capture-run-state/v1');
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('RETENTION: plan snapshot atomic, idempotent, never overwrites, rejects symlink, read revalidates', () => {
    const dir = tmpDir('fotmob-ret-snapshot-');
    try {
        const { plan } = makePlanFixture(dir, [CANDIDATE], { seasons: ['2024/2025'] });
        // The fixture plan.json is byte-identical to the snapshot serialization;
        // remove it so the first snapshot write is a real write.
        fs.unlinkSync(path.join(dir, 'plan.json'));
        const first = writePlanSnapshot({ runDir: dir, plan });
        assert.equal(first.idempotent, false);
        assert.ok(fs.existsSync(path.join(dir, 'plan.json')));
        const second = writePlanSnapshot({ runDir: dir, plan });
        assert.equal(second.idempotent, true);
        assert.equal(second.snapshotSha256, first.snapshotSha256);

        // Different bytes never overwrite the snapshot.
        fs.appendFileSync(path.join(dir, 'plan.json'), '// tampered\n');
        assert.throws(
            () => writePlanSnapshot({ runDir: dir, plan }),
            (e) => e.code === 'SAFETY_ERROR' && /different content/.test(e.message)
        );

        // Symlinked snapshot rejected.
        fs.rmSync(path.join(dir, 'plan.json'));
        const targetDir = path.join(dir, 'symtarget');
        fs.mkdirSync(targetDir);
        fs.writeFileSync(path.join(targetDir, 'plan.json'), '{}');
        fs.symlinkSync(path.join(targetDir, 'plan.json'), path.join(dir, 'plan.json'));
        assert.throws(
            () => writePlanSnapshot({ runDir: dir, plan }),
            (e) => e.code === 'SAFETY_ERROR'
        );
        fs.unlinkSync(path.join(dir, 'plan.json'));

        // readPlanSnapshot re-validates: tampered snapshot fails closed.
        fs.writeFileSync(path.join(dir, 'plan.json'), JSON.stringify(plan, null, 2));
        const loaded = readPlanSnapshot(dir);
        assert.equal(loaded.plan_business_sha256, plan.plan_business_sha256);
        const tampered = JSON.parse(JSON.stringify(plan));
        tampered.candidates[0].source_match_id = '999999';
        fs.writeFileSync(path.join(dir, 'plan.json'), JSON.stringify(tampered, null, 2));
        assert.throws(
            () => readPlanSnapshot(dir),
            (e) => e.code === 'SAFETY_ERROR' && /plan snapshot invalid/.test(e.message)
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

// ─────────────────────────────────────────────────────────────
// G. REPLAY
// ─────────────────────────────────────────────────────────────

test('REPLAY: fully offline deterministic replay produces a valid artifact from the payload', () => {
    const dir = tmpDir('fotmob-replay-ok-');
    try {
        const { plan, manifest } = buildCapturedRun(dir);
        // No .html exists anywhere in the run dir — replay has no HTML
        // dependency (P1-1).
        assert.equal(fs.readdirSync(path.join(dir, 'captures')).some(f => f.endsWith('.html')), false);
        const result = replayCapturePair({
            runDir: dir,
            ordinal: 1,
            sourceMatchId: CANDIDATE.source_match_id,
            runPlan: plan,
            parserCodeRevision: TEST_REVISION,
            expectedRunId: RUN_ID,
            expectedAuthorizationId: AUTH_ID,
            expectedRequestBudget: 1,
            expectedDelayMs: 60000,
            expectedCollectorCodeRevision: TEST_REVISION,
        });
        const artifact = result.artifact;
        assert.equal(artifact.schema_version, 'fotmob-match-detail-artifact/v1');
        assert.equal(artifact.source_match_id, CANDIDATE.source_match_id);
        assert.equal(artifact.candidate_id, plan.candidates[0].candidate_id);
        assert.equal(artifact.observed_identity.observed_match_id, CANDIDATE.source_match_id);
        assert.equal(artifact.observed_identity.observed_match_id_source, 'general.matchId');
        assert.equal(artifact.observed_identity.observed_match_id_is_response_derived, true);
        assert.equal(artifact.expected_identity.home_team, CANDIDATE.home_team);
        assert.equal(artifact.expected_identity.away_team, CANDIDATE.away_team);
        assert.equal(artifact.expected_identity.kickoff_at, CANDIDATE.kickoff_at);
        assert.match(artifact.payload_file_sha256, /^[0-9a-f]{64}$/);
        assert.match(artifact.structured_payload_sha256, /^[0-9a-f]{64}$/);
        assert.ok(artifact.normalized.match_external_id);
        assert.equal(String(artifact.normalized.match_external_id), CANDIDATE.source_match_id);
        // P2-2: parsed_at derives from the capture record, not wall clock.
        assert.equal(artifact.parsed_at, manifest.response_received_at);

        // Deterministic: replaying again yields byte-identical artifact.
        const again = replayCapturePair({
            runDir: dir,
            ordinal: 1,
            sourceMatchId: CANDIDATE.source_match_id,
            runPlan: plan,
            parserCodeRevision: TEST_REVISION,
            expectedRunId: RUN_ID,
            expectedAuthorizationId: AUTH_ID,
            expectedRequestBudget: 1,
            expectedDelayMs: 60000,
            expectedCollectorCodeRevision: TEST_REVISION,
        });
        assert.equal(again.artifact.structured_payload_sha256, artifact.structured_payload_sha256);
        assert.equal(again.artifact.parsed_at, artifact.parsed_at);
        assert.equal(again.artifactSha256, result.artifactSha256);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('REPLAY: payload file hash mismatch rejected', () => {
    const dir = tmpDir('fotmob-replay-payloadhash-');
    try {
        const { plan } = buildCapturedRun(dir);
        fs.writeFileSync(
            path.join(dir, 'captures', `1-${CANDIDATE.source_match_id}.payload.json`),
            Buffer.from('tampered', 'utf8')
        );
        assert.throws(
            () => replayCapturePair({
                runDir: dir,
                ordinal: 1,
                sourceMatchId: CANDIDATE.source_match_id,
                runPlan: plan,
                parserCodeRevision: TEST_REVISION,
                expectedRunId: RUN_ID,
                expectedAuthorizationId: AUTH_ID,
                expectedRequestBudget: 1,
                expectedDelayMs: 60000,
                expectedCollectorCodeRevision: TEST_REVISION,
            }),
            (e) => e.code === 'SAFETY_ERROR' && /payload file hash does not match/.test(e.message)
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('REPLAY: manifest validation failure rejected', () => {
    const dir = tmpDir('fotmob-replay-manifest-');
    try {
        const { plan } = buildCapturedRun(dir);
        const manifestPath = path.join(dir, 'captures', `1-${CANDIDATE.source_match_id}.manifest.json`);
        const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
        delete manifest.collector_code_revision;
        fs.writeFileSync(manifestPath, JSON.stringify(manifest));
        assert.throws(
            () => replayCapturePair({
                runDir: dir,
                ordinal: 1,
                sourceMatchId: CANDIDATE.source_match_id,
                runPlan: plan,
                parserCodeRevision: TEST_REVISION,
                expectedRunId: RUN_ID,
                expectedAuthorizationId: AUTH_ID,
                expectedRequestBudget: 1,
                expectedDelayMs: 60000,
                expectedCollectorCodeRevision: TEST_REVISION,
            }),
            (e) => e.code === 'SAFETY_ERROR' && /manifest invalid/.test(e.message)
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('REPLAY: missing run plan snapshot fails closed, no artifact', () => {
    const dir = tmpDir('fotmob-replay-noplan-');
    try {
        buildCapturedRun(dir);
        assert.throws(
            () => replayCapturePair({
                runDir: dir,
                ordinal: 1,
                sourceMatchId: CANDIDATE.source_match_id,
                parserCodeRevision: TEST_REVISION,
                expectedRunId: RUN_ID,
                expectedAuthorizationId: AUTH_ID,
                expectedRequestBudget: 1,
                expectedDelayMs: 60000,
                expectedCollectorCodeRevision: TEST_REVISION,
            }),
            (e) => e.code === 'SAFETY_ERROR' && /run-bound plan snapshot required/.test(e.message)
        );
        assert.ok(!fs.existsSync(path.join(dir, 'replay')));
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('REPLAY: plan candidate missing for a pair fails closed', () => {
    const dir = tmpDir('fotmob-replay-nocand-');
    try {
        const { plan } = buildCapturedRun(dir);
        const stripped = JSON.parse(JSON.stringify(plan));
        stripped.candidates = [];
        assert.throws(
            () => replayCapturePair({
                runDir: dir,
                ordinal: 1,
                sourceMatchId: CANDIDATE.source_match_id,
                runPlan: stripped,
                parserCodeRevision: TEST_REVISION,
                expectedRunId: RUN_ID,
                expectedAuthorizationId: AUTH_ID,
                expectedRequestBudget: 1,
                expectedDelayMs: 60000,
                expectedCollectorCodeRevision: TEST_REVISION,
            }),
            (e) => e.code === 'SAFETY_ERROR' && /has no candidate/.test(e.message)
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('REPLAY: manifest bound to a different plan candidate fails closed', () => {
    const dir = tmpDir('fotmob-replay-otherplan-');
    try {
        const { plan } = buildCapturedRun(dir);
        const otherPlan = JSON.parse(JSON.stringify(plan));
        otherPlan.candidates[0].candidate_identity_sha256 = 'f'.repeat(64);
        assert.throws(
            () => replayCapturePair({
                runDir: dir,
                ordinal: 1,
                sourceMatchId: CANDIDATE.source_match_id,
                runPlan: otherPlan,
                parserCodeRevision: TEST_REVISION,
                expectedRunId: RUN_ID,
                expectedAuthorizationId: AUTH_ID,
                expectedRequestBudget: 1,
                expectedDelayMs: 60000,
                expectedCollectorCodeRevision: TEST_REVISION,
            }),
            (e) => e.code === 'SAFETY_ERROR' && /does not match run plan snapshot/.test(e.message)
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('REPLAY: atomic write, symlink rejection, no overwrite of different content', () => {
    const dir = tmpDir('fotmob-replay-write-');
    try {
        const { plan } = buildCapturedRun(dir);
        const result = replayCapturePair({
            runDir: dir,
            ordinal: 1,
            sourceMatchId: CANDIDATE.source_match_id,
            runPlan: plan,
            parserCodeRevision: TEST_REVISION,
            expectedRunId: RUN_ID,
            expectedAuthorizationId: AUTH_ID,
            expectedRequestBudget: 1,
            expectedDelayMs: 60000,
            expectedCollectorCodeRevision: TEST_REVISION,
        });
        const replayDir = path.join(dir, 'replay');
        const first = writeDetailArtifact({
            artifact: result.artifact,
            replayDir,
            ordinal: 1,
            sourceMatchId: CANDIDATE.source_match_id,
        });
        assert.ok(fs.existsSync(first.artifactPath));

        // Idempotent rewrite of identical bytes.
        const second = writeDetailArtifact({
            artifact: result.artifact,
            replayDir,
            ordinal: 1,
            sourceMatchId: CANDIDATE.source_match_id,
        });
        assert.equal(second.idempotent, true);

        // Different content must not overwrite.
        const different = JSON.parse(JSON.stringify(result.artifact));
        different.structured_payload_sha256 = 'f'.repeat(64);
        assert.throws(
            () => writeDetailArtifact({
                artifact: different,
                replayDir,
                ordinal: 1,
                sourceMatchId: CANDIDATE.source_match_id,
            }),
            (e) => e.code === 'SAFETY_ERROR' && /different content/.test(e.message)
        );

        // Symlink destination rejected.
        fs.rmSync(first.artifactPath);
        const targetDir = path.join(dir, 'symtarget');
        fs.mkdirSync(targetDir);
        fs.writeFileSync(path.join(targetDir, 'fake.json'), '{}');
        fs.symlinkSync(path.join(targetDir, 'fake.json'), first.artifactPath);
        assert.throws(
            () => writeDetailArtifact({
                artifact: result.artifact,
                replayDir,
                ordinal: 1,
                sourceMatchId: CANDIDATE.source_match_id,
            }),
            (e) => e.code === 'SAFETY_ERROR'
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('RETENTION: checkCompletedPair distinguishes complete/partial/mismatch and binds run context', () => {
    const dir = tmpDir('fotmob-ret-check-');
    try {
        const { plan } = buildCapturedRun(dir);
        const candidate = plan.candidates[0];
        const expected = {
            runDir: dir,
            ordinal: 1,
            sourceMatchId: candidate.source_match_id,
            expectedRunId: RUN_ID,
            expectedAuthorizationId: AUTH_ID,
            expectedRequestBudget: 1,
            expectedDelayMs: 60000,
            expectedCollectorCodeRevision: TEST_REVISION,
            expectedPlanSha256: plan.plan_business_sha256,
            expectedSourceArtifactSha256: plan.source_artifact_sha256,
            expectedCandidate: candidate,
            expectedRequestUrl: `https://www.fotmob.com/match/${candidate.source_match_id}`,
        };
        const complete = checkCompletedPair(expected);
        assert.equal(complete.state, 'complete');
        assert.equal(complete.completed, true);

        // Remove manifest → partial.
        fs.unlinkSync(path.join(dir, 'captures', `1-${CANDIDATE.source_match_id}.manifest.json`));
        const partial = checkCompletedPair(expected);
        assert.equal(partial.state, 'partial');

        // Add manifest back with wrong payload hash → mismatch.
        const { manifest } = makePairFixture(plan, {
            payload_file_sha256: '0'.repeat(64),
        });
        fs.writeFileSync(path.join(dir, 'captures', `1-${CANDIDATE.source_match_id}.manifest.json`), JSON.stringify(manifest));
        const hashMismatch = checkCompletedPair(expected);
        assert.equal(hashMismatch.state, 'mismatch');
        assert.equal(hashMismatch.completed, false);

        // P1-5: a pair copied from another run id is a context mismatch,
        // never treated as completed.
        fs.writeFileSync(
            path.join(dir, 'captures', `1-${CANDIDATE.source_match_id}.manifest.json`),
            JSON.stringify(makePairFixture(plan).manifest)
        );
        const wrongRun = checkCompletedPair({ ...expected, expectedRunId: 'run-other' });
        assert.equal(wrongRun.state, 'mismatch');
        assert.match(wrongRun.detail, /RESUME_PAIR_CONTEXT_MISMATCH:manifest.capture_run_id/);

        const wrongCandidate = checkCompletedPair({ ...expected, expectedCandidate: { ...candidate, candidate_id: '999' } });
        assert.equal(wrongCandidate.state, 'mismatch');
        assert.match(wrongCandidate.detail, /RESUME_PAIR_CONTEXT_MISMATCH:manifest.candidate_id/);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('RETENTION: run summary proves zero database writes and counts attempts/responses/captures', () => {
    const dir = tmpDir('fotmob-ret-summary-');
    try {
        const runState = {
            schema_version: 'fotmob-detail-capture-run-state/v1',
            run_id: 'run-summary',
            plan_sha256: 'b'.repeat(64),
            source_artifact_sha256: 'c'.repeat(64),
            authorization_id: AUTH_ID,
            status: 'complete',
            stopped_at_ordinal: null,
            stop_reason: null,
            network_requests_attempted: 3,
            network_responses_received: 3,
            network_requests_made: 3,
            real_fotmob_network_requests: 3,
            completed_ordinals: [1, 2, 3],
        };
        const summary = buildRunSummary(runState, { selected_candidate_count: 3 }, [1, 2, 3]);
        assert.equal(summary.schema_version, 'fotmob-detail-capture-run-summary/v1');
        assert.equal(summary.database_writes, 0);
        assert.equal(summary.network_requests_attempted, 3);
        assert.equal(summary.network_responses_received, 3);
        assert.equal(summary.captures_completed, 3);
        assert.equal(summary.network_requests_made, 3);
        assert.equal(summary.real_fotmob_network_requests, 3);
        assert.deepEqual(summary.completed_ordinals, [1, 2, 3]);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});
