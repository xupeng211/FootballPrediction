'use strict';

// lifecycle: permanent
// Retention + REPLAY tests for the bounded FotMob detail capture pipeline.
// Fully offline: no network (structurally forbidden), no database.

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
    checkCompletedPair,
    replayCapturePair,
    writeDetailArtifact,
    buildRunSummary,
    sha256Bytes,
} = require('../../src/infrastructure/fotmob/FotMobDetailCaptureRetention');
const {
    sha256Text,
    canonicalJsonHash,
} = require('../../src/infrastructure/fotmob/FotMobDetailCaptureContract');
const NextDataParser = require('../../src/parsers/fotmob/NextDataParser');
const FotMobRawParser = require('../../src/parsers/fotmob/FotMobRawParser');

const TEST_REVISION = 'a7da729fd29675c6f16e1bfc49511772d2bd590d';
const FIXED_CLOCK = '2026-08-02T12:00:00.000Z';

function tmpDir(prefix) {
    return fs.mkdtempSync(path.join(os.tmpdir(), prefix));
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

function makeValidManifest(overrides = {}) {
    return {
        schema_version: 'fotmob-match-detail-capture-manifest/v1',
        source_provider: 'FotMob',
        source_kind: 'match_detail_page',
        request_method: 'GET',
        request_url: 'https://www.fotmob.com/match/4506263',
        candidate_id: '4506263',
        source_match_id: '4506263',
        competition: 'Premier League',
        season: '2024/2025',
        home_team: 'Manchester United',
        away_team: 'Fulham',
        kickoff_at: '2024-08-16T19:00:00Z',
        candidate_identity_sha256: 'a'.repeat(64),
        source_plan_sha256: 'b'.repeat(64),
        source_artifact_sha256: 'c'.repeat(64),
        capture_run_id: 'run-retention',
        authorization_id: 'auth-test',
        request_ordinal: 1,
        request_budget: 1,
        delay_ms: 60000,
        capture_started_at: FIXED_CLOCK,
        capture_completed_at: FIXED_CLOCK,
        http_status: 200,
        content_type: 'text/html; charset=utf-8',
        body_byte_size: 0,
        body_sha256: 'd'.repeat(64),
        observed_match_id: '4506263',
        observed_match_id_match: true,
        hydration_parse_ok: true,
        transformed_api_format: true,
        looks_like_valid_match_detail: true,
        has_stats: true,
        has_lineup: true,
        has_shotmap: true,
        stable_raw_payload_sha256: 'e'.repeat(64),
        parser_component: 'NextDataParser',
        parser_version: 'V174.0.0',
        collector_component: 'FotMobDetailCapturePipeline',
        collector_code_revision: TEST_REVISION,
        raw_file_relative_path: '1-4506263.html',
        network_authorization_mode: 'explicit_network_authorization',
        ...overrides,
    };
}

// ─────────────────────────────────────────────────────────────
// E. Retention
// ─────────────────────────────────────────────────────────────

test('RETENTION: atomic pair write succeeds with readback', () => {
    const dir = tmpDir('fotmob-ret-pair-');
    try {
        const rawBody = Buffer.from(makePageHtml({ matchId: 4506263, homeTeam: 'Manchester United', awayTeam: 'Fulham', kickoffAt: '2024-08-16T19:00:00Z' }), 'utf8');
        const manifest = makeValidManifest({ body_sha256: sha256Bytes(rawBody), body_byte_size: rawBody.length });
        const result = writeCapturePair({
            rawBody,
            manifest,
            rawFileName: '1-4506263.html',
            manifestFileName: '1-4506263.manifest.json',
            pairDir: dir,
        });
        assert.equal(result.idempotent, false);
        assert.ok(fs.existsSync(path.join(dir, '1-4506263.html')));
        assert.ok(fs.existsSync(path.join(dir, '1-4506263.manifest.json')));
        assert.equal(sha256Bytes(fs.readFileSync(path.join(dir, '1-4506263.html'))), sha256Bytes(rawBody));
        const writtenManifest = JSON.parse(fs.readFileSync(path.join(dir, '1-4506263.manifest.json'), 'utf8'));
        assert.equal(writtenManifest.raw_file_relative_path, '1-4506263.html');
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('RETENTION: partial existing pair rejected', () => {
    const dir = tmpDir('fotmob-ret-partial-');
    try {
        const rawBody = Buffer.from('raw html', 'utf8');
        fs.writeFileSync(path.join(dir, '1-4506263.html'), rawBody);
        const manifest = makeValidManifest({ body_sha256: sha256Bytes(rawBody), body_byte_size: rawBody.length });
        assert.throws(
            () => writeCapturePair({
                rawBody,
                manifest,
                rawFileName: '1-4506263.html',
                manifestFileName: '1-4506263.manifest.json',
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
            const rawBody = Buffer.from('raw html', 'utf8');
            const manifest = makeValidManifest({ body_sha256: sha256Bytes(rawBody), body_byte_size: rawBody.length });
            fs.writeFileSync(path.join(targetDir, '1-4506263.html'), rawBody);
            fs.writeFileSync(path.join(targetDir, '1-4506263.manifest.json'), JSON.stringify(manifest));
            fs.symlinkSync(path.join(targetDir, '1-4506263.html'), path.join(dir, '1-4506263.html'));
            fs.symlinkSync(path.join(targetDir, '1-4506263.manifest.json'), path.join(dir, '1-4506263.manifest.json'));
            assert.throws(
                () => writeCapturePair({
                    rawBody,
                    manifest,
                    rawFileName: '1-4506263.html',
                    manifestFileName: '1-4506263.manifest.json',
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

test('RETENTION: raw rename failure rolls back (no files remain)', () => {
    const dir = tmpDir('fotmob-ret-rollraw-');
    try {
        const rawBody = Buffer.from('raw html', 'utf8');
        const manifest = makeValidManifest({ body_sha256: sha256Bytes(rawBody), body_byte_size: rawBody.length });
        const fsImpl = failingFs(fs, 'rename', {});
        assert.throws(
            () => writeCapturePair({
                rawBody,
                manifest,
                rawFileName: '1-4506263.html',
                manifestFileName: '1-4506263.manifest.json',
                pairDir: dir,
                fsImpl,
            }),
            (e) => e.code === 'SAFETY_ERROR'
        );
        assert.deepEqual(fs.readdirSync(dir), []);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('RETENTION: manifest rename failure rolls back the raw file', () => {
    const dir = tmpDir('fotmob-ret-rollmanifest-');
    try {
        const rawBody = Buffer.from('raw html', 'utf8');
        const manifest = makeValidManifest({ body_sha256: sha256Bytes(rawBody), body_byte_size: rawBody.length });
        let renamedCount = 0;
        const fsImpl = failingFs(fs, 'rename', {
            after: () => { renamedCount += 1; },
        });
        // Fail only on the second rename (manifest), after raw was renamed.
        const throwingFs = new Proxy(fsImpl, {
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
                rawBody,
                manifest,
                rawFileName: '1-4506263.html',
                manifestFileName: '1-4506263.manifest.json',
                pairDir: dir,
                fsImpl: throwingFs,
            }),
            (e) => e.code === 'SAFETY_ERROR'
        );
        assert.deepEqual(fs.readdirSync(dir), []);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('RETENTION: final readback failure rolls back both files', () => {
    const dir = tmpDir('fotmob-ret-readback-');
    try {
        const rawBody = Buffer.from('raw html', 'utf8');
        const manifest = makeValidManifest({ body_sha256: sha256Bytes(rawBody), body_byte_size: rawBody.length });
        const fsImpl = failingFs(fs, 'readback', {});
        assert.throws(
            () => writeCapturePair({
                rawBody,
                manifest,
                rawFileName: '1-4506263.html',
                manifestFileName: '1-4506263.manifest.json',
                pairDir: dir,
                fsImpl,
            }),
            (e) => e.code === 'SAFETY_ERROR'
        );
        assert.deepEqual(fs.readdirSync(dir), []);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('RETENTION: identical pair is idempotent; different content never overwritten', () => {
    const dir = tmpDir('fotmob-ret-idem-');
    try {
        const rawBody = Buffer.from('raw html', 'utf8');
        const manifest = makeValidManifest({ body_sha256: sha256Bytes(rawBody), body_byte_size: rawBody.length });
        const first = writeCapturePair({
            rawBody,
            manifest,
            rawFileName: '1-4506263.html',
            manifestFileName: '1-4506263.manifest.json',
            pairDir: dir,
        });
        assert.equal(first.idempotent, false);
        const second = writeCapturePair({
            rawBody,
            manifest,
            rawFileName: '1-4506263.html',
            manifestFileName: '1-4506263.manifest.json',
            pairDir: dir,
        });
        assert.equal(second.idempotent, true);

        const differentBody = Buffer.from('different raw html', 'utf8');
        assert.throws(
            () => writeCapturePair({
                rawBody: differentBody,
                manifest: makeValidManifest({ body_sha256: sha256Bytes(differentBody), body_byte_size: differentBody.length }),
                rawFileName: '1-4506263.html',
                manifestFileName: '1-4506263.manifest.json',
                pairDir: dir,
            }),
            (e) => e.code === 'SAFETY_ERROR' && /different content/.test(e.message)
        );
        // Original content untouched.
        assert.equal(sha256Bytes(fs.readFileSync(path.join(dir, '1-4506263.html'))), sha256Bytes(rawBody));
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('RETENTION: manifest never contains secrets', () => {
    const dir = tmpDir('fotmob-ret-secrets-');
    try {
        const rawBody = Buffer.from('raw html', 'utf8');
        const manifest = makeValidManifest({ body_sha256: sha256Bytes(rawBody), body_byte_size: rawBody.length });
        writeCapturePair({
            rawBody,
            manifest,
            rawFileName: '1-4506263.html',
            manifestFileName: '1-4506263.manifest.json',
            pairDir: dir,
        });
        const written = fs.readFileSync(path.join(dir, '1-4506263.manifest.json'), 'utf8').toLowerCase();
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
        const rawBody = Buffer.from('raw html', 'utf8');
        const manifest = makeValidManifest({ body_sha256: sha256Bytes(rawBody), body_byte_size: rawBody.length });
        delete manifest.source_match_id;
        assert.throws(
            () => writeCapturePair({
                rawBody,
                manifest,
                rawFileName: '1-4506263.html',
                manifestFileName: '1-4506263.manifest.json',
                pairDir: dir,
            }),
            (e) => e.code === 'SAFETY_ERROR' && /manifest validation failed/.test(e.message)
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('RETENTION: run state round-trips and binds plan SHA', () => {
    const dir = tmpDir('fotmob-ret-runstate-');
    try {
        const plan = { plan_business_sha256: 'b'.repeat(64), source_artifact_sha256: 'c'.repeat(64), selected_candidate_count: 1 };
        const state = defaultRunState(plan, {
            runId: 'run-state-test',
            authorizationId: 'auth-test',
            maxRequests: 3,
            delayMs: 60000,
            startedAt: FIXED_CLOCK,
        });
        writeRunState(dir, state);
        const loaded = readRunState(dir);
        assert.equal(loaded.plan_sha256, plan.plan_business_sha256);
        assert.equal(loaded.authorization_id, 'auth-test');
        assert.equal(loaded.schema_version, 'fotmob-detail-capture-run-state/v1');
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

// ─────────────────────────────────────────────────────────────
// G. REPLAY
// ─────────────────────────────────────────────────────────────

function buildCapturedRun(dir, { pageContent } = {}) {
    const rawBody = Buffer.from(makePageHtml({
        matchId: 4506263,
        homeTeam: 'Manchester United',
        awayTeam: 'Fulham',
        kickoffAt: '2024-08-16T19:00:00Z',
        content: pageContent,
    }), 'utf8');
    const captures = path.join(dir, 'captures');
    fs.mkdirSync(captures, { recursive: true });
    const manifest = makeValidManifest({
        body_sha256: sha256Bytes(rawBody),
        body_byte_size: rawBody.length,
        stable_raw_payload_sha256: 'e'.repeat(64),
    });
    fs.writeFileSync(path.join(captures, '1-4506263.html'), rawBody);
    fs.writeFileSync(path.join(captures, '1-4506263.manifest.json'), JSON.stringify(manifest, null, 2));
    return { rawBody, manifest, captures };
}

const REPLAY_PARSER = {
    extractFromHtml: NextDataParser.extractFromHtml,
    transformToApiFormat: NextDataParser.transformToApiFormat,
    parseFotMobRaw: FotMobRawParser.parseFotMobRaw,
};

test('REPLAY: fully offline replay produces a valid deterministic artifact', () => {
    const dir = tmpDir('fotmob-replay-ok-');
    try {
        buildCapturedRun(dir);
        const plan = {
            candidates: [{
                candidate_id: '4506263',
                source_match_id: '4506263',
                competition: 'Premier League',
                season: '2024/2025',
                home_team: 'Manchester United',
                away_team: 'Fulham',
                kickoff_at: '2024-08-16T19:00:00Z',
            }],
        };
        const result = replayCapturePair({
            runDir: dir,
            ordinal: 1,
            sourceMatchId: '4506263',
            plan,
            parser: REPLAY_PARSER,
            parsedAt: FIXED_CLOCK,
            parserCodeRevision: TEST_REVISION,
        });
        const artifact = result.artifact;
        assert.equal(artifact.schema_version, 'fotmob-match-detail-artifact/v1');
        assert.equal(artifact.source_match_id, '4506263');
        assert.equal(artifact.observed_identity.observed_match_id, '4506263');
        assert.match(artifact.raw_file_sha256, /^[0-9a-f]{64}$/);
        assert.match(artifact.structured_payload_sha256, /^[0-9a-f]{64}$/);
        assert.ok(artifact.content.match);
        assert.equal(String(artifact.content.match.externalId), '4506263');
        // Deterministic: replaying again yields the same structured hash.
        const again = replayCapturePair({
            runDir: dir,
            ordinal: 1,
            sourceMatchId: '4506263',
            plan,
            parser: REPLAY_PARSER,
            parsedAt: FIXED_CLOCK,
            parserCodeRevision: TEST_REVISION,
        });
        assert.equal(again.artifact.structured_payload_sha256, artifact.structured_payload_sha256);
        assert.equal(again.artifactSha256, result.artifactSha256);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('REPLAY: raw/manifest hash mismatch rejected', () => {
    const dir = tmpDir('fotmob-replay-rawhash-');
    try {
        const { rawBody, manifest } = buildCapturedRun(dir);
        // Corrupt the raw file so its hash no longer matches the manifest.
        fs.writeFileSync(path.join(dir, 'captures', '1-4506263.html'), Buffer.from('tampered', 'utf8'));
        assert.throws(
            () => replayCapturePair({
                runDir: dir,
                ordinal: 1,
                sourceMatchId: '4506263',
                plan: { candidates: [] },
                parser: REPLAY_PARSER,
                parsedAt: FIXED_CLOCK,
                parserCodeRevision: TEST_REVISION,
            }),
            (e) => e.code === 'SAFETY_ERROR' && /raw hash does not match/.test(e.message)
        );
        assert.ok(rawBody.length > 0 && manifest.body_sha256.length === 64);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('REPLAY: manifest validation failure rejected', () => {
    const dir = tmpDir('fotmob-replay-manifest-');
    try {
        buildCapturedRun(dir);
        const manifestPath = path.join(dir, 'captures', '1-4506263.manifest.json');
        const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
        delete manifest.collector_code_revision;
        fs.writeFileSync(manifestPath, JSON.stringify(manifest));
        assert.throws(
            () => replayCapturePair({
                runDir: dir,
                ordinal: 1,
                sourceMatchId: '4506263',
                plan: { candidates: [] },
                parser: REPLAY_PARSER,
                parsedAt: FIXED_CLOCK,
                parserCodeRevision: TEST_REVISION,
            }),
            (e) => e.code === 'SAFETY_ERROR' && /manifest invalid/.test(e.message)
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('REPLAY: parser failure produces no artifact', () => {
    const dir = tmpDir('fotmob-replay-parsefail-');
    try {
        buildCapturedRun(dir);
        const parser = {
            extractFromHtml: () => ({ success: false, error: 'NO_NEXT_DATA:test' }),
            transformToApiFormat: () => null,
            parseFotMobRaw: () => ({ ok: false, error: 'x' }),
        };
        assert.throws(
            () => replayCapturePair({
                runDir: dir,
                ordinal: 1,
                sourceMatchId: '4506263',
                plan: { candidates: [] },
                parser,
                parsedAt: FIXED_CLOCK,
                parserCodeRevision: TEST_REVISION,
            }),
            (e) => e.code === 'REPLAY_PARSE_ERROR'
        );
        // No detail artifact was written anywhere.
        assert.ok(!fs.existsSync(path.join(dir, 'replay')));
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('REPLAY: atomic write, symlink rejection, no overwrite of different content', () => {
    const dir = tmpDir('fotmob-replay-write-');
    try {
        buildCapturedRun(dir);
        const plan = {
            candidates: [{
                candidate_id: '4506263',
                source_match_id: '4506263',
                competition: 'Premier League',
                season: '2024/2025',
                home_team: 'Manchester United',
                away_team: 'Fulham',
                kickoff_at: '2024-08-16T19:00:00Z',
            }],
        };
        const replayDir = path.join(dir, 'replay');
        fs.mkdirSync(replayDir, { recursive: true });
        const result = replayCapturePair({
            runDir: dir,
            ordinal: 1,
            sourceMatchId: '4506263',
            plan,
            parser: REPLAY_PARSER,
            parsedAt: FIXED_CLOCK,
            parserCodeRevision: TEST_REVISION,
        });
        const first = writeDetailArtifact({
            artifact: result.artifact,
            replayDir,
            ordinal: 1,
            sourceMatchId: '4506263',
        });
        assert.ok(fs.existsSync(first.artifactPath));

        // Idempotent rewrite of identical bytes.
        const second = writeDetailArtifact({
            artifact: result.artifact,
            replayDir,
            ordinal: 1,
            sourceMatchId: '4506263',
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
                sourceMatchId: '4506263',
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
                sourceMatchId: '4506263',
            }),
            (e) => e.code === 'SAFETY_ERROR'
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('RETENTION: checkCompletedPair distinguishes complete/partial/mismatch', () => {
    const dir = tmpDir('fotmob-ret-check-');
    try {
        buildCapturedRun(dir);
        const complete = checkCompletedPair({ runDir: dir, ordinal: 1, sourceMatchId: '4506263' });
        assert.equal(complete.state, 'complete');
        assert.equal(complete.completed, true);

        // Remove manifest → partial.
        fs.unlinkSync(path.join(dir, 'captures', '1-4506263.manifest.json'));
        const partial = checkCompletedPair({ runDir: dir, ordinal: 1, sourceMatchId: '4506263' });
        assert.equal(partial.state, 'partial');

        // Add manifest back with wrong hash → mismatch.
        const rawBody = fs.readFileSync(path.join(dir, 'captures', '1-4506263.html'));
        const manifest = makeValidManifest({ body_sha256: '0'.repeat(64), body_byte_size: rawBody.length });
        fs.writeFileSync(path.join(dir, 'captures', '1-4506263.manifest.json'), JSON.stringify(manifest));
        const mismatch = checkCompletedPair({ runDir: dir, ordinal: 1, sourceMatchId: '4506263' });
        assert.equal(mismatch.state, 'mismatch');
        assert.equal(mismatch.completed, false);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('RETENTION: run summary proves zero database writes and counts real fotmob requests', () => {
    const dir = tmpDir('fotmob-ret-summary-');
    try {
        const runState = {
            schema_version: 'fotmob-detail-capture-run-state/v1',
            run_id: 'run-summary',
            plan_sha256: 'b'.repeat(64),
            source_artifact_sha256: 'c'.repeat(64),
            authorization_id: 'auth-test',
            status: 'complete',
            stopped_at_ordinal: null,
            stop_reason: null,
            network_requests_made: 3,
            real_fotmob_network_requests: 3,
            completed_ordinals: [1, 2, 3],
        };
        const summary = buildRunSummary(runState, { selected_candidate_count: 3 }, [1, 2, 3]);
        assert.equal(summary.schema_version, 'fotmob-detail-capture-run-summary/v1');
        assert.equal(summary.database_writes, 0);
        assert.equal(summary.network_requests_made, 3);
        assert.equal(summary.real_fotmob_network_requests, 3);
        assert.deepEqual(summary.completed_ordinals, [1, 2, 3]);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});
