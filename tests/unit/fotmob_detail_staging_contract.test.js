/* eslint-disable complexity, max-lines */
'use strict';

// lifecycle: permanent
// Contract module tests for FotMobDetailStagingContract.js.
// Fully offline: no network (structurally forbidden), no database.

global.fetch = () => {
    throw new Error('REAL_NETWORK_FORBIDDEN_IN_TEST');
};

const { test } = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');

const {
    validateSourceIndex,
    validateObservation,
    validateStagingArtifact,
    computeStagingArtifactBusinessHash,
    DOUBLE_BOUND_FIELD_PAIRS,
    ACTUAL_DOUBLE_BOUND_FIELDS,
    uuidV5,
    deterministicObservationId,
    sameInstant,
    isStrictAbsoluteTimestamp,
    TERMINAL_STATES,
    ERROR_CODES,
    VALIDATION_LAYERS,
    SECTIONS,
} = require('../../src/infrastructure/fotmob/FotMobDetailStagingContract');
const {
    computeStableCapturePayloadSha256,
    computeCaptureManifestSelfHash,
} = require('../../src/infrastructure/fotmob/FotMobDetailCaptureContract');
const {
    buildPair,
    buildPayload,
    buildManifest,
    buildSourceIndex,
    sourceIndexEntry,
} = require('../helpers/fotmobDetailStagingFixtures');

const REPO_ROOT = path.resolve(__dirname, '..', '..');

function pairToValidationArgs(pair) {
    return {
        payload: pair.payload,
        manifest: pair.manifest,
        payloadBytes: pair.payloadBytes,
    };
}

// ── A. contract basics ───────────────────────────────────────

test('A1: legal minimal payload+manifest passes L1-L8 and yields ACCEPTED_NEW-ready state', () => {
    const pair = buildPair();
    const validation = validateObservation(pairToValidationArgs(pair));
    assert.strictEqual(validation.ok, true);
    assert.strictEqual(validation.terminal_state, null); // ACCEPTED_* decided by store
    assert.strictEqual(validation.quarantine_status, 'not_quarantined');
    assert.strictEqual(validation.layers[VALIDATION_LAYERS.L4_PROVENANCE_HASH_CHAIN].ok, true);
});

test('A2: legal complete payload+manifest (all five sections) builds a valid artifact', () => {
    const pair = buildPair();
    const validation = validateObservation(pairToValidationArgs(pair));
    assert.strictEqual(validation.ok, true);
    assert.deepStrictEqual(validation.coverage.events, {
        present: true,
        count: 2,
        version: 'fotmob-match-detail-parsed/v1',
    });
    assert.deepStrictEqual(validation.coverage.stats.periods, ['All', 'FirstHalf', 'SecondHalf']);
    assert.strictEqual(validation.coverage.player_stats.count, 2);
    assert.strictEqual(validation.coverage.shotmap.shots, 1);
    assert.deepStrictEqual(validation.coverage.lineup.sides.sort(), ['away', 'home']);
});

test('A3: schema error (wrong schema_version) → REJECTED_SCHEMA_UNKNOWN E002', () => {
    const pair = buildPair();
    const tampered = {
        ...pair.payload,
        schema_version: 'not-a-capture-payload/v9',
    };
    const validation = validateObservation({
        payload: tampered,
        manifest: pair.manifest,
        payloadBytes: pair.payloadBytes,
    });
    assert.strictEqual(validation.ok, false);
    assert.strictEqual(validation.terminal_state, TERMINAL_STATES.REJECTED_SCHEMA_UNKNOWN);
    assert.strictEqual(validation.error_code, ERROR_CODES.E002);
});

test('A4: observed ID missing → E007 identity conflict', () => {
    const pair = buildPair({ observed: { observed_match_id: '' } });
    const validation = validateObservation(pairToValidationArgs(pair));
    assert.strictEqual(validation.ok, false);
    assert.strictEqual(validation.terminal_state, TERMINAL_STATES.REJECTED_IDENTITY_INCONSISTENT);
    assert.strictEqual(validation.error_code, ERROR_CODES.E007);
});

test('A5: observed ID conflicts with source_match_id → REJECTED_IDENTITY_INCONSISTENT E007', () => {
    const pair = buildPair({
        source_match_id: '3901023',
        observed: { observed_match_id: '9999999' },
    });
    const validation = validateObservation(pairToValidationArgs(pair));
    assert.strictEqual(validation.terminal_state, TERMINAL_STATES.REJECTED_IDENTITY_INCONSISTENT);
    assert.strictEqual(validation.error_code, ERROR_CODES.E007);
});

test('A6: response-derived=false → REJECTED_PROVENANCE_BROKEN E010', () => {
    const pair = buildPair({
        observed: { observed_match_id_is_response_derived: false },
    });
    const validation = validateObservation(pairToValidationArgs(pair));
    assert.strictEqual(validation.terminal_state, TERMINAL_STATES.REJECTED_PROVENANCE_BROKEN);
    assert.strictEqual(validation.error_code, ERROR_CODES.E010);
});

test('A7: untrusted observed ID source → REJECTED_PROVENANCE_BROKEN E010', () => {
    const pair = buildPair({
        observed: { observed_match_id_source: 'request.url' },
    });
    const validation = validateObservation(pairToValidationArgs(pair));
    assert.strictEqual(validation.terminal_state, TERMINAL_STATES.REJECTED_PROVENANCE_BROKEN);
    assert.strictEqual(validation.error_code, ERROR_CODES.E010);
});

