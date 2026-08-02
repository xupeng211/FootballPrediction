'use strict';

// lifecycle: permanent
// PLAN-stage tests for the bounded FotMob detail capture pipeline.
// Fully offline: no network, no database, no repository writes.
// Real network is structurally forbidden via global.fetch.

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
    buildDeterministicCapturePlan,
    writePlanDocument,
    verifyRepositoryExternalPath,
} = require('../../src/infrastructure/fotmob/FotMobDetailCapturePlan');
const {
    computeBusinessContentHash,
    computeV1IdentityProjectionHash,
    computeV2BusinessHash,
} = require('../../src/infrastructure/fotmob/FotMobCandidateExporter');
const {
    PLAN_SCHEMA_VERSION,
} = require('../../src/infrastructure/fotmob/FotMobDetailCaptureContract');

const REPO_ROOT = path.resolve(__dirname, '..', '..');
const TEST_REVISION = 'a7da729fd29675c6f16e1bfc49511772d2bd590d';
const FIXED_CLOCK = '2026-08-02T12:00:00.000Z';

function sha256Text(text) {
    return crypto.createHash('sha256').update(String(text), 'utf8').digest('hex');
}

function tmpDir(prefix) {
    return fs.mkdtempSync(path.join(os.tmpdir(), prefix));
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

function makeV1Artifact(candidates, { schema = 'candidate-match-identity/v1', provider = 'FotMob', leagueId = 47, competition = 'Premier League' } = {}) {
    const business_content_sha256 = computeBusinessContentHash(candidates);
    return {
        schema_version: schema,
        extracted_at: '2026-07-17T18:51:14.657Z',
        snapshot: {
            source_provider: provider,
            league_id: leagueId,
            competition,
            seasons: [...new Set(candidates.map(c => c.season))].sort(),
            candidate_count: candidates.length,
            business_content_sha256,
        },
        candidates,
    };
}

// v2 fixture mirrors the REAL producer shape
// (FotMobCandidateExporter.buildV2OutputDocument): metadata lives in the
// artifact block, hashes are the exporter's dual hashes.
function makeV2Artifact(candidates, { provider = 'FotMob', leagueId = 47, competition = 'Premier League' } = {}) {
    const identity_projection_hash = computeV1IdentityProjectionHash(candidates);
    const business_hash = computeV2BusinessHash(candidates);
    return {
        schema_version: 'canonical-inventory-artifact/v2',
        extracted_at: '2026-07-17T18:51:14.657Z',
        artifact: {
            kind: 'master',
            source_provider: provider,
            competition,
            seasons: [...new Set(candidates.map(c => c.season))].sort(),
            candidate_count: candidates.length,
            identity_projection_hash,
            business_hash,
            status_mapping_version: 'fotmob-status-to-matches-status/v1',
            synthetic_test_only: false,
        },
        candidates,
    };
}

function writeArtifact(dir, doc) {
    const p = path.join(dir, 'artifact.json');
    fs.writeFileSync(p, JSON.stringify(doc, null, 2));
    return p;
}

const SAMPLE_CANDIDATES = [
    makeCandidate({ id: 4506263, season: '2024/2025', home: 'Manchester United', away: 'Fulham', kickoff: '2024-08-16T19:00:00Z' }),
    makeCandidate({ id: 4506264, season: '2024/2025', home: 'Ipswich Town', away: 'Liverpool', kickoff: '2024-08-17T11:30:00Z' }),
    makeCandidate({ id: 4506265, season: '2024/2025', home: 'Arsenal', away: 'Wolverhampton Wanderers', kickoff: '2024-08-17T14:00:00Z' }),
    makeCandidate({ id: 4484199, season: '2023/2024', home: 'Burnley', away: 'Manchester City', kickoff: '2023-08-11T19:00:00Z' }),
    makeCandidate({ id: 4484200, season: '2023/2024', home: 'Arsenal', away: 'Nottingham Forest', kickoff: '2023-08-12T14:00:00Z' }),
];

function makePlanOptions(dir, extra = {}) {
    const artifact = extra.artifactPath || writeArtifact(dir, makeV1Artifact(SAMPLE_CANDIDATES));
    return {
        artifactPath: artifact,
        seasons: ['2024/2025'],
        generatedAt: FIXED_CLOCK,
        collectorCodeRevision: TEST_REVISION,
        ...extra,
    };
}

// ─────────────────────────────────────────────────────────────
// A. PLAN
// ─────────────────────────────────────────────────────────────

test('PLAN: v1 artifact success with season+limit produces deterministic plan', () => {
    const dir = tmpDir('fotmob-plan-v1-');
    try {
        const result = buildDeterministicCapturePlan(makePlanOptions(dir, { limit: 2 }));
        assert.equal(result.plan.schema_version, PLAN_SCHEMA_VERSION);
        assert.equal(result.selectedCount, 2);
        assert.equal(result.plan.selected_candidate_count, 2);
        assert.equal(result.plan.source_provider, 'FotMob');
        assert.equal(result.plan.competition, 'Premier League');
        assert.equal(result.plan.league_id, '47');
        assert.deepEqual(result.plan.selected_seasons, ['2024/2025']);
        assert.equal(result.plan.generator_component, 'FotMobDetailCapturePipeline');
        assert.equal(result.plan.generator_code_revision, TEST_REVISION);
        assert.match(result.plan.plan_business_sha256, /^[0-9a-f]{64}$/);
        assert.equal(result.plan.candidates[0].ordinal, 1);
        assert.equal(result.plan.candidates[0].expected_request_path, '/match/4506263');
        assert.match(result.plan.candidates[0].candidate_identity_sha256, /^[0-9a-f]{64}$/);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('PLAN: v2 artifact success', () => {
    const dir = tmpDir('fotmob-plan-v2-');
    try {
        const artifact = writeArtifact(dir, makeV2Artifact(SAMPLE_CANDIDATES));
        const result = buildDeterministicCapturePlan({
            artifactPath: artifact,
            seasons: ['2023/2024'],
            limit: 1,
            generatedAt: FIXED_CLOCK,
            collectorCodeRevision: TEST_REVISION,
        });
        assert.equal(result.plan.source_artifact_schema, 'canonical-inventory-artifact/v2');
        assert.equal(result.selectedCount, 1);
        assert.equal(result.plan.candidates[0].season, '2023/2024');
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('PLAN: unknown schema rejected', () => {
    const dir = tmpDir('fotmob-plan-unknown-');
    try {
        const doc = makeV1Artifact(SAMPLE_CANDIDATES);
        doc.schema_version = 'mystery-schema/v9';
        const artifact = writeArtifact(dir, doc);
        assert.throws(
            () => buildDeterministicCapturePlan(makePlanOptions(dir, { artifactPath: artifact, limit: 1 })),
            (err) => err.code === 'INPUT_ERROR' && /unknown artifact schema/.test(err.message)
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('PLAN: wrong source provider rejected', () => {
    const dir = tmpDir('fotmob-plan-provider-');
    try {
        const doc = makeV1Artifact(SAMPLE_CANDIDATES, { provider: 'Football-Data' });
        const artifact = writeArtifact(dir, doc);
        assert.throws(
            () => buildDeterministicCapturePlan(makePlanOptions(dir, { artifactPath: artifact, limit: 1 })),
            (err) => err.code === 'INPUT_ERROR' && /source_provider/.test(err.message)
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('PLAN: wrong league id rejected', () => {
    const dir = tmpDir('fotmob-plan-league-');
    try {
        const doc = makeV1Artifact(SAMPLE_CANDIDATES, { leagueId: 123 });
        const artifact = writeArtifact(dir, doc);
        assert.throws(
            () => buildDeterministicCapturePlan(makePlanOptions(dir, { artifactPath: artifact, limit: 1 })),
            (err) => err.code === 'INPUT_ERROR' && /league_id/.test(err.message)
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('PLAN: wrong competition rejected', () => {
    const dir = tmpDir('fotmob-plan-comp-');
    try {
        const doc = makeV1Artifact(SAMPLE_CANDIDATES, { competition: 'La Liga' });
        const artifact = writeArtifact(dir, doc);
        assert.throws(
            () => buildDeterministicCapturePlan(makePlanOptions(dir, { artifactPath: artifact, limit: 1 })),
            (err) => err.code === 'INPUT_ERROR' && /competition/.test(err.message)
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('PLAN: duplicate candidate id rejected', () => {
    const dir = tmpDir('fotmob-plan-dupid-');
    try {
        const candidates = [
            makeCandidate({ id: 100, season: '2024/2025', home: 'A', away: 'B', kickoff: '2024-08-16T19:00:00Z' }),
            makeCandidate({ id: 100, season: '2024/2025', home: 'C', away: 'D', kickoff: '2024-08-17T19:00:00Z' }),
        ];
        const artifact = writeArtifact(dir, makeV1Artifact(candidates));
        assert.throws(
            () => buildDeterministicCapturePlan(makePlanOptions(dir, { artifactPath: artifact, limit: 2 })),
            (err) => err.code === 'INPUT_ERROR' && /duplicate candidate id/.test(err.message)
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('PLAN: duplicate source_match_id rejected', () => {
    const dir = tmpDir('fotmob-plan-dupsrc-');
    try {
        const candidates = [
            makeCandidate({ id: 100, season: '2024/2025', home: 'A', away: 'B', kickoff: '2024-08-16T19:00:00Z' }),
            makeCandidate({ id: 101, season: '2024/2025', home: 'C', away: 'D', kickoff: '2024-08-17T19:00:00Z' }),
        ];
        candidates[1].source_match_id = '100';
        const artifact = writeArtifact(dir, makeV1Artifact(candidates));
        assert.throws(
            () => buildDeterministicCapturePlan(makePlanOptions(dir, { artifactPath: artifact, limit: 2 })),
            (err) => err.code === 'INPUT_ERROR' && /duplicate source_match_id/.test(err.message)
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('PLAN: non-numeric source_match_id rejected', () => {
    const dir = tmpDir('fotmob-plan-src-');
    try {
        const candidates = [
            makeCandidate({ id: 100, season: '2024/2025', home: 'A', away: 'B', kickoff: '2024-08-16T19:00:00Z' }),
        ];
        candidates[0].source_match_id = '100abc';
        const artifact = writeArtifact(dir, makeV1Artifact(candidates));
        assert.throws(
            () => buildDeterministicCapturePlan(makePlanOptions(dir, { artifactPath: artifact, limit: 1 })),
            (err) => err.code === 'INPUT_ERROR' && /source_match_id must be numeric/.test(err.message)
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('PLAN: invalid kickoff rejected', () => {
    const dir = tmpDir('fotmob-plan-kickoff-');
    try {
        const candidates = [
            makeCandidate({ id: 100, season: '2024/2025', home: 'A', away: 'B', kickoff: 'not-a-date' }),
        ];
        const artifact = writeArtifact(dir, makeV1Artifact(candidates));
        assert.throws(
            () => buildDeterministicCapturePlan(makePlanOptions(dir, { artifactPath: artifact, limit: 1 })),
            (err) => err.code === 'INPUT_ERROR' && /kickoff_at/.test(err.message)
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('PLAN: business hash mismatch rejected', () => {
    const dir = tmpDir('fotmob-plan-hash-');
    try {
        const doc = makeV1Artifact(SAMPLE_CANDIDATES);
        doc.snapshot.business_content_sha256 = 'f'.repeat(64);
        const artifact = writeArtifact(dir, doc);
        assert.throws(
            () => buildDeterministicCapturePlan(makePlanOptions(dir, { artifactPath: artifact, limit: 1 })),
            (err) => err.code === 'INPUT_ERROR' && /business hash mismatch/.test(err.message)
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('PLAN: v2 identity hash mismatch rejected', () => {
    const dir = tmpDir('fotmob-plan-v2hash-');
    try {
        const doc = makeV2Artifact(SAMPLE_CANDIDATES);
        doc.artifact.identity_projection_hash = 'e'.repeat(64);
        const artifact = writeArtifact(dir, doc);
        assert.throws(
            () => buildDeterministicCapturePlan(makePlanOptions(dir, { artifactPath: artifact, limit: 1 })),
            (err) => err.code === 'INPUT_ERROR' && /identity hash mismatch/.test(err.message)
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('PLAN: v2 business hash mismatch rejected', () => {
    const dir = tmpDir('fotmob-plan-v2bhash-');
    try {
        const doc = makeV2Artifact(SAMPLE_CANDIDATES);
        doc.artifact.business_hash = 'f'.repeat(64);
        const artifact = writeArtifact(dir, doc);
        assert.throws(
            () => buildDeterministicCapturePlan(makePlanOptions(dir, { artifactPath: artifact, limit: 1 })),
            (err) => err.code === 'INPUT_ERROR' && /business hash mismatch/.test(err.message)
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('PLAN: v2 candidate_count mismatch rejected', () => {
    const dir = tmpDir('fotmob-plan-v2count-');
    try {
        const doc = makeV2Artifact(SAMPLE_CANDIDATES);
        doc.artifact.candidate_count = 999;
        const artifact = writeArtifact(dir, doc);
        assert.throws(
            () => buildDeterministicCapturePlan(makePlanOptions(dir, { artifactPath: artifact, limit: 1 })),
            (err) => err.code === 'INPUT_ERROR' && /candidate_count mismatch/.test(err.message)
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('PLAN: symlink input rejected', () => {
    const dir = tmpDir('fotmob-plan-symlink-');
    try {
        const target = writeArtifact(dir, makeV1Artifact(SAMPLE_CANDIDATES));
        const link = path.join(dir, 'artifact-link.json');
        fs.symlinkSync(target, link);
        assert.throws(
            () => buildDeterministicCapturePlan(makePlanOptions(dir, { artifactPath: link, limit: 1 })),
            (err) => err.code === 'SAFETY_ERROR' && /symlink/.test(err.message)
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('PLAN: no filter and no limit rejected (no full population default)', () => {
    const dir = tmpDir('fotmob-plan-nofilter-');
    try {
        assert.throws(
            () => buildDeterministicCapturePlan(makePlanOptions(dir, { seasons: [], matchIds: [] })),
            (err) => err.code === 'INPUT_ERROR' && /explicit selection required/.test(err.message)
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('PLAN: invalid limit rejected', () => {
    const dir = tmpDir('fotmob-plan-limit-');
    try {
        assert.throws(
            () => buildDeterministicCapturePlan(makePlanOptions(dir, { limit: 0 })),
            (err) => err.code === 'INPUT_ERROR' && /limit/.test(err.message)
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('PLAN: deterministic ordering is season → kickoff_at → source_match_id', () => {
    const dir = tmpDir('fotmob-plan-order-');
    try {
        const candidates = [
            makeCandidate({ id: 3, season: '2023/2024', home: 'A', away: 'B', kickoff: '2023-08-12T14:00:00Z' }),
            makeCandidate({ id: 2, season: '2023/2024', home: 'C', away: 'D', kickoff: '2023-08-11T14:00:00Z' }),
            makeCandidate({ id: 1, season: '2024/2025', home: 'E', away: 'F', kickoff: '2024-08-16T19:00:00Z' }),
            makeCandidate({ id: 5, season: '2024/2025', home: 'G', away: 'H', kickoff: '2024-08-16T19:00:00Z' }),
            makeCandidate({ id: 4, season: '2024/2025', home: 'I', away: 'J', kickoff: '2024-08-16T19:00:00Z' }),
        ];
        const artifact = writeArtifact(dir, makeV1Artifact(candidates));
        const result = buildDeterministicCapturePlan({
            artifactPath: artifact,
            limit: 5,
            generatedAt: FIXED_CLOCK,
            collectorCodeRevision: TEST_REVISION,
        });
        const ids = result.plan.candidates.map(c => c.source_match_id);
        assert.deepEqual(ids, ['2', '3', '1', '4', '5']);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('PLAN: deterministic plan hash — identical inputs produce identical business content', () => {
    const dir = tmpDir('fotmob-plan-det-');
    try {
        const a = buildDeterministicCapturePlan(makePlanOptions(dir, { limit: 2 }));
        const b = buildDeterministicCapturePlan(makePlanOptions(dir, { limit: 2 }));
        assert.equal(a.planBusinessSha256, b.planBusinessSha256);
        assert.equal(a.plan.plan_business_sha256, b.plan.plan_business_sha256);
        assert.deepEqual(a.plan.candidates, b.plan.candidates);
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('PLAN: --match-id filter works', () => {
    const dir = tmpDir('fotmob-plan-mid-');
    try {
        const result = buildDeterministicCapturePlan(makePlanOptions(dir, {
            seasons: [],
            matchIds: ['4506264'],
        }));
        assert.equal(result.selectedCount, 1);
        assert.equal(result.plan.candidates[0].source_match_id, '4506264');
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('PLAN: plan document writes to repository-external path with readback', () => {
    const dir = tmpDir('fotmob-plan-write-');
    try {
        const result = buildDeterministicCapturePlan(makePlanOptions(dir, { limit: 1 }));
        const outputPath = path.join(dir, 'plan.json');
        const written = writePlanDocument(result.plan, outputPath);
        assert.equal(written.outputPath, outputPath);
        const readback = JSON.parse(fs.readFileSync(outputPath, 'utf8'));
        assert.equal(readback.schema_version, PLAN_SCHEMA_VERSION);
        assert.equal(written.writtenSha256, sha256Text(fs.readFileSync(outputPath, 'utf8')));
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('PLAN: output path inside repository rejected', () => {
    const dir = tmpDir('fotmob-plan-repo-');
    try {
        const result = buildDeterministicCapturePlan(makePlanOptions(dir, { limit: 1 }));
        const inRepo = path.join(REPO_ROOT, '.tmp-plan-rejected.json');
        try {
            assert.throws(
                () => writePlanDocument(result.plan, inRepo),
                (err) => err.code === 'SAFETY_ERROR' && /outside the repository/.test(err.message)
            );
        } finally {
            try { fs.unlinkSync(inRepo); } catch { /* ignore */ }
        }
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('PLAN: output parent must not be a symlink', () => {
    const dir = tmpDir('fotmob-plan-parsym-');
    try {
        const realParent = path.join(dir, 'real');
        fs.mkdirSync(realParent);
        const linkParent = path.join(dir, 'link');
        fs.symlinkSync(realParent, linkParent, 'dir');
        const result = buildDeterministicCapturePlan(makePlanOptions(dir, { limit: 1 }));
        assert.throws(
            () => writePlanDocument(result.plan, path.join(linkParent, 'plan.json')),
            (err) => err.code === 'SAFETY_ERROR' && /symlink/.test(err.message)
        );
    } finally {
        fs.rmSync(dir, { recursive: true, force: true });
    }
});

test('PLAN: verifyRepositoryExternalPath rejects relative paths', () => {
    assert.throws(
        () => verifyRepositoryExternalPath('relative/path.json'),
        (err) => err.code === 'INPUT_ERROR'
    );
});
