'use strict';

// lifecycle: permanent
// Converter tests for FotMobDetailStagingConverter.js.
// Fully offline: no network, no database, no capture.

global.fetch = () => {
    throw new Error('REAL_NETWORK_FORBIDDEN_IN_TEST');
};

const { test } = require('node:test');
const assert = require('node:assert');
const path = require('node:path');

const { convertPair, convertAll } = require('../../src/infrastructure/fotmob/FotMobDetailStagingConverter');
const {
    TERMINAL_STATES,
    ERROR_CODES,
    validateStagingArtifact,
    SECTIONS,
} = require('../../src/infrastructure/fotmob/FotMobDetailStagingContract');
const {
    buildPair,
    buildPayload,
    buildSourceIndex,
    sourceIndexEntry,
} = require('../helpers/fotmobDetailStagingFixtures');

const REPO_ROOT = path.resolve(__dirname, '..', '..');

function pairArgs(pair) {
    return {
        payload: pair.payload,
        manifest: pair.manifest,
        payloadBytes: pair.payloadBytes,
    };
}

// ── converter purity / determinism ──────────────────────────

test('converter produces a valid deterministic artifact; identical input → identical bytes', () => {
    const pair = buildPair();
    const a = convertPair(pairArgs(pair));
    const b = convertPair(pairArgs(buildPair()));
    assert.strictEqual(a.ok, true);
    assert.strictEqual(a.artifact.business_hash, b.artifact.business_hash);
    assert.strictEqual(JSON.stringify(a.artifact), JSON.stringify(b.artifact));
    const validation = validateStagingArtifact(a.artifact);
    assert.strictEqual(validation.ok, true, validation.errors.join('; '));
});

test('C21: shuffled source index order produces identical outputs', async () => {
    const pairs = [
        buildPair({ source_match_id: '3900932' }),
        buildPair({ source_match_id: '3900933' }),
        buildPair({ source_match_id: '3901023' }),
    ];
    const entries = pairs.map((p, i) =>
        sourceIndexEntry(p.payload.source_match_id, `/tmp/p${i}.payload.json`, `/tmp/p${i}.manifest.json`, {
            package: 'pkg',
            payload_file_sha256: String(i).repeat(64).slice(0, 64),
            manifest_file_sha256: String(i + 10).repeat(64).slice(0, 64),
        })
    );
    const run = async order => {
        const index = buildSourceIndex(
            order.map(i => entries[i]),
            {
                pkg: {
                    sha256: '0'.repeat(64),
                    path: '/tmp/archive.tar.gz',
                    receipt: '/tmp/receipt.json',
                },
            }
        );
        return convertAll({
            sourceIndex: index,
            loader: async entry => {
                const idx = entries.findIndex(e => e.source_match_id === entry.source_match_id);
                return {
                    ...pairArgs(pairs[idx]),
                    payloadFileSha256: pairs[idx].payloadBytes && undefined,
                };
            },
        });
    };
    const r1 = await run([0, 1, 2]);
    const r2 = await run([2, 0, 1]);
    assert.strictEqual(r1.ok, true);
    assert.strictEqual(r2.ok, true);
    const sorted = results =>
        results
            .map(r => ({ id: r.source_match_id, hash: r.artifact.business_hash }))
            .sort((x, y) => (x.id < y.id ? -1 : 1));
    assert.deepStrictEqual(sorted(r1.results), sorted(r2.results));
});

test('C26: duplicate source entries in the index fail closed', async () => {
    const pair = buildPair();
    const dupIndex = buildSourceIndex([
        sourceIndexEntry('3901023', '/tmp/a.payload.json', '/tmp/a.manifest.json'),
        sourceIndexEntry('3901023', '/tmp/b.payload.json', '/tmp/b.manifest.json'),
    ]);
    const result = await convertAll({
        sourceIndex: dupIndex,
        loader: async () => pairArgs(pair),
    });
    assert.strictEqual(result.ok, false);
});