test('A8: provider/competition/season conflicts → REJECTED_SCHEMA_UNKNOWN E003/E004/E006', () => {
    const pair = buildPair();
    const p = validateObservation({
        ...pairToValidationArgs(pair),
        payload: { ...pair.payload, source_provider: 'Opta' },
    });
    assert.strictEqual(p.terminal_state, TERMINAL_STATES.REJECTED_SCHEMA_UNKNOWN);
    assert.strictEqual(p.error_code, ERROR_CODES.E003);
    const c = validateObservation({
        ...pairToValidationArgs(pair),
        payload: { ...pair.payload, competition: 'Serie A' },
    });
    assert.strictEqual(c.error_code, ERROR_CODES.E004);
    const s = validateObservation({
        ...pairToValidationArgs(pair),
        payload: { ...pair.payload, season: '2022' },
    });
    assert.strictEqual(s.error_code, ERROR_CODES.E006);
});

test('A9: payload file SHA wrong (physical bytes differ) → E008', () => {
    const pair = buildPair();
    const modifiedBytes = Buffer.from(JSON.stringify(pair.payload, null, 2) + '\n\n', 'utf8');
    const validation = validateObservation({
        payload: pair.payload,
        manifest: pair.manifest,
        payloadBytes: modifiedBytes,
    });
    assert.strictEqual(validation.ok, false);
    assert.strictEqual(validation.terminal_state, TERMINAL_STATES.REJECTED_PROVENANCE_BROKEN);
    assert.strictEqual(validation.error_code, ERROR_CODES.E008);
});

test('A10: payload byte size change (trailing whitespace) fails closed → E008', () => {
    const pair = buildPair();
    const resized = Buffer.from(JSON.stringify(pair.payload) + '  ', 'utf8');
    const validation = validateObservation({
        payload: pair.payload,
        manifest: pair.manifest,
        payloadBytes: resized,
    });
    assert.strictEqual(validation.ok, false);
    assert.strictEqual(validation.error_code, ERROR_CODES.E008);
});

test('A11: payload business hash wrong (stable_payload_sha256 tampered) → E008', () => {
    const pair = buildPair();
    const tampered = {
        ...pair.payload,
        stable_payload_sha256: '0'.repeat(64),
    };
    const validation = validateObservation({
        payload: tampered,
        manifest: pair.manifest,
        payloadBytes: pair.payloadBytes,
    });
    assert.strictEqual(validation.terminal_state, TERMINAL_STATES.REJECTED_PROVENANCE_BROKEN);
    assert.strictEqual(validation.error_code, ERROR_CODES.E008);
});

test('A12: manifest self-hash wrong → E009', () => {
    const pair = buildPair();
    const tamperedManifest = {
        ...pair.manifest,
        delay_ms: pair.manifest.delay_ms - 1,
    };
    const validation = validateObservation({
        payload: pair.payload,
        manifest: tamperedManifest,
        payloadBytes: pair.payloadBytes,
    });
    assert.strictEqual(validation.ok, false);
    assert.strictEqual(validation.error_code, ERROR_CODES.E009);
});

test('A13: source index with bad archive sha / duplicate ids fails closed', () => {
    const bad = validateSourceIndex({
        schema_version: 'fotmob-detail-source-index/v1',
        source_provider: 'FotMob',
        archive_bindings: { one_match: { sha256: 'nope' } },
        entries: [{ source_match_id: '1', payload_file: '/tmp/a', manifest_file: '/tmp/b' }],
    });
    assert.strictEqual(bad.ok, false);
    const dup = validateSourceIndex({
        schema_version: 'fotmob-detail-source-index/v1',
        source_provider: 'FotMob',
        archive_bindings: {
            one_match: {
                sha256: 'e3679262ff1f8ca8154a1da2aa79f28c03f622653496ec7195e4c5b91ec90120',
            },
        },
        entries: [
            {
                source_match_id: '3901023',
                payload_file: '/tmp/a',
                manifest_file: '/tmp/b',
            },
            {
                source_match_id: '3901023',
                payload_file: '/tmp/c',
                manifest_file: '/tmp/d',
            },
        ],
    });
    assert.strictEqual(dup.ok, false);
});

// ── B. hashing (ERRATA_4) ────────────────────────────────────

test('B14: contract reuses computeStableCapturePayloadSha256 directly (import, not copy)', () => {
    const pair = buildPair();
    const direct = computeStableCapturePayloadSha256(pair.payload);
    assert.strictEqual(direct, pair.payload.stable_payload_sha256);
    const validation = validateObservation(pairToValidationArgs(pair));
    assert.strictEqual(validation.checks.stable_payload_sha256, direct);
});

test('B15: numeric-string object keys (player_stats style) verify via the real pipeline hash', () => {
    // Insert the numeric player-id keys in a scrambled order; V8 enumerates
    // them in dict-hash-bucket order — only the pipeline hashing matches.
    const normalized = {
        match_external_id: '3901023',
        home_team: { id: 10204, name: 'AFC Bournemouth', score: 2 },
        away_team: { id: 10261, name: 'Leicester City', score: 1 },
        player_stats: {
            1353551: {
                id: 1353551,
                name: 'Sammy Braybrooke',
                shirtNumber: '44',
                isGoalkeeper: false,
                teamId: 10204,
                teamName: 'AFC Bournemouth',
            },
            1171140: {
                id: 1171140,
                name: 'Jaidon Anthony',
                shirtNumber: '32',
                isGoalkeeper: false,
                teamId: 10204,
                teamName: 'AFC Bournemouth',
                positionId: 38,
                usualPosition: 'Forward',
                funFacts: ['first goal'],
            },
            176186: {
                id: 176186,
                name: 'Neto',
                shirtNumber: '13',
                isGoalkeeper: true,
                teamId: 10204,
                teamName: 'AFC Bournemouth',
                positionId: 11,
                usualPosition: 'Goalkeeper',
            },
            160447: {
                id: 160447,
                name: 'Adam Smith',
                shirtNumber: '15',
                isGoalkeeper: false,
                teamId: 10204,
                teamName: 'AFC Bournemouth',
                positionId: 38,
                usualPosition: 'Defender',
            },
            194323: {
                id: 194323,
                name: 'Ryan Fredericks',
                shirtNumber: '2',
                isGoalkeeper: false,
                teamId: 10204,
                teamName: 'AFC Bournemouth',
                positionId: 32,
                usualPosition: 'Defender',
            },
        },
        events: [
            {
                id: 1,
                minute: 10,
                homeScore: 0,
                awayScore: 0,
                event_kind: 'real_event',
            },
        ],
        stats: [{ key: 'shots', homeValue: 15, awayValue: 9, period: 'All' }],
        lineup: {
            home: { coach: null, starters: [], subs: [] },
            away: { coach: null, starters: [], subs: [] },
        },
        shotmap: { shots: [] },
    };
    const pair = buildPair({ normalized });
    const validation = validateObservation(pairToValidationArgs(pair));
    assert.strictEqual(validation.ok, true, JSON.stringify(validation.errors));
});

test('B16: player_stats-style ID keys present in sections verbatim after conversion', () => {
    const normalized = {
        match_external_id: '3901023',
        home_team: { id: 10204, name: 'AFC Bournemouth', score: 0 },
        away_team: { id: 10261, name: 'Leicester City', score: 0 },
        player_stats: {
            109222: {
                id: 109222,
                name: 'Player X',
                shirtNumber: '9',
                isGoalkeeper: false,
            },
            1021586: {
                id: 1021586,
                name: 'Player Y',
                shirtNumber: '21',
                isGoalkeeper: false,
            },
        },
        events: [
            {
                id: 5,
                minute: 1,
                homeScore: 0,
                awayScore: 0,
                event_kind: 'real_event',
            },
        ],
        stats: [{ key: 'shots', homeValue: 1, awayValue: 1, period: 'All' }],
        lineup: {
            home: { coach: null, starters: [], subs: [] },
            away: { coach: null, starters: [], subs: [] },
        },
        shotmap: { shots: [] },
    };
    const pair = buildPair({ normalized });
    const { convertPair } = require('../../src/infrastructure/fotmob/FotMobDetailStagingConverter');
    const result = convertPair({ ...pairToValidationArgs(pair) });
    assert.strictEqual(result.ok, true);
    assert.deepStrictEqual(Object.keys(result.artifact.sections.player_stats.json).sort(), ['1021586', '109222']);
});

test('B17: same object content in different key insertion order → identical capture hash', () => {
    const first = buildPayload();
    const reversed = buildPayload({
        normalized: {
            match_external_id: '3901023',
            home_team: { id: 10204, name: 'AFC Bournemouth', score: 2 },
            away_team: { id: 10261, name: 'Leicester City', score: 1 },
            events: [
                {
                    id: 9434327,
                    minute: 10,
                    homeScore: 0,
                    awayScore: 0,
                    event_kind: 'real_event',
                },
            ],
            stats: [{ key: 'shots', homeValue: 15, awayValue: 9, period: 'All' }],
            lineup: {
                home: { coach: null, starters: [], subs: [] },
                away: { coach: null, starters: [], subs: [] },
            },
            shotmap: { shots: [] },
            player_stats: {},
        },
    });
    const { stable_payload_sha256: h1 } = first;
    // Rebuild with a different insertion order of the same keys.
    const reordered = buildPayload();
    const reorderedNorm = {};
    const keys = Object.keys(reordered.normalized);
    for (let i = keys.length - 1; i >= 0; i -= 1) {
        reorderedNorm[keys[i]] = reordered.normalized[keys[i]];
    }
    reordered.normalized = reorderedNorm;
    reordered.stable_payload_sha256 = computeStableCapturePayloadSha256(reordered);
    assert.strictEqual(reordered.stable_payload_sha256, h1);
});