test('converter never guesses canonical_match_id and keeps link status safe', () => {
    const pair = buildPair();
    const result = convertPair(pairArgs(pair));
    assert.strictEqual(result.artifact.canonical_match_id, null);
    assert.strictEqual(result.artifact.canonical_link_status, 'UNLINKED_NOT_ATTEMPTED');
});

test('converter does not write or mutate its inputs', () => {
    const pair = buildPair();
    const payloadSnapshot = JSON.stringify(pair.payload);
    const manifestSnapshot = JSON.stringify(pair.manifest);
    convertPair(pairArgs(pair));
    assert.strictEqual(JSON.stringify(pair.payload), payloadSnapshot);
    assert.strictEqual(JSON.stringify(pair.manifest), manifestSnapshot);
});

test('no wall clock: artifact generated_at comes from the manifest, observation_id is deterministic', () => {
    const pair = buildPair();
    const a = convertPair(pairArgs(pair));
    const b = convertPair(pairArgs(buildPair()));
    assert.strictEqual(a.artifact.generated_at, pair.manifest.response_received_at);
    assert.strictEqual(a.artifact.observation_id, b.artifact.observation_id);
    assert.match(a.artifact.observation_id, /^[0-9a-f]{8}-[0-9a-f]{4}-5[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
});

test('artifact preserves the five allowlisted sections verbatim (byte-faithful)', () => {
    const pair = buildPair();
    const result = convertPair(pairArgs(pair));
    for (const section of SECTIONS) {
        assert.ok(result.artifact.sections[section], `section ${section} present`);
        assert.strictEqual(result.artifact.sections[section].version, 'fotmob-match-detail-parsed/v1');
    }
    assert.deepStrictEqual(result.artifact.sections.player_stats.json, pair.payload.normalized.player_stats);
    assert.deepStrictEqual(result.artifact.sections.events.json, pair.payload.normalized.events);
});

test('rejected observations carry terminal state + error code, no artifact', () => {
    const pair = buildPair({ observed: { observed_match_id: '1111111' } });
    const result = convertPair(pairArgs(pair));
    assert.strictEqual(result.ok, false);
    assert.strictEqual(result.terminal_state, TERMINAL_STATES.REJECTED_IDENTITY_INCONSISTENT);
    assert.strictEqual(result.error_code, ERROR_CODES.E007);
    assert.strictEqual(result.artifact, null);
});

test('quarantine-class observations carry quarantine status and code', () => {
    // L6 violation: an event minute far out of range triggers E011 quarantine.
    const pair = buildPair({
        normalized: {
            match_external_id: '3901023',
            home_team: { id: 1, name: 'AFC Bournemouth', score: 0 },
            away_team: { id: 2, name: 'Leicester City', score: 0 },
            events: [
                {
                    id: 9,
                    minute: 999,
                    homeScore: 0,
                    awayScore: 0,
                    event_kind: 'real_event',
                },
            ],
            stats: [{ key: 'shots', homeValue: 0, awayValue: 0, period: 'All' }],
            lineup: {
                home: { coach: null, starters: [], subs: [] },
                away: { coach: null, starters: [], subs: [] },
            },
            shotmap: { shots: [] },
        },
    });
    const result = convertPair(pairArgs(pair));
    assert.strictEqual(result.ok, false);
    assert.strictEqual(result.terminal_state, TERMINAL_STATES.QUARANTINED_VALIDATION_FAIL);
    assert.strictEqual(result.error_code, ERROR_CODES.E011);
    assert.strictEqual(result.quarantine_status, 'quarantined');
});

test('module graph is offline: no fetch/http/DB imports in converter', () => {
    const fs = require('node:fs');
    const source = fs.readFileSync(
        path.join(REPO_ROOT, 'src/infrastructure/fotmob/FotMobDetailStagingConverter.js'),
        'utf8'
    );
    // Only the actual require() calls count — the header comment legitimately
    // names the forbidden modules.
    const requires = (source.match(/require\(['"][^'"]+['"]\)/g) || []).join('\n');
    assert.doesNotMatch(requires, /node:http|node:https|pg|ioredis/i);
    assert.doesNotMatch(source, /global\.fetch/);
    assert.doesNotMatch(source, /Date\.now\(\)/);
});

test('C27: per-observation business hashes are stable across rebuilds (aggregate arithmetic)', async () => {
    const pairs = [buildPair({ source_match_id: '3900932' }), buildPair({ source_match_id: '3900933' })];
    const run = async () =>
        convertAll({
            sourceIndex: buildSourceIndex(
                pairs.map((p, i) =>
                    sourceIndexEntry(p.payload.source_match_id, `/tmp/${i}.payload.json`, `/tmp/${i}.manifest.json`)
                )
            ),
            loader: async entry => pairArgs(pairs.find(p => p.payload.source_match_id === entry.source_match_id)),
        });
    const r1 = await run();
    const r2 = await run();
    const hashOf = r =>
        r.results
            .map(x => x.artifact.business_hash)
            .sort()
            .join('');
    assert.strictEqual(hashOf(r1), hashOf(r2));
});

// ── P2-4: convertAll never lets one pathological input crash the batch ──

test('P2-4: convertAll with a structured-garbage loader entry rejects that entry and converts the rest', async () => {
    const pairs = [buildPair({ source_match_id: '3900932' }), buildPair({ source_match_id: '3900933' })];
    const index = buildSourceIndex(
        pairs.map((p, i) =>
            sourceIndexEntry(p.payload.source_match_id, `/tmp/${i}.payload.json`, `/tmp/${i}.manifest.json`, {
                package: 'pkg',
                payload_file_sha256: `${i}`.repeat(64).slice(0, 64),
                manifest_file_sha256: `${i + 10}`.repeat(64).slice(0, 64),
            })
        ),
        {
            pkg: {
                sha256: '0'.repeat(64),
                path: '/tmp/archive.tar.gz',
                receipt: '/tmp/receipt.json',
            },
        }
    );
    const result = await convertAll({
        sourceIndex: index,
        loader: async entry => {
            if (entry.source_match_id === '3900932') {
                return { payload: null, manifest: null, payloadBytes: Buffer.alloc(0) };
            }
            const pair = pairs.find(p => p.payload.source_match_id === entry.source_match_id);
            return pairArgs(pair);
        },
    });
    assert.strictEqual(result.ok, false, 'a batch with one bad entry is not all-ok');
    assert.strictEqual(result.results.length, 2, 'both entries are processed, the batch does not crash');
    const rejected = result.results.find(r => r.source_match_id === '3900932');
    assert.strictEqual(rejected.ok, false);
    assert.strictEqual(rejected.terminal_state, TERMINAL_STATES.REJECTED_SCHEMA_UNKNOWN);
    assert.strictEqual(rejected.artifact, null);
    const accepted = result.results.find(r => r.source_match_id === '3900933');
    assert.strictEqual(accepted.ok, true);
    assert.ok(accepted.artifact);
});

test('P2-4: a loader SAFETY_ERROR (e.g. forged package receipt at live archive verification) rejects only that entry as E008 and converts the rest', async () => {
    // RUN_D revalidation evidence: the package-level guard
    // (verifyLiveArchiveAgainstReceipt) throws SAFETY_ERROR; convertAll's
    // per-entry isolation records the failing entry as
    // REJECTED_PROVENANCE_BROKEN/E008 and continues the batch — a forged
    // receipt can never produce an accepted observation.
    const pairs = [buildPair({ source_match_id: '3900932' }), buildPair({ source_match_id: '3900933' })];
    const index = buildSourceIndex(
        pairs.map((p, i) =>
            sourceIndexEntry(p.payload.source_match_id, `/tmp/${i}.payload.json`, `/tmp/${i}.manifest.json`, {
                package: i === 0 ? 'forged' : 'good',
                payload_file_sha256: `${i}`.repeat(64).slice(0, 64),
                manifest_file_sha256: `${i + 10}`.repeat(64).slice(0, 64),
            })
        ),
        {
            forged: { sha256: '1'.repeat(64), path: '/tmp/forged.tar.gz', receipt: '/tmp/forged-receipt.json' },
            good: { sha256: '0'.repeat(64), path: '/tmp/good.tar.gz', receipt: '/tmp/good-receipt.json' },
        }
    );
    const result = await convertAll({
        sourceIndex: index,
        loader: async entry => {
            if (entry.source_match_id === '3900932') {
                throw Object.assign(
                    new Error('live archive member inventory does not match receipt archive_inventory_sha256'),
                    { code: 'SAFETY_ERROR' }
                );
            }
            const pair = pairs.find(p => p.payload.source_match_id === entry.source_match_id);
            return pairArgs(pair);
        },
    });
    assert.strictEqual(result.results.length, 2, 'both entries are processed, the batch does not crash');
    const rejected = result.results.find(r => r.source_match_id === '3900932');
    assert.strictEqual(rejected.ok, false);
    assert.strictEqual(rejected.terminal_state, TERMINAL_STATES.REJECTED_PROVENANCE_BROKEN);
    assert.strictEqual(rejected.error_code, ERROR_CODES.E008);
    assert.ok(rejected.errors[0].message.startsWith('input load failed:'), 'the underlying cause is preserved');
    const accepted = result.results.find(r => r.source_match_id === '3900933');
    assert.strictEqual(accepted.ok, true);
    assert.ok(accepted.artifact);
});

test('R3-P1-1: a source index entry whose source_match_id does not bind the loaded documents is rejected as E007 (identity binding)', async () => {
    // Codex round-3 finding: convertAll overwrote the result with the INDEX's
    // source_match_id, so an entry claiming `3901024` while referencing a
    // legal, receipt-bound `3901023` payload produced a "complete" build whose
    // ledger/filenames disagreed with the artifacts (only a later validate
    // would notice). The loader-level check must fail this entry closed.
    const pairs = [buildPair({ source_match_id: '3901023' }), buildPair({ source_match_id: '3900933' })];
    const index = buildSourceIndex(
        [
            sourceIndexEntry('3901024', '/tmp/1.payload.json', '/tmp/1.manifest.json', {
                package: 'pkg',
                payload_file_sha256: 'a'.repeat(64),
                manifest_file_sha256: 'b'.repeat(64),
            }),
            sourceIndexEntry('3900933', '/tmp/2.payload.json', '/tmp/2.manifest.json', {
                package: 'pkg',
                payload_file_sha256: 'c'.repeat(64),
                manifest_file_sha256: 'd'.repeat(64),
            }),
        ],
        {
            pkg: { sha256: '0'.repeat(64), path: '/tmp/archive.tar.gz', receipt: '/tmp/receipt.json' },
        }
    );
    const result = await convertAll({
        sourceIndex: index,
        loader: async entry => {
            // the loader resolves the index's claim (3901024) to the LEGAL
            // pair 3901023 — exactly the R3-P1-1 mismatch scenario
            if (entry.source_match_id === '3901024') {
                return pairArgs(pairs[0]);
            }
            return pairArgs(pairs[1]); // 3900933 resolves to its own pair
        },
    });
    assert.strictEqual(result.results.length, 2, 'both entries are processed, the batch does not crash');
    const mismatched = result.results.find(r => r.source_match_id === '3901024');
    assert.strictEqual(mismatched.ok, false);
    assert.strictEqual(mismatched.terminal_state, TERMINAL_STATES.REJECTED_PROVENANCE_BROKEN);
    assert.strictEqual(mismatched.error_code, ERROR_CODES.E007);
    assert.ok(mismatched.errors[0].message.includes('does not bind the loaded documents'));
    const accepted = result.results.find(r => r.source_match_id === '3900933');
    assert.strictEqual(accepted.ok, true);
    assert.ok(accepted.artifact);
});

test('R4-P2-1: array payload/manifest keep the P2-4 schema classification (E001), not the E007 identity path', async () => {
    // Codex round-4 finding: `typeof value === 'object'` also matches arrays,
    // so an array payload was treated as a parsed document and rejected as
    // REJECTED_PROVENANCE_BROKEN/E007 — but JSON structured garbage must
    // follow the P2-4 contract: REJECTED_SCHEMA_UNKNOWN/E001 from L1.
    const pair = buildPair({ source_match_id: '3901023' });
    const index = buildSourceIndex(
        [
            sourceIndexEntry('3901023', '/tmp/1.payload.json', '/tmp/1.manifest.json', {
                package: 'pkg',
                payload_file_sha256: 'a'.repeat(64),
                manifest_file_sha256: 'b'.repeat(64),
            }),
        ],
        {
            pkg: { sha256: '0'.repeat(64), path: '/tmp/archive.tar.gz', receipt: '/tmp/receipt.json' },
        }
    );
    // loader yields an ARRAY payload (legal-shaped manifest) — garbage shape
    const arrayPayloadResult = await convertAll({
        sourceIndex: index,
        loader: async () => ({ payload: [], manifest: pair.manifest, payloadBytes: pair.payloadBytes }),
    });
    const arrayPayload = arrayPayloadResult.results[0];
    assert.strictEqual(arrayPayload.ok, false);
    assert.strictEqual(arrayPayload.terminal_state, TERMINAL_STATES.REJECTED_SCHEMA_UNKNOWN);
    assert.strictEqual(arrayPayload.error_code, ERROR_CODES.E001);
    assert.ok(!arrayPayload.errors[0].message.includes('does not bind'), 'identity binding must not fire for arrays');
    // loader yields an ARRAY manifest (legal-shaped payload)
    const arrayManifestResult = await convertAll({
        sourceIndex: index,
        loader: async () => ({ payload: pair.payload, manifest: [], payloadBytes: pair.payloadBytes }),
    });
    const arrayManifest = arrayManifestResult.results[0];
    assert.strictEqual(arrayManifest.ok, false);
    assert.strictEqual(arrayManifest.terminal_state, TERMINAL_STATES.REJECTED_SCHEMA_UNKNOWN);
    assert.strictEqual(arrayManifest.error_code, ERROR_CODES.E001);
    // genuine object documents still pass the identity binding and convert
    const okResult = await convertAll({
        sourceIndex: index,
        loader: async () => pairArgs(pair),
    });
    assert.strictEqual(okResult.results[0].ok, true);
});

test('R6-P1-2a: payloads with EMPTY observed home/away teams are rejected (E007 identity binding), not accepted', async () => {
    // Codex round-6 finding: observed team names were only compared when
    // truthy — `observed_identity: { home_team: '', away_team: '' }` skipped
    // the binding and produced an accepted artifact with empty observed teams.
    const pair = buildPair({
        observed: {
            home_team: '',
            away_team: '',
        },
    });
    const result = convertPair({
        payload: pair.payload,
        manifest: pair.manifest,
        payloadBytes: pair.payloadBytes,
    });
    assert.strictEqual(result.ok, false);
    assert.strictEqual(result.terminal_state, 'REJECTED_IDENTITY_INCONSISTENT');
    assert.strictEqual(result.error_code, 'E007');
    assert.ok(
        result.errors.some(e => /observed_identity home_team\/away_team required/.test(e.message)),
        JSON.stringify(result.errors)
    );
});

test('R6-P1-2b (legal control): payloads with present observed teams still convert and commit', async () => {
    const pair = buildPair();
    const result = convertPair({
        payload: pair.payload,
        manifest: pair.manifest,
        payloadBytes: pair.payloadBytes,
    });
    assert.strictEqual(result.ok, true);
    assert.strictEqual(result.artifact.observed_identity.home_team, 'AFC Bournemouth');
    assert.strictEqual(result.artifact.observed_identity.away_team, 'Leicester City');
});