test('B18: no duplicated canonical-JSON hash implementation exists in staging contract source', () => {
    const source = fs.readFileSync(
        path.join(REPO_ROOT, 'src/infrastructure/fotmob/FotMobDetailStagingContract.js'),
        'utf8'
    );
    // The module must reuse the pipeline helper, never re-implement
    // canonicalization or hashing (quote style is formatter-owned).
    assert.match(source, /require\(\s*['"]\.\/FotMobDetailCaptureContract['"]\s*\)/);
    assert.doesNotMatch(source, /function\s+canonicalizeJson/);
    assert.doesNotMatch(source, /function\s+sha256CanonicalJson/);
    assert.doesNotMatch(source, /Object\.keys\([^)]*\)\.sort\(\).*createHash/s);
});

test('B19: generated_at / observation_id never enter the business hash', () => {
    const pair = buildPair();
    const { convertPair } = require('../../src/infrastructure/fotmob/FotMobDetailStagingConverter');
    const result = convertPair({ ...pairToValidationArgs(pair) });
    assert.strictEqual(result.ok, true);
    const artifact = result.artifact;
    const mutated = {
        ...artifact,
        generated_at: '2099-01-01T00:00:00.000Z',
        observation_id: 'ffffffff-ffff-ffff-ffff-ffffffffffff',
    };
    assert.strictEqual(computeStagingArtifactBusinessHash(mutated), artifact.business_hash);
});

// ── D. optional section (ERRATA_2) ───────────────────────────

test('D28/D29: legal payload missing an optional section from the start (correct hash chain) is accepted and recorded absent', () => {
    const normalized = {
        match_external_id: '3901023',
        home_team: { id: 10204, name: 'AFC Bournemouth', score: 0 },
        away_team: { id: 10261, name: 'Leicester City', score: 0 },
        events: [
            {
                id: 1,
                minute: 5,
                homeScore: 0,
                awayScore: 0,
                event_kind: 'real_event',
            },
        ],
        lineup: {
            home: { coach: null, starters: [], subs: [] },
            away: { coach: null, starters: [], subs: [] },
        },
        stats: [{ key: 'shots', homeValue: 1, awayValue: 0, period: 'All' }],
        // shotmap absent from the very start — legally captured without it.
    };
    const pair = buildPair({ normalized });
    const validation = validateObservation(pairToValidationArgs(pair));
    assert.strictEqual(validation.ok, true, JSON.stringify(validation.errors));
    assert.strictEqual(validation.coverage.shotmap.present, false);
    assert.strictEqual(validation.coverage.events.present, true);
    // conversion produces artifact with null section json
    const { convertPair } = require('../../src/infrastructure/fotmob/FotMobDetailStagingConverter');
    const result = convertPair({ ...pairToValidationArgs(pair) });
    assert.strictEqual(result.ok, true);
    assert.strictEqual(result.artifact.sections.shotmap.json, null);
    assert.strictEqual(result.artifact.business_hash.length, 64);
});

test('D30: physical removal of a section without re-signing hashes is caught as tampering → E008', () => {
    const pair = buildPair();
    const tampered = { ...pair.payload };
    tampered.normalized = { ...pair.payload.normalized };
    delete tampered.normalized.shotmap;
    // stable_payload_sha256 NOT updated — hash chain must fail.
    const validation = validateObservation({
        payload: tampered,
        manifest: pair.manifest,
        payloadBytes: pair.payloadBytes,
    });
    assert.strictEqual(validation.ok, false);
    assert.strictEqual(validation.error_code, ERROR_CODES.E008);
});

test('D31: required block missing (normalized absent) fails closed → E002', () => {
    const pair = buildPair();
    const validation = validateObservation({
        payload: { ...pair.payload, normalized: undefined },
        manifest: pair.manifest,
        payloadBytes: pair.payloadBytes,
    });
    assert.strictEqual(validation.ok, false);
    assert.strictEqual(validation.terminal_state, TERMINAL_STATES.REJECTED_SCHEMA_UNKNOWN);
});

test('D31b: parser-injected marker_event entries (no id by design) pass L6', () => {
    // Real capture data: every match carries four marker_event minute markers
    // (AddedTime 45/90, Half 45/90) with NO id, NO synthetic_event_key. They
    // are parser-injected structure, not id-bearing events — id absence is a
    // legal variant, not an E011 quarantine trigger.
    const pair = buildPair({
        source_match_id: '3900932',
        normalized: {
            match_external_id: '3900932',
            home_team: { id: 1, name: 'AFC Bournemouth', score: 0 },
            away_team: { id: 2, name: 'Leicester City', score: 0 },
            events: [
                { id: 1, minute: 10, homeScore: 0, awayScore: 0, event_kind: 'real_event' },
                {
                    id: null,
                    minute: 45,
                    event_kind: 'marker_event',
                    type: 'AddedTime',
                    playerName: null,
                    synthetic_event_key: null,
                    source_has_native_id: false,
                },
                {
                    id: null,
                    minute: 45,
                    event_kind: 'marker_event',
                    type: 'Half',
                    playerName: null,
                    synthetic_event_key: null,
                    source_has_native_id: false,
                },
                {
                    id: null,
                    minute: 90,
                    event_kind: 'marker_event',
                    type: 'AddedTime',
                    playerName: null,
                    synthetic_event_key: null,
                    source_has_native_id: false,
                },
                {
                    id: null,
                    minute: 90,
                    event_kind: 'marker_event',
                    type: 'Half',
                    playerName: null,
                    synthetic_event_key: null,
                    source_has_native_id: false,
                },
                { id: 2, minute: 40, homeScore: 0, awayScore: 1, event_kind: 'real_event', card: 'Yellow' },
            ],
            stats: [{ key: 'shots', homeValue: 0, awayValue: 0, period: 'All' }],
            lineup: {
                home: { coach: null, starters: [], subs: [] },
                away: { coach: null, starters: [], subs: [] },
            },
            shotmap: { shots: [] },
        },
    });
    const validation = validateObservation({
        payload: pair.payload,
        manifest: pair.manifest,
        payloadBytes: pair.payloadBytes,
    });
    assert.strictEqual(validation.ok, true, validation.errors.map(e => e.message).join('; '));
    assert.strictEqual(validation.quarantine_status, 'not_quarantined');
});

// ── F. data domain / dependencies ────────────────────────────

test('F40/F41/F42: converter and contract modules import no fetcher, no DB client, no scripts/ops', () => {
    for (const rel of [
        'src/infrastructure/fotmob/FotMobDetailStagingConverter.js',
        'src/infrastructure/fotmob/FotMobDetailStagingContract.js',
        'src/infrastructure/fotmob/FotMobDetailStagingRetention.js',
    ]) {
        const source = fs.readFileSync(path.join(REPO_ROOT, rel), 'utf8');
        assert.doesNotMatch(
            source,
            /FotMobRawDetailFetcher|NextDataParser|FotMobDetailCapturePipeline|playwright/i,
            `${rel} must not import the network fetcher/parser`
        );
        assert.doesNotMatch(
            source,
            /require\(['"]pg['"]\)|require\(['"]ioredis['"]\)|node-postgres|DATABASE_URL|PGHOST/i,
            `${rel} must not import a DB client`
        );
        assert.doesNotMatch(source, /scripts\/ops/, `${rel} must not reference scripts/ops`);
        // Fuzzy matching would require an import; the word itself may appear
        // in documentation comments, so only the import is forbidden.
        assert.doesNotMatch(source, /require\(['"]fuzzball['"]\)/, `${rel} must not import fuzzball`);
        assert.doesNotMatch(source, /\.similarity\(|fuzzy_match/i, `${rel} must not contain fuzzy matching calls`);
    }
});

test('F43: artifact sections contain only the five allowlisted sections, no odds fields', () => {
    const pair = buildPair();
    const { convertPair } = require('../../src/infrastructure/fotmob/FotMobDetailStagingConverter');
    const result = convertPair({ ...pairToValidationArgs(pair) });
    assert.strictEqual(result.ok, true);
    assert.deepStrictEqual(Object.keys(result.artifact.sections).sort(), [...SECTIONS].sort());
    const serialized = JSON.stringify(result.artifact);
    assert.doesNotMatch(serialized, /odds|handicap|asian|over_under|bookmaker/i);
});

test('F44/F45: canonical_match_id defaults to null and an unlinked detail is legal', () => {
    const pair = buildPair();
    const { convertPair } = require('../../src/infrastructure/fotmob/FotMobDetailStagingConverter');
    const result = convertPair({ ...pairToValidationArgs(pair) });
    assert.strictEqual(result.artifact.canonical_match_id, null);
    assert.strictEqual(result.artifact.canonical_link_status, 'UNLINKED_NOT_ATTEMPTED');
    const validation = validateStagingArtifact(result.artifact);
    assert.strictEqual(validation.ok, true, validation.errors.join('; '));
});

test('F46: team comparison is exact case/whitespace fold only (no fuzzy, no aliases)', () => {
    const pair = buildPair({ expected: { home_team: '  AFC   Bournemouth ' } });
    const validation = validateObservation(pairToValidationArgs(pair));
    assert.strictEqual(validation.ok, true, JSON.stringify(validation.errors));
    // Synonym-style rename must fail closed.
    const aliasPair = buildPair({ expected: { home_team: 'Bournemouth AFC' } });
    const aliasValidation = validateObservation(pairToValidationArgs(aliasPair));
    assert.strictEqual(aliasValidation.ok, false);
    assert.strictEqual(aliasValidation.error_code, ERROR_CODES.E007);
});

// ── artifact validation ─────────────────────────────────────

test('artifact validation catches tampered business hash and bad enums', () => {
    const pair = buildPair();
    const { convertPair } = require('../../src/infrastructure/fotmob/FotMobDetailStagingConverter');
    const artifact = convertPair({ ...pairToValidationArgs(pair) }).artifact;
    const tampered = { ...artifact, business_hash: '0'.repeat(64) };
    const v1 = validateStagingArtifact(tampered);
    assert.strictEqual(v1.ok, false);
    const badState = { ...artifact, import_terminal_state: 'INVENTED_STATE' };
    const v2 = validateStagingArtifact(badState);
    assert.strictEqual(v2.ok, false);
    const badLink = { ...artifact, canonical_link_status: 'GUESSED_LINK' };
    const v3 = validateStagingArtifact(badLink);
    assert.strictEqual(v3.ok, false);
});

test('source index helper builds a legal index', () => {
    const index = buildSourceIndex(
        [
            sourceIndexEntry('3901023', '/tmp/pairs/1.payload.json', '/tmp/pairs/1.manifest.json', {
                package: 'ten-match',
                payload_file_sha256: '0'.repeat(64),
                manifest_file_sha256: '1'.repeat(64),
            }),
        ],
        {
            'ten-match': {
                sha256: '0'.repeat(64),
                path: '/tmp/pairs/archive.tar.gz',
                receipt: '/tmp/pairs/receipt.json',
            },
        }
    );
    const validation = validateSourceIndex(index);
    assert.strictEqual(validation.ok, true, validation.errors.join('; '));
    assert.strictEqual(validation.entries.length, 1);
});

test('C20b (P2-2): source index entries missing manifest_file_sha256 are rejected', () => {
    const index = buildSourceIndex(
        [
            sourceIndexEntry('3901023', '/tmp/pairs/1.payload.json', '/tmp/pairs/1.manifest.json', {
                package: 'ten-match',
                payload_file_sha256: '0'.repeat(64),
                manifest_file_sha256: undefined,
            }),
        ],
        {
            'ten-match': {
                sha256: '0'.repeat(64),
                path: '/tmp/pairs/archive.tar.gz',
                receipt: '/tmp/pairs/receipt.json',
            },
        }
    );
    const validation = validateSourceIndex(index);
    assert.strictEqual(validation.ok, false);
    assert.ok(validation.errors.some(e => /manifest_file_sha256/.test(e)), validation.errors.join('; '));
});

// ── FINDING_6: artifact integrity protection (LAYER_A + LAYER_B) ──

function convertedArtifact() {
    const { convertPair } = require('../../src/infrastructure/fotmob/FotMobDetailStagingConverter');
    const pair = buildPair();
    const result = convertPair({
        payload: pair.payload,
        manifest: pair.manifest,
        payloadBytes: pair.payloadBytes,
    });
    assert.strictEqual(result.ok, true);
    return result.artifact;
}

test('I1: untouched artifact passes LAYER_A and LAYER_B (positive control)', () => {
    const artifact = convertedArtifact();
    const validation = validateStagingArtifact(artifact);
    assert.strictEqual(validation.ok, true, validation.errors.join('; '));
    assert.strictEqual(artifact.artifact_integrity_sha256.length, 64);
    assert.strictEqual(
        artifact.generated_at,
        artifact.source_response_received_at,
        'generated_at must equal source_response_received_at'
    );
    assert.match(artifact.generated_at, /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/);
});

test('I2: tampered observation_id fails LAYER_A recomputation', () => {
    const artifact = convertedArtifact();
    artifact.observation_id = artifact.observation_id.replace(/./, '0');
    const validation = validateStagingArtifact(artifact);
    assert.strictEqual(validation.ok, false);
});

test('I3: tampered generated_at (valid ISO, wrong value) is detected', () => {
    const artifact = convertedArtifact();
    artifact.generated_at = '2026-01-01T00:00:00.000Z';
    const validation = validateStagingArtifact(artifact);
    assert.strictEqual(validation.ok, false);
});

test('I4: source_response_received_at diverging from generated_at is detected', () => {
    const artifact = convertedArtifact();
    artifact.source_response_received_at = '2026-01-01T00:00:00.000Z';
    const validation = validateStagingArtifact(artifact);
    assert.strictEqual(validation.ok, false);
});

test('I5: tampered business_hash fails business recomputation', () => {
    const artifact = convertedArtifact();
    artifact.business_hash = '0'.repeat(64);
    const validation = validateStagingArtifact(artifact);
    assert.strictEqual(validation.ok, false);
});

test('I6: tampered stable_payload_sha256 is detected by LAYER_A and the business hash', () => {
    const artifact = convertedArtifact();
    artifact.stable_payload_sha256 = '1'.repeat(64);
    const validation = validateStagingArtifact(artifact);
    assert.strictEqual(validation.ok, false);
});

test('I7: tampered artifact_integrity_sha256 itself is detected', () => {
    const artifact = convertedArtifact();
    artifact.artifact_integrity_sha256 = '2'.repeat(64);
    const validation = validateStagingArtifact(artifact);
    assert.strictEqual(validation.ok, false);
});

test('I8: tampered source_match_id is detected by LAYER_A recomputation', () => {
    const artifact = convertedArtifact();
    artifact.source_match_id = '111111';
    const validation = validateStagingArtifact(artifact);
    assert.strictEqual(validation.ok, false);
});

test('I9: integrity hash covers observation_id and generated_at (not just business fields)', () => {
    const artifact = convertedArtifact();
    const {
        computeStagingArtifactIntegrityHash,
    } = require('../../src/infrastructure/fotmob/FotMobDetailStagingContract');
    const recomputed = computeStagingArtifactIntegrityHash(artifact);
    assert.strictEqual(recomputed, artifact.artifact_integrity_sha256);
    // a change in observation_id must change the integrity hash
    const changed = {
        ...artifact,
        observation_id: artifact.observation_id.replace(/./, '9'),
    };
    assert.notStrictEqual(computeStagingArtifactIntegrityHash(changed), artifact.artifact_integrity_sha256);
});

// ── P1-2: ACTUAL double-binding matrix (Codex review 4863122944 P1-2) ──

test('P1-2 matrix: 16 ACTUAL_DOUBLE_BOUND_FIELDS are declared', () => {
    const { ACTUAL_DOUBLE_BOUND_FIELDS, DOUBLE_BOUND_FIELD_PAIRS } = require('../../src/infrastructure/fotmob/FotMobDetailStagingContract');
    assert.strictEqual(DOUBLE_BOUND_FIELD_PAIRS.length, 16);
    assert.strictEqual(ACTUAL_DOUBLE_BOUND_FIELDS.length, 16);
    const expected = [
        'source_provider', 'source_match_id', 'candidate_id', 'competition',
        'league_id', 'season', 'parser_component', 'parser_version',
        'home_team', 'away_team', 'kickoff_at',
        'observed_match_id', 'observed_match_id_source',
        'observed_match_id_conflict', 'observed_match_id_is_response_derived',
        'stable_payload_sha256',
    ];
    assert.deepStrictEqual([...ACTUAL_DOUBLE_BOUND_FIELDS], expected);
});

// One single-field conflict test per double-bound field. Each conflict
// RE-RECOMPUTES the manifest self-hash (capture_manifest_sha256), proving
// that a re-signed manifest cannot smuggle a disagreement through.
const PAIRS = DOUBLE_BOUND_FIELD_PAIRS;

function pairWithSingleFieldConflict(manifestPath, payloadPath, conflictValue) {
    const pair = buildPair();
    const payloadAt = pPath => {
        const parts = String(pPath).split('.');
        let value = pair.payload;
        for (const part of parts) {
            if (value === null || typeof value !== 'object') return undefined;
            value = value[part];
        }
        return value;
    };
    const original = payloadAt(payloadPath);
    // apply the conflict on the MANIFEST side (payload stays legal)
    const manifest = { ...pair.manifest, [manifestPath]: conflictValue };
    manifest.capture_manifest_sha256 = computeCaptureManifestSelfHash(manifest);
    return { payload: pair.payload, manifest, payloadBytes: pair.payloadBytes, original };
}

for (const [mField, pField] of PAIRS) {
    test(`P1-2 conflict: ${mField} disagrees with payload (${pField}) and is rejected even with a recomputed manifest self-hash`, () => {
        const conflictValue = mField === 'observed_match_id_conflict' ? true : mField === 'observed_match_id_is_response_derived' ? false : 'CONFLICT_VALUE';
        const { payload, manifest, payloadBytes } = pairWithSingleFieldConflict(mField, pField, conflictValue);
        const validation = validateObservation({ payload, manifest, payloadBytes });
        assert.strictEqual(validation.ok, false, `${mField} conflict must be rejected`);
        assert.strictEqual(validation.terminal_state, 'REJECTED_PROVENANCE_BROKEN');
        assert.ok(
            validation.errors.some(e => e.message.includes(`double binding ${mField} disagrees`)),
            JSON.stringify(validation.errors)
        );
    });
}

// ── R1-P1-1: type-strict double binding for boolean fields (Codex round 1)
// ── The OLD code String()-coerced both sides, so boolean `true` and string
// ── `"true"` compared equal — while the artifact writer used `=== true` and
// ── silently wrote `false`. ──────────────────────────────────────────

test('R1-P1-1: payload string "true" for a boolean double-bound field is a type mismatch, not equality', () => {
    const pair = buildPair();
    pair.payload.observed_identity.observed_match_id_is_response_derived = 'true'; // string, not boolean
    pair.payloadBytes = Buffer.from(JSON.stringify(pair.payload, null, 2) + '\n', 'utf8');
    const validation = validateObservation({ payload: pair.payload, manifest: pair.manifest, payloadBytes: pair.payloadBytes });
    assert.strictEqual(validation.ok, false);
    assert.ok(
        validation.errors.some(e => e.message.includes('must be a boolean on both documents')),
        JSON.stringify(validation.errors)
    );
});

test('R1-P1-1: manifest string "true" for a boolean double-bound field is rejected', () => {
    const pair = buildPair();
    const manifest = { ...pair.manifest, observed_match_id_is_response_derived: 'true' };
    manifest.capture_manifest_sha256 = computeCaptureManifestSelfHash(manifest);
    const validation = validateObservation({ payload: pair.payload, manifest, payloadBytes: pair.payloadBytes });
    assert.strictEqual(validation.ok, false);
    assert.ok(
        validation.errors.some(e => e.message.includes('must be a boolean on both documents')),
        JSON.stringify(validation.errors)
    );
});

test('R1-P1-1: manifest string "false" and payload boolean false are still a type mismatch', () => {
    const pair = buildPair();
    const manifest = { ...pair.manifest, observed_match_id_conflict: 'false' };
    manifest.capture_manifest_sha256 = computeCaptureManifestSelfHash(manifest);
    const validation = validateObservation({ payload: pair.payload, manifest, payloadBytes: pair.payloadBytes });
    assert.strictEqual(validation.ok, false);
    assert.ok(
        validation.errors.some(e => e.message.includes('must be a boolean on both documents')),
        JSON.stringify(validation.errors)
    );
});

test('R1-P1-1: genuine booleans on both sides still pass the double binding (no regression)', () => {
    const pair = buildPair();
    const validation = validateObservation({ payload: pair.payload, manifest: pair.manifest, payloadBytes: pair.payloadBytes });
    assert.strictEqual(validation.ok, true, JSON.stringify(validation.errors));
});

test('P1-2: kickoff_at byte-inequality is rejected (nanosecond precision)', () => {
    const pair = buildPair();
    const manifest = {
        ...pair.manifest,
        kickoff_at: '2026-08-04T19:30:00.000001Z', // 1 microsecond off
    };
    manifest.capture_manifest_sha256 = computeCaptureManifestSelfHash(manifest);
    const validation = validateObservation({
        payload: pair.payload,
        manifest,
        payloadBytes: pair.payloadBytes,
    });
    assert.strictEqual(validation.ok, false);
    assert.ok(validation.errors.some(e => e.message.includes('double binding kickoff_at disagrees')));
});

test('P1-2: manifest-only fields are validated but NOT claimed as double-bound', () => {
    const { ACTUAL_DOUBLE_BOUND_FIELDS } = require('../../src/infrastructure/fotmob/FotMobDetailStagingContract');
    for (const singleSide of ['parser_output_contract_version', 'capture_run_id', 'authorization_id', 'collector_code_revision']) {
        assert.ok(!ACTUAL_DOUBLE_BOUND_FIELDS.includes(singleSide), `${singleSide} must not be claimed double-bound`);
    }
    // capture_run_id empty -> rejected (C-class presence check)
    const pair = buildPair();
    const manifest = { ...pair.manifest, capture_run_id: '' };
    manifest.capture_manifest_sha256 = computeCaptureManifestSelfHash(manifest);
    const validation = validateObservation({ payload: pair.payload, manifest, payloadBytes: pair.payloadBytes });
    assert.strictEqual(validation.ok, false);
    assert.ok(validation.errors.some(e => e.message.includes('capture_run_id missing')));
});

// ── P2-3: RFC 4122 UUIDv5 + strict timestamp binding (Codex review
// ── 4863122944 P2-3) ─────────────────────────────────────────────────

test('P2-3: UUIDv5 matches the official RFC 4122 test vector (DNS namespace, www.example.com)', () => {
    const { uuidV5 } = require('../../src/infrastructure/fotmob/FotMobDetailStagingContract');
    // RFC 4122 Appendix B: UUIDv5(DNS, "www.example.com") =
    // 2ed6657d-e927-568b-95e1-2665a8aea6a2
    assert.strictEqual(
        uuidV5('6ba7b810-9dad-11d1-80b4-00c04fd430c8', 'www.example.com'),
        '2ed6657d-e927-568b-95e1-2665a8aea6a2'
    );
});

test('P2-3: deterministicObservationId is deterministic and input-sensitive', () => {
    const { deterministicObservationId } = require('../../src/infrastructure/fotmob/FotMobDetailStagingContract');
    const a = deterministicObservationId('3901023', 'a'.repeat(64));
    const b = deterministicObservationId('3901023', 'a'.repeat(64));
    const c = deterministicObservationId('3901023', 'b'.repeat(64));
    const d = deterministicObservationId('3901024', 'a'.repeat(64));
    assert.strictEqual(a, b);
    assert.notStrictEqual(a, c);
    assert.notStrictEqual(a, d);
    assert.match(a, /^[0-9a-f]{8}-[0-9a-f]{4}-5[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
});

test('P2-3: nanosecond-different timestamps are NOT equal (no ms-precision collapse)', () => {
    const { sameInstant } = require('../../src/infrastructure/fotmob/FotMobDetailStagingContract');
    assert.strictEqual(sameInstant('2026-08-04T12:00:00.123456789Z', '2026-08-04T12:00:00.123456788Z'), false);
    assert.strictEqual(sameInstant('2026-08-04T12:00:00.000000001Z', '2026-08-04T12:00:00.000000002Z'), false);
});

test('P2-3: timezone-equivalent but textually different strings are rejected (contract decision)', () => {
    const { sameInstant } = require('../../src/infrastructure/fotmob/FotMobDetailStagingContract');
    assert.strictEqual(sameInstant('2026-08-04T12:00:00.000Z', '2026-08-04T12:00:00Z'), false);
    assert.strictEqual(sameInstant('2026-08-04T12:00:00Z', '2026-08-04T14:00:00+02:00'), false);
});

test('P2-3: illegal timestamps are rejected', () => {
    const { sameInstant, isStrictAbsoluteTimestamp } = require('../../src/infrastructure/fotmob/FotMobDetailStagingContract');
    for (const bad of ['not-a-date', '2026-08-04', '2026-08-04T12:00:00', '2026-13-04T12:00:00Z', '']) {
        assert.strictEqual(isStrictAbsoluteTimestamp(bad), false, bad);
        assert.strictEqual(sameInstant(bad, '2026-08-04T12:00:00Z'), false, bad);
    }
    // equal canonical strings ARE the same instant
    assert.strictEqual(sameInstant('2026-08-04T12:00:00.537Z', '2026-08-04T12:00:00.537Z'), true);
});

// ── P2-4: structured garbage fails closed (Codex review 4863122944 P2-4) ──

test('P2-4: null / array / string / number / boolean payload is REJECTED_SCHEMA_UNKNOWN (never throws)', () => {
    const pair = buildPair();
    for (const garbage of [null, [], 'string', 123, true, undefined]) {
        const validation = validateObservation({
            payload: garbage,
            manifest: pair.manifest,
            payloadBytes: pair.payloadBytes,
        });
        assert.strictEqual(validation.ok, false, String(garbage));
        assert.strictEqual(validation.terminal_state, TERMINAL_STATES.REJECTED_SCHEMA_UNKNOWN, String(garbage));
        assert.strictEqual(validation.error_code, ERROR_CODES.E001, String(garbage));
        assert.ok(
            validation.errors.some(e => e.message.includes('must be JSON objects')),
            JSON.stringify(validation.errors)
        );
    }
});

test('P2-4: structured garbage manifest is REJECTED_SCHEMA_UNKNOWN (never throws)', () => {
    const pair = buildPair();
    for (const garbage of [null, [], 'manifest', 42, false]) {
        const validation = validateObservation({
            payload: pair.payload,
            manifest: garbage,
            payloadBytes: pair.payloadBytes,
        });
        assert.strictEqual(validation.ok, false, String(garbage));
        assert.strictEqual(validation.terminal_state, TERMINAL_STATES.REJECTED_SCHEMA_UNKNOWN, String(garbage));
        assert.strictEqual(validation.error_code, ERROR_CODES.E001, String(garbage));
    }
});

test('P2-4: the L1 message names the actual received type of each side', () => {
    const pair = buildPair();
    const validation = validateObservation({
        payload: null,
        manifest: [1, 2],
        payloadBytes: pair.payloadBytes,
    });
    assert.ok(
        validation.errors.some(e => /payload=null, manifest=array\(2\)/.test(e.message)),
        JSON.stringify(validation.errors)
    );
});

test('R6-P1-2b: validateStagingArtifact rejects an artifact whose observed teams are empty (identity semantics)', async () => {
    // Codex round-6 finding (part 2): the artifact validator must enforce the
    // same identity semantics the converter enforces — an artifact whose
    // observed_identity teams are empty must never validate.
    const pair = buildPair();
    const { convertPair } = require('../../src/infrastructure/fotmob/FotMobDetailStagingConverter');
    const ok = convertPair({
        payload: pair.payload,
        manifest: pair.manifest,
        payloadBytes: pair.payloadBytes,
    });
    assert.strictEqual(ok.ok, true);
    const tampered = {
        ...ok.artifact,
        observed_identity: { ...ok.artifact.observed_identity, home_team: '', away_team: '' },
    };
    const validation = validateStagingArtifact(tampered);
    assert.strictEqual(validation.ok, false);
    assert.ok(validation.errors.some(e => e.includes('observed_identity.home_team required')));
    assert.ok(validation.errors.some(e => e.includes('observed_identity.away_team required')));
});

test('R6-P1-2c: validateStagingArtifact rejects an artifact whose observed_match_id contradicts source_match_id', async () => {
    const pair = buildPair();
    const { convertPair } = require('../../src/infrastructure/fotmob/FotMobDetailStagingConverter');
    const ok = convertPair({
        payload: pair.payload,
        manifest: pair.manifest,
        payloadBytes: pair.payloadBytes,
    });
    const tampered = {
        ...ok.artifact,
        observed_identity: { ...ok.artifact.observed_identity, observed_match_id: '9999999' },
    };
    const validation = validateStagingArtifact(tampered);
    assert.strictEqual(validation.ok, false);
    assert.ok(validation.errors.some(e => e.includes('observed_identity.observed_match_id must equal source_match_id')));
});

test('R6-P1-2d (legal control): a converter-built artifact passes the identity semantics', async () => {
    const pair = buildPair();
    const { convertPair } = require('../../src/infrastructure/fotmob/FotMobDetailStagingConverter');
    const ok = convertPair({
        payload: pair.payload,
        manifest: pair.manifest,
        payloadBytes: pair.payloadBytes,
    });
    const validation = validateStagingArtifact(ok.artifact);
    assert.strictEqual(validation.ok, true, validation.errors.join('; '));
});
