'use strict';

// lifecycle: permanent；M3-R1 canonical 恢复 / candidate 绑定 / output-aware 收据验证 /
// M3-R2 temporal contract 回归测试（canonical ×8、canonical-vs-generic ×1、binding ×3、
// verify ×6、temporal ×11）。sibling 文件 odds_staging_rebuild.test.js 保留 bundle 模式
// 回归；两者共同覆盖 historical_odds_rebuild.js + historical_odds_rebuild_canonical.js。
// 全部使用运行时生成的 fixture git 仓库 / 临时 bundle；不写入仓库、不访问网络/数据库。

const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const {
    canonicalStagingDirectory,
    classifyTemporalEvaluationReadiness,
    createBoundedGitReader,
    runRebuild,
    validateRebuildReceipt,
    verifyRebuildReceiptAgainstOutput,
} = require('../../scripts/ops/odds_staging/historical_odds_rebuild');

const INGESTED_AT = '2026-08-09T06:15:00Z';
const PROJECT_ROOT = path.resolve(__dirname, '../..');

function createTempDirectory(t, prefix = 'fp-canonical-') {
    const directory = fs.mkdtempSync(path.join(os.tmpdir(), prefix));
    t.after(() => fs.rmSync(directory, { recursive: true, force: true }));
    return directory;
}

// 4-row fixture: A1/A2 = same match spelled with aliases (Bournemouth/Man City vs
// AFC Bournemouth/Manchester City), B = Chelsea vs Arsenal, C = Liverpool vs Everton.
const FIXTURE_CSV = [
    'FixtureLifecycle,Div,Date,Time,HomeTeam,AwayTeam,FTHG,FTAG,B365H,B365D,B365A,B365CH,B365CD,B365CA',
    'test-fixture,E0,05/08/2023,15:00,Bournemouth,Man City,1,0,2.10,3.40,3.60,2.15,3.35,3.50',
    'test-fixture,E0,05/08/2023,15:00,AFC Bournemouth,Manchester City,1,0,2.10,3.40,3.60,2.15,3.35,3.50',
    'test-fixture,E0,06/08/2023,17:30,Chelsea,Arsenal,2,1,1.80,3.80,4.50,1.84,3.76,4.44',
    'test-fixture,E0,06/08/2023,19:00,Liverpool,Everton,0,0,2.05,3.30,3.90,2.10,3.28,3.85',
].join('\n');

// 4-row fixture variant: same columns, distinct fourth match (Newcastle vs Aston Villa).
const FIXTURE_CSV_ALT = [
    'FixtureLifecycle,Div,Date,Time,HomeTeam,AwayTeam,FTHG,FTAG,B365H,B365D,B365A,B365CH,B365CD,B365CA',
    'test-fixture,E0,05/08/2023,15:00,Bournemouth,Man City,1,0,2.10,3.40,3.60,2.15,3.35,3.50',
    'test-fixture,E0,05/08/2023,15:00,AFC Bournemouth,Manchester City,1,0,2.10,3.40,3.60,2.15,3.35,3.50',
    'test-fixture,E0,06/08/2023,17:30,Chelsea,Arsenal,2,1,1.80,3.80,4.50,1.84,3.76,4.44',
    'test-fixture,E0,07/08/2023,14:00,Newcastle United,Aston Villa,1,1,2.30,3.25,3.10,2.35,3.15,3.00',
].join('\n');

function collectTree(directory) {
    const files = {};
    for (const name of fs.readdirSync(directory).sort()) {
        const full = path.join(directory, name);
        if (fs.statSync(full).isDirectory()) {
            for (const [relative, content] of Object.entries(collectTree(full))) {
                files[path.join(name, relative)] = content;
            }
        } else {
            files[name] = fs.readFileSync(full, 'utf8');
        }
    }
    return files;
}

function createFixtureGitRepository(t, files) {
    const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'fp-git-fixture-'));
    t.after(() => fs.rmSync(directory, { recursive: true, force: true }));
    execFileSync('git', ['init', '-q', directory]);
    execFileSync('git', ['-C', directory, 'config', 'user.email', 'fixture@example.com']);
    execFileSync('git', ['-C', directory, 'config', 'user.name', 'fixture']);
    execFileSync('git', ['-C', directory, 'config', 'commit.gpgsign', 'false']);
    execFileSync('git', ['-C', directory, 'config', 'init.defaultBranch', 'main']);
    for (const [relativePath, content] of Object.entries(files)) {
        const target = path.join(directory, relativePath);
        fs.mkdirSync(path.dirname(target), { recursive: true });
        fs.writeFileSync(target, content, 'utf8');
    }
    execFileSync('git', ['-C', directory, 'add', '-A']);
    execFileSync('git', ['-C', directory, 'commit', '-q', '-m', 'fixture']);
    const commitSha = execFileSync('git', ['-C', directory, 'rev-parse', 'HEAD'], { encoding: 'utf8' }).trim();
    return {
        repositoryRoot: directory,
        commitSha,
        blobShaOf: relativePath => execFileSync('git', ['-C', directory, 'rev-parse', `${commitSha}:${relativePath}`], { encoding: 'utf8' }).trim(),
    };
}

function canonicalSpecsFromFixture(git, files) {
    return Object.entries(files).map(([historicalPath, content], index) => {
        const bytes = Buffer.from(content, 'utf8');
        return {
            id: `src${index}`,
            historicalPath,
            sourceCommit: git.commitSha,
            expectedBlobSha: git.blobShaOf(historicalPath),
            expectedSha256: crypto.createHash('sha256').update(bytes).digest('hex'),
            expectedBytes: bytes.length,
            expectedRows: content.trim().split('\n').length - 1,
        };
    });
}

function canonicalFixture(t) {
    const files = {
        'data/odds/2223.csv': FIXTURE_CSV,
        'data/odds/2324.csv': FIXTURE_CSV_ALT,
        'data/odds/real.csv': FIXTURE_CSV,
    };
    const git = createFixtureGitRepository(t, files);
    const specs = canonicalSpecsFromFixture(git, files);
    const directory = createTempDirectory(t, 'fp-canonical-');
    const emitDir = path.join(directory, 'emit');
    fs.mkdirSync(emitDir);
    return { git, specs, emitDir };
}

function canonicalRunOptions(fixture) {
    return { canonical: true, emitDir: fixture.emitDir, ingestedAt: INGESTED_AT };
}

function canonicalRunDependencies(fixture) {
    return { repositoryRoot: fixture.git.repositoryRoot, canonicalSources: fixture.specs };
}

function verifyEmitDirectory(emitDirectory, dependencies = {}) {
    return verifyRebuildReceiptAgainstOutput(emitDirectory, fs, {
        validateReceipt: validateRebuildReceipt,
        ...dependencies,
    });
}

// ---- canonical mode (GAP-01) ------------------------------------------------

// 4-row fixture variant: same columns, distinct fourth match (Newcastle vs Aston Villa).
test('canonical: full canonical rebuild recovers sources from git objects and emits a v2 receipt', t => {
    const fixture = canonicalFixture(t);
    const receipt = runRebuild(canonicalRunOptions(fixture), canonicalRunDependencies(fixture));
    assert.equal(receipt.rebuild_mode, 'canonical_git_history');
    assert.equal(receipt.sources.length, 3);
    assert.equal(receipt.canonical_source_contract.satisfied, true);
    assert.equal(receipt.canonical_source_contract.sources[0].commit_sha, fixture.git.commitSha);
    assert.equal(receipt.canonical_source_contract.sources[0].blob_sha, fixture.specs[0].expectedBlobSha);
    assert.equal(receipt.source_population.unique_candidates, 4);
    assert.equal(validateRebuildReceipt(receipt).valid, true);

    // Materialized manifests mirror the evidence shape with the git triple binding.
    const manifest = JSON.parse(
        fs.readFileSync(path.join(fixture.emitDir, 'src0', 'source-manifest.normalized.json'), 'utf8')
    );
    assert.equal(manifest.acquisition_mode, 'historical_git_recovery');
    assert.equal(manifest.recovered_at, INGESTED_AT);
    assert.equal(manifest.repository_provenance.commit_sha, fixture.git.commitSha);
    assert.equal(manifest.repository_provenance.blob_sha, fixture.specs[0].expectedBlobSha);
    assert.equal(manifest.repository_provenance.path, 'data/odds/2223.csv');
    assert.match(manifest.repository_provenance.commit_timestamp, /^\d{4}-\d{2}-\d{2}T/);

    // The materialized raw path satisfies the sourceManifest realpath contract:
    // it must be the staging CSV, inside the deterministic staging directory,
    // and never inside the repository.
    const stagingDirectory = canonicalStagingDirectory(INGESTED_AT, fixture.specs);
    assert.equal(manifest.raw_path, path.join(stagingDirectory, 'src0.csv'));
    assert.ok(!manifest.raw_path.startsWith(fixture.git.repositoryRoot));
    assert.ok(!manifest.raw_path.startsWith(PROJECT_ROOT));
    assert.equal(fs.existsSync(manifest.raw_path), true);
});

test('canonical: two canonical rebuilds with identical identities produce byte-identical output', t => {
    const fixture = canonicalFixture(t);
    const emitB = path.join(path.dirname(fixture.emitDir), 'emit-b');
    fs.mkdirSync(emitB);
    const optionsA = { ...canonicalRunOptions(fixture), canonicalSources: fixture.specs, repositoryRoot: fixture.git.repositoryRoot };
    const receiptA = runRebuild(optionsA, canonicalRunDependencies(fixture));
    const receiptB = runRebuild({ ...optionsA, emitDir: emitB }, canonicalRunDependencies(fixture));
    assert.equal(receiptA.source_population.business_content_sha256, receiptB.source_population.business_content_sha256);
    assert.deepEqual(collectTree(fixture.emitDir), collectTree(emitB));
});

test('canonical: wrong pinned blob identity fails closed before any staging', t => {
    const fixture = canonicalFixture(t);
    const badSpecs = fixture.specs.map(spec => ({ ...spec, expectedBlobSha: 'f'.repeat(40) }));
    assert.throws(
        () => runRebuild(canonicalRunOptions(fixture), { ...canonicalRunDependencies(fixture), canonicalSources: badSpecs }),
        error => error.code === 'SAFETY_ERROR'
    );
    assert.deepEqual(fs.readdirSync(fixture.emitDir), [], 'no output may be emitted when the git binding is violated');
});

test('canonical: wrong pinned raw SHA-256 fails closed', t => {
    const fixture = canonicalFixture(t);
    const badSpecs = fixture.specs.map(spec => ({ ...spec, expectedSha256: '0'.repeat(64) }));
    assert.throws(
        () => runRebuild(canonicalRunOptions(fixture), { ...canonicalRunDependencies(fixture), canonicalSources: badSpecs }),
        error => error.code === 'SAFETY_ERROR'
    );
    assert.deepEqual(fs.readdirSync(fixture.emitDir), []);
});

test('canonical: wrong pinned row count fails closed', t => {
    const fixture = canonicalFixture(t);
    const badSpecs = fixture.specs.map(spec => ({ ...spec, expectedRows: spec.expectedRows + 1 }));
    assert.throws(
        () => runRebuild(canonicalRunOptions(fixture), { ...canonicalRunDependencies(fixture), canonicalSources: badSpecs }),
        error => error.code === 'SAFETY_ERROR'
    );
    assert.deepEqual(fs.readdirSync(fixture.emitDir), []);
});

test('canonical: GIT_DIR environment cannot hijack repository resolution', t => {
    const fixture = canonicalFixture(t);
    const evil = createFixtureGitRepository(t, { 'evil.csv': 'not,relevant\n1,2\n' });
    const reader = createBoundedGitReader(fixture.git.repositoryRoot, {
        env: { ...process.env, GIT_DIR: evil.repositoryRoot, GIT_WORK_TREE: evil.repositoryRoot },
    });
    const resolved = reader.resolveBlobSha(fixture.git.commitSha, 'data/odds/2223.csv');
    assert.equal(resolved, fixture.specs[0].expectedBlobSha);
});

test('canonical: bounded git reader rejects non-fixed inputs before executing anything', t => {
    const fixture = canonicalFixture(t);
    const reader = createBoundedGitReader(fixture.git.repositoryRoot);
    assert.throws(() => reader.resolveBlobSha('HEAD; rm -rf /', 'data/odds/2223.csv'), error => error.code === 'SAFETY_ERROR');
    assert.throws(() => reader.resolveBlobSha(fixture.git.commitSha, '../escape.csv'), error => error.code === 'SAFETY_ERROR');
    assert.throws(() => reader.readBlob('not-a-sha'), error => error.code === 'SAFETY_ERROR');
});

test('canonical: --canonical-history cannot be combined with --bundle', t => {
    const fixture = canonicalFixture(t);
    assert.throws(
        () => runRebuild({ ...canonicalRunOptions(fixture), bundle: path.dirname(fixture.emitDir) }, canonicalRunDependencies(fixture)),
        error => error.code === 'INPUT_ERROR'
    );
});

// ---- canonical vs generic ×1 -------------------------------------------------

test('canonical: conflict samples sort deterministically with multiple samples', t => {
    const { classifyLinkage } = require('../../scripts/ops/odds_staging/historical_odds_rebuild');
    const entries = [
        { identity: { season: '2023/2024', kickoff_at: '2023-08-05T14:00:00Z', home_team: 'AFC Bournemouth', away_team: 'Manchester City' }, observations: [{ match_link: { status: 'unmatched', method: 'derived_kickoff_conflict', evidence: { delta_minutes: 15 }, candidate_ids: ['c2', 'c1'] } }] },
        { identity: { season: '2023/2024', kickoff_at: '2023-08-05T14:00:00Z', home_team: 'Chelsea', away_team: 'Arsenal' }, observations: [{ match_link: { status: 'unmatched', method: 'derived_kickoff_conflict', evidence: { delta_minutes: 30 }, candidate_ids: ['c3'] } }] },
    ];
    const linkage = classifyLinkage(entries);
    assert.equal(linkage.conflict_samples.length, 2);
    const keys = linkage.conflict_samples.map(sample => `${sample.season}|${sample.home_team}|${sample.away_team}|${sample.kickoff_at}|${sample.method}|${sample.delta_minutes}|${(sample.candidate_ids || []).join('|')}`);
    assert.deepEqual(keys, [...keys].sort(), 'conflict samples must be in code-unit order');
    assert.deepEqual(classifyLinkage(entries).conflict_samples, linkage.conflict_samples, 'sorting must be deterministic across calls');
});

test('canonical-vs-generic: canonical and bundle rebuilds emit the same observation content', t => {
    // Replay the exact materialized sources through generic bundle mode: the
    // bundle is built from the canonical staging files with only raw_path
    // adjusted, so the observation layer must be byte-identical across modes.
    const fixture = canonicalFixture(t);
    const receiptCanonical = runRebuild(canonicalRunOptions(fixture), canonicalRunDependencies(fixture));
    const stagingDirectory = canonicalStagingDirectory(INGESTED_AT, fixture.specs);
    const directory = createTempDirectory(t);
    const genericSources = [];
    fixture.specs.forEach((spec, index) => {
        const name = `src${index}`;
        const csvPath = path.join(directory, `${name}.csv`);
        fs.copyFileSync(path.join(stagingDirectory, `${name}.csv`), csvPath);
        const manifest = JSON.parse(fs.readFileSync(path.join(stagingDirectory, `${name}.manifest.json`), 'utf8'));
        fs.writeFileSync(path.join(directory, `${name}.manifest.json`), `${JSON.stringify({ ...manifest, raw_path: csvPath })}\n`, 'utf8');
        genericSources.push({ id: name, csv: `${name}.csv`, manifest: `${name}.manifest.json` });
    });
    fs.writeFileSync(
        path.join(directory, 'sources.json'),
        `${JSON.stringify({ schema_version: 'm3-historical-odds-rebuild-bundle/v1', sources: genericSources })}\n`,
        'utf8'
    );
    const genericEmitDir = path.join(directory, 'emit');
    fs.mkdirSync(genericEmitDir);

    const receiptGeneric = runRebuild(
        { bundle: directory, candidates: undefined, emitDir: genericEmitDir, ingestedAt: INGESTED_AT },
        {}
    );
    assert.equal(receiptCanonical.rebuild_mode, 'canonical_git_history');
    assert.equal(receiptGeneric.rebuild_mode, 'generic_external_bundle');
    assert.equal(receiptCanonical.source_population.business_content_sha256, receiptGeneric.source_population.business_content_sha256);
    for (const file of ['accepted-observations.jsonl', 'quarantine.jsonl', 'summary.json']) {
        const canonicalFile = fs.readFileSync(path.join(fixture.emitDir, 'src0', file), 'utf8');
        const genericFile = fs.readFileSync(path.join(genericEmitDir, 'src0', file), 'utf8');
        assert.equal(canonicalFile, genericFile, `${file} must be identical across modes`);
    }
});

// ---- candidate artifact binding ×3 ------------------------------------------

function writeFrozenCandidates(t, directory) {
    // Self-consistent frozen artifact: declared 1140 AND 1140 array entries (the
    // binding check rejects artifacts whose declared count contradicts the array).
    const fixtureCandidates = [
        { id: '47_20232024_0000001', source_provider: 'FotMob', source_match_id: '0000001', competition: 'Premier League', season: '2023/2024', home_team: 'AFC Bournemouth', away_team: 'Manchester City', kickoff_at: '2023-08-05T14:00:00Z' },
        { id: '47_20232024_0000002', source_provider: 'FotMob', source_match_id: '0000002', competition: 'Premier League', season: '2023/2024', home_team: 'Chelsea', away_team: 'Arsenal', kickoff_at: '2023-08-06T16:30:00Z' },
        { id: '47_20232024_0000003', source_provider: 'FotMob', source_match_id: '0000003', competition: 'Premier League', season: '2023/2024', home_team: 'Liverpool', away_team: 'Everton', kickoff_at: '2023-08-06T18:15:00Z' },
        { id: '47_20232024_0000004', source_provider: 'FotMob', source_match_id: '0000004', competition: 'Premier League', season: '2023/2024', home_team: 'Newcastle United', away_team: 'Aston Villa', kickoff_at: '2023-08-07T13:00:00Z' },
    ];
    const candidates = [...fixtureCandidates];
    for (let index = 5; index <= 1140; index += 1) {
        candidates.push({
            id: `47_20232024_${String(index).padStart(7, '0')}`,
            source_provider: 'FotMob',
            source_match_id: String(index),
            competition: 'Premier League',
            season: '2023/2024',
            home_team: `Filler FC ${index}`,
            away_team: `Opponent FC ${index}`,
            kickoff_at: '2023-08-05T14:00:00Z',
        });
    }
    const candidatesPath = path.join(directory, 'frozen-candidates.json');
    fs.writeFileSync(
        candidatesPath,
        `${JSON.stringify({
            schema_version: 'candidate-match-identity/v1',
            extracted_at: '2026-07-17T18:51:14.657Z',
            snapshot: {
                source_provider: 'FotMob',
                league_id: '47',
                competition: 'Premier League',
                seasons: ['2023/2024'],
                candidate_count: candidates.length,
                business_content_sha256: 'eff881728429260012b4de9f93764a08096407e06b9dffd9c9f9e2b4e0bc9d3f',
            },
            candidates,
        })}\n`,
        'utf8'
    );
    return candidatesPath;
}

test('binding: canonical mode rejects a candidate artifact with the wrong count (fail closed)', t => {
    const fixture = canonicalFixture(t);
    const directory = createTempDirectory(t);
    const wrongCount = path.join(directory, 'candidates.json');
    fs.writeFileSync(wrongCount, `${JSON.stringify({
        schema_version: 'candidate-match-identity/v1',
        snapshot: { candidate_count: 4, business_content_sha256: 'eff881728429260012b4de9f93764a08096407e06b9dffd9c9f9e2b4e0bc9d3f' },
        candidates: [],
    })}\n`, 'utf8');
    assert.throws(
        () => runRebuild({ ...canonicalRunOptions(fixture), candidates: wrongCount }, canonicalRunDependencies(fixture)),
        error => error.code === 'INPUT_ERROR'
    );
});

test('binding: canonical mode rejects a candidate artifact with the wrong declared business hash', t => {
    const fixture = canonicalFixture(t);
    const directory = createTempDirectory(t);
    const wrongHash = path.join(directory, 'candidates.json');
    fs.writeFileSync(wrongHash, `${JSON.stringify({
        schema_version: 'candidate-match-identity/v1',
        snapshot: { candidate_count: 1140, business_content_sha256: 'b'.repeat(64) },
        candidates: [],
    })}\n`, 'utf8');
    assert.throws(
        () => runRebuild({ ...canonicalRunOptions(fixture), candidates: wrongHash }, canonicalRunDependencies(fixture)),
        error => error.code === 'INPUT_ERROR'
    );
});

test('binding: canonical mode accepts the frozen M3 candidate artifact and runs linkage', t => {
    const fixture = canonicalFixture(t);
    const directory = createTempDirectory(t);
    const candidatesPath = writeFrozenCandidates(t, directory);
    const receipt = runRebuild(
        { ...canonicalRunOptions(fixture), candidates: candidatesPath },
        canonicalRunDependencies(fixture)
    );
    assert.ok(receipt.linkage, 'linkage must be executed with the frozen candidate artifact');
    assert.equal(receipt.candidates_artifact.declared_business_content_sha256, 'eff881728429260012b4de9f93764a08096407e06b9dffd9c9f9e2b4e0bc9d3f');
    assert.equal(validateRebuildReceipt(receipt).valid, true);
});

test('binding: an artifact whose declared count contradicts its candidates array is rejected', t => {
    // Forged snapshot metadata (declared 1140, actual array 1) must fail closed:
    // otherwise linkage could silently run against far fewer candidates than the
    // frozen baseline while the receipt still claims the frozen count.
    const fixture = canonicalFixture(t);
    const directory = createTempDirectory(t);
    const forged = path.join(directory, 'candidates.json');
    fs.writeFileSync(forged, `${JSON.stringify({
        schema_version: 'candidate-match-identity/v1',
        snapshot: { candidate_count: 1140, business_content_sha256: 'eff881728429260012b4de9f93764a08096407e06b9dffd9c9f9e2b4e0bc9d3f' },
        candidates: [{ id: '47_20232024_0000001', source_provider: 'FotMob', source_match_id: '0000001', competition: 'Premier League', season: '2023/2024', home_team: 'AFC Bournemouth', away_team: 'Manchester City', kickoff_at: '2023-08-05T14:00:00Z' }],
    })}\n`, 'utf8');
    assert.throws(
        () => runRebuild({ ...canonicalRunOptions(fixture), candidates: forged }, canonicalRunDependencies(fixture)),
        error => error.code === 'INPUT_ERROR'
    );
});

// ---- output-aware receipt verification (GAP-02) ------------------------------

test('verify: an untouched emitted rebuild verifies PASS, recomputing every receipt fact', t => {
    const fixture = canonicalFixture(t);
    runRebuild(canonicalRunOptions(fixture), canonicalRunDependencies(fixture));
    const result = verifyEmitDirectory(fixture.emitDir, canonicalRunDependencies(fixture));
    assert.deepEqual(result, { valid: true, errors: [] });
});

test('verify: a tampered receipt count is REJECTED', t => {
    const fixture = canonicalFixture(t);
    runRebuild(canonicalRunOptions(fixture), canonicalRunDependencies(fixture));
    const receiptPath = path.join(fixture.emitDir, 'receipt.json');
    const receipt = JSON.parse(fs.readFileSync(receiptPath, 'utf8'));
    receipt.sources[0].accepted_count += 1;
    fs.writeFileSync(receiptPath, `${JSON.stringify(receipt)}\n`, 'utf8');
    const result = verifyEmitDirectory(fixture.emitDir, canonicalRunDependencies(fixture));
    assert.equal(result.valid, false);
    assert.ok(result.errors.some(error => error.includes('accepted_count')));
});

test('verify: a removed emitted observation line is REJECTED', t => {
    const fixture = canonicalFixture(t);
    runRebuild(canonicalRunOptions(fixture), canonicalRunDependencies(fixture));
    // No candidates -> the accepted file is empty; tamper the quarantine stream.
    const quarantinePath = path.join(fixture.emitDir, 'src0', 'quarantine.jsonl');
    const lines = fs.readFileSync(quarantinePath, 'utf8').trim().split('\n');
    fs.writeFileSync(quarantinePath, `${lines.slice(1).join('\n')}\n`, 'utf8');
    const result = verifyEmitDirectory(fixture.emitDir, canonicalRunDependencies(fixture));
    assert.equal(result.valid, false);
    assert.ok(result.errors.some(error => error.includes('quarantine rows')));
});

test('verify: a tampered source population business hash is REJECTED', t => {
    const fixture = canonicalFixture(t);
    runRebuild(canonicalRunOptions(fixture), canonicalRunDependencies(fixture));
    const receiptPath = path.join(fixture.emitDir, 'receipt.json');
    const receipt = JSON.parse(fs.readFileSync(receiptPath, 'utf8'));
    receipt.source_population.business_content_sha256 = 'c'.repeat(64);
    fs.writeFileSync(receiptPath, `${JSON.stringify(receipt)}\n`, 'utf8');
    const result = verifyEmitDirectory(fixture.emitDir, canonicalRunDependencies(fixture));
    assert.equal(result.valid, false);
    assert.ok(result.errors.some(error => error.includes('business hash')));
});

test('verify: a missing receipt.json is REJECTED', t => {
    const fixture = canonicalFixture(t);
    runRebuild(canonicalRunOptions(fixture), canonicalRunDependencies(fixture));
    fs.rmSync(path.join(fixture.emitDir, 'receipt.json'));
    const result = verifyEmitDirectory(fixture.emitDir, canonicalRunDependencies(fixture));
    assert.equal(result.valid, false);
    assert.ok(result.errors.some(error => error.includes('missing receipt.json')));
});

test('verify: a tampered canonical contract hash is REJECTED by git re-verification', t => {
    const fixture = canonicalFixture(t);
    runRebuild(canonicalRunOptions(fixture), canonicalRunDependencies(fixture));
    const receiptPath = path.join(fixture.emitDir, 'receipt.json');
    const receipt = JSON.parse(fs.readFileSync(receiptPath, 'utf8'));
    receipt.canonical_source_contract.sources[0].raw_sha256 = 'd'.repeat(64);
    fs.writeFileSync(receiptPath, `${JSON.stringify(receipt)}\n`, 'utf8');
    const result = verifyEmitDirectory(fixture.emitDir, canonicalRunDependencies(fixture));
    assert.equal(result.valid, false);
    assert.ok(result.errors.some(error => error.includes('SHA-256')));
});

test('verify: a contract pointing at a valid but non-pinned git object is REJECTED', t => {
    const fixture = canonicalFixture(t);
    runRebuild(canonicalRunOptions(fixture), canonicalRunDependencies(fixture));
    const receiptPath = path.join(fixture.emitDir, 'receipt.json');
    const receipt = JSON.parse(fs.readFileSync(receiptPath, 'utf8'));
    // Swap src0's blob for src1's (a perfectly valid git object — but not the
    // pinned identity): git re-verification alone would pass; the pinned cross-
    // check must reject it.
    receipt.canonical_source_contract.sources[0].blob_sha = fixture.specs[1].expectedBlobSha;
    fs.writeFileSync(receiptPath, `${JSON.stringify(receipt)}\n`, 'utf8');
    const result = verifyEmitDirectory(fixture.emitDir, canonicalRunDependencies(fixture));
    assert.equal(result.valid, false);
    assert.ok(result.errors.some(error => error.includes('pinned identity')));
});

test('verify: a contract that drops a pinned source is REJECTED', t => {
    const fixture = canonicalFixture(t);
    runRebuild(canonicalRunOptions(fixture), canonicalRunDependencies(fixture));
    const receiptPath = path.join(fixture.emitDir, 'receipt.json');
    const receipt = JSON.parse(fs.readFileSync(receiptPath, 'utf8'));
    receipt.canonical_source_contract.sources = receipt.canonical_source_contract.sources.slice(1);
    fs.writeFileSync(receiptPath, `${JSON.stringify(receipt)}\n`, 'utf8');
    const result = verifyEmitDirectory(fixture.emitDir, canonicalRunDependencies(fixture));
    assert.equal(result.valid, false);
    assert.ok(result.errors.some(error => error.includes('pinned')));
});

test('verify: a contract repeating a pinned source and dropping another is REJECTED', t => {
    const fixture = canonicalFixture(t);
    runRebuild(canonicalRunOptions(fixture), canonicalRunDependencies(fixture));
    const receiptPath = path.join(fixture.emitDir, 'receipt.json');
    const receipt = JSON.parse(fs.readFileSync(receiptPath, 'utf8'));
    // Same declared length: src0 repeated, src2 dropped — only the duplicate-id
    // check can catch this substitution.
    receipt.canonical_source_contract.sources = [
        receipt.canonical_source_contract.sources[0],
        receipt.canonical_source_contract.sources[1],
        receipt.canonical_source_contract.sources[0],
    ];
    fs.writeFileSync(receiptPath, `${JSON.stringify(receipt)}\n`, 'utf8');
    const result = verifyEmitDirectory(fixture.emitDir, canonicalRunDependencies(fixture));
    assert.equal(result.valid, false);
    assert.ok(result.errors.some(error => error.includes('more than once')));
});

test('verify: a receipt dropping a source entry while its emitted files remain is REJECTED', t => {
    const fixture = canonicalFixture(t);
    runRebuild(canonicalRunOptions(fixture), canonicalRunDependencies(fixture));
    const receiptPath = path.join(fixture.emitDir, 'receipt.json');
    const receipt = JSON.parse(fs.readFileSync(receiptPath, 'utf8'));
    receipt.sources = receipt.sources.slice(1);
    fs.writeFileSync(receiptPath, `${JSON.stringify(receipt)}\n`, 'utf8');
    const result = verifyEmitDirectory(fixture.emitDir, canonicalRunDependencies(fixture));
    assert.equal(result.valid, false);
    assert.ok(result.errors.some(error => error.includes('not declared by the receipt')));
});

test('verify: a modified emitted observation line is REJECTED by the emitted digest', t => {
    const fixture = canonicalFixture(t);
    runRebuild(canonicalRunOptions(fixture), canonicalRunDependencies(fixture));
    // Flip one decimal odds value: counts, population and linkage all stay
    // identical — only the emitted output digest can catch this byte-level tamper.
    const quarantinePath = path.join(fixture.emitDir, 'src0', 'quarantine.jsonl');
    const lines = fs.readFileSync(quarantinePath, 'utf8').trim().split('\n');
    const first = JSON.parse(lines[0]);
    first.evidence.parsed_fields.decimal_odds = 9.99;
    const rewritten = [JSON.stringify(first), ...lines.slice(1)].join('\n');
    fs.writeFileSync(quarantinePath, `${rewritten}\n`, 'utf8');
    const result = verifyEmitDirectory(fixture.emitDir, canonicalRunDependencies(fixture));
    assert.equal(result.valid, false);
    assert.ok(result.errors.some(error => error.includes('digest')));
});

test('verify: a tampered receipt emitted_digest is REJECTED', t => {
    const fixture = canonicalFixture(t);
    runRebuild(canonicalRunOptions(fixture), canonicalRunDependencies(fixture));
    const receiptPath = path.join(fixture.emitDir, 'receipt.json');
    const receipt = JSON.parse(fs.readFileSync(receiptPath, 'utf8'));
    receipt.sources[0].emitted_digest = 'e'.repeat(64);
    fs.writeFileSync(receiptPath, `${JSON.stringify(receipt)}\n`, 'utf8');
    const result = verifyEmitDirectory(fixture.emitDir, canonicalRunDependencies(fixture));
    assert.equal(result.valid, false);
    assert.ok(result.errors.some(error => error.includes('digest')));
});

test('verify: a hand-edited receipt raw_sha256 is REJECTED against the emitted manifest', t => {
    const fixture = canonicalFixture(t);
    runRebuild(canonicalRunOptions(fixture), canonicalRunDependencies(fixture));
    const receiptPath = path.join(fixture.emitDir, 'receipt.json');
    const receipt = JSON.parse(fs.readFileSync(receiptPath, 'utf8'));
    receipt.sources[0].raw_sha256 = 'f'.repeat(64);
    fs.writeFileSync(receiptPath, `${JSON.stringify(receipt)}\n`, 'utf8');
    const result = verifyEmitDirectory(fixture.emitDir, canonicalRunDependencies(fixture));
    assert.equal(result.valid, false);
    assert.ok(result.errors.some(error => error.includes('raw_sha256')));
});

test('verify: a hand-edited quarantine_reasons is REJECTED', t => {
    const fixture = canonicalFixture(t);
    runRebuild(canonicalRunOptions(fixture), canonicalRunDependencies(fixture));
    const receiptPath = path.join(fixture.emitDir, 'receipt.json');
    const receipt = JSON.parse(fs.readFileSync(receiptPath, 'utf8'));
    receipt.sources[0].quarantine_reasons = { match_link_unmatched: 1 };
    fs.writeFileSync(receiptPath, `${JSON.stringify(receipt)}\n`, 'utf8');
    const result = verifyEmitDirectory(fixture.emitDir, canonicalRunDependencies(fixture));
    assert.equal(result.valid, false);
    assert.ok(result.errors.some(error => error.includes('quarantine reasons')));
});

test('verify: a hand-edited readiness reasons list is REJECTED by the classifier recompute', t => {
    const fixture = canonicalFixture(t);
    runRebuild(canonicalRunOptions(fixture), canonicalRunDependencies(fixture));
    const receiptPath = path.join(fixture.emitDir, 'receipt.json');
    const receipt = JSON.parse(fs.readFileSync(receiptPath, 'utf8'));
    receipt.evaluation_readiness.reasons = ['some invented reason'];
    fs.writeFileSync(receiptPath, `${JSON.stringify(receipt)}\n`, 'utf8');
    const result = verifyEmitDirectory(fixture.emitDir, canonicalRunDependencies(fixture));
    assert.equal(result.valid, false);
    assert.ok(result.errors.some(error => error.includes('classifier')));
});

test('verify: a removed linkage block on a candidates receipt is REJECTED', t => {
    const fixture = canonicalFixture(t);
    const directory = createTempDirectory(t);
    const candidatesPath = writeFrozenCandidates(t, directory);
    runRebuild({ ...canonicalRunOptions(fixture), candidates: candidatesPath }, canonicalRunDependencies(fixture));
    const receiptPath = path.join(fixture.emitDir, 'receipt.json');
    const receipt = JSON.parse(fs.readFileSync(receiptPath, 'utf8'));
    delete receipt.linkage;
    fs.writeFileSync(receiptPath, `${JSON.stringify(receipt)}\n`, 'utf8');
    const result = verifyEmitDirectory(fixture.emitDir, canonicalRunDependencies(fixture));
    assert.equal(result.valid, false);
    // The schema-level rebuild_status contract fires first (EXECUTED requires
    // linkage); the output-aware presence check is defense in depth.
    assert.ok(result.errors.some(error => error.includes('presence') || error.includes('linkage_rebuild')));
});

test('verify: an invented linkage block on a no-candidates receipt is REJECTED', t => {
    const fixture = canonicalFixture(t);
    runRebuild(canonicalRunOptions(fixture), canonicalRunDependencies(fixture));
    const receiptPath = path.join(fixture.emitDir, 'receipt.json');
    const receipt = JSON.parse(fs.readFileSync(receiptPath, 'utf8'));
    receipt.linkage = { classification: {}, distinct_matched_fotmob_ids: 0, conflict_samples: [] };
    fs.writeFileSync(receiptPath, `${JSON.stringify(receipt)}\n`, 'utf8');
    const result = verifyEmitDirectory(fixture.emitDir, canonicalRunDependencies(fixture));
    assert.equal(result.valid, false);
    assert.ok(result.errors.some(error => error.includes('presence') || error.includes('linkage_rebuild')));
});

// ---- machine-readable temporal contract (GAP-03) -----------------------------

test('temporal: observation facts are computed from the actual emitted canonical fixture data', t => {
    // Three canonical sources, no candidate artifact: every emitted observation
    // quarantines as match_link_unmatched (18 per fixture CSV — the alias pair
    // collapses at adapter level). M3-R2: canonical manifests declare the provider
    // contract applicable, so the 9 plain per-source observations carry
    // provider_collection_phase=first_collection_after_market_open (snapshot_type
    // stays unknown) and the 9 C-series observations carry snapshot_type=closing +
    // provider_collection_phase=closing — the facts must be computed, never assumed.
    const fixture = canonicalFixture(t);
    const receipt = runRebuild(canonicalRunOptions(fixture), canonicalRunDependencies(fixture));
    const facts = receipt.evaluation_readiness.observation_facts;
    assert.equal(facts.observation_count, 54);
    assert.equal(facts.accepted_count, 0);
    assert.equal(facts.quarantine_count, 54);
    assert.equal(facts.snapshot_type_unknown_count, 27);
    assert.equal(facts.known_snapshot_type_count, 27);
    assert.equal(facts.known_source_observed_at_count, 0);
    assert.equal(facts.known_captured_at_count, 0);
    assert.equal(facts.closing_observation_count, 27);
    assert.equal(facts.first_collection_observation_count, 27);
    assert.equal(facts.unknown_temporal_semantics_observation_count, 0);
    assert.equal(receipt.evaluation_readiness.temporal_value_evaluation, 'NOT_READY_FOR_TEMPORAL_VALUE_EVALUATION');
    assert.equal(receipt.evaluation_readiness.closing_odds_semantics_ready, 'YES');
    assert.equal(receipt.evaluation_readiness.first_collection_semantics_ready, 'YES');
    assert.equal(receipt.evaluation_readiness.exact_observation_timestamp_ready, 'NO');
    assert.equal(receipt.evaluation_readiness.exact_capture_timestamp_ready, 'NO');
    assert.equal(receipt.evaluation_readiness.strict_decision_time_value_evaluation_ready, 'NO');
    assert.equal(receipt.evaluation_readiness.closing_market_benchmark_semantics_ready, 'YES');
    assert.equal(receipt.temporal_semantics.snapshot_type, 'mixed');
    assert.equal(receipt.temporal_semantics.source_observed_at, 'unknown');
    assert.equal(receipt.temporal_semantics.capture_time, 'unknown');
    assert.equal(receipt.temporal_semantics.plain_series_opening_status, 'not_proven');
    assert.equal(receipt.temporal_semantics.c_series_closing_status, 'proven');
    assert.equal(receipt.temporal_semantics.plain_series_first_collection_status, 'proven');
    assert.equal(receipt.temporal_semantics.provider_contract_id, 'football-data-provider-contract/v1');
    assert.deepEqual(receipt.series_semantics_distribution, {
        closing_observation_count: 27,
        first_collection_observation_count: 27,
        unknown_temporal_semantics_observation_count: 0,
    });
    assert.deepEqual(receipt.provider_semantic_contract.applicable_sources, ['src0', 'src1', 'src2']);
    assert.equal(receipt.provider_semantic_contract.exact_observation_timestamp_available, false);
    assert.equal(receipt.provider_semantic_contract.exact_capture_timestamp_available, false);
});

test('temporal: the classifier returns NOT_READY with concrete reasons for the fixture facts', t => {
    const facts = {
        observation_count: 18,
        accepted_count: 12,
        quarantine_count: 6,
        snapshot_type_unknown_count: 9,
        known_snapshot_type_count: 9,
        known_source_observed_at_count: 0,
        known_captured_at_count: 0,
        capture_time_status_unknown_count: 18,
        closing_observation_count: 9,
        first_collection_observation_count: 9,
        unknown_temporal_semantics_observation_count: 0,
    };
    const semantics = { snapshot_type: 'mixed', source_observed_at: 'unknown', capture_time: 'unknown', plain_series_opening_status: 'not_proven', c_series_closing_status: 'proven', plain_series_first_collection_status: 'proven', provider_contract_id: 'football-data-provider-contract/v1' };
    const readiness = classifyTemporalEvaluationReadiness(facts, semantics);
    assert.equal(readiness.temporal_value_evaluation, 'NOT_READY_FOR_TEMPORAL_VALUE_EVALUATION');
    assert.ok(readiness.reasons.length >= 3);
    assert.equal(readiness.closing_odds_semantics_ready, 'YES');
    assert.equal(readiness.first_collection_semantics_ready, 'YES');
    assert.equal(readiness.exact_observation_timestamp_ready, 'NO');
    assert.equal(readiness.exact_capture_timestamp_ready, 'NO');
    assert.equal(readiness.strict_decision_time_value_evaluation_ready, 'NO');
    assert.equal(readiness.closing_market_benchmark_semantics_ready, 'YES');
});

test('temporal: proven closing semantics cannot rescue missing timestamps or plain opening (fail closed)', t => {
    const facts = {
        observation_count: 18,
        accepted_count: 12,
        quarantine_count: 6,
        snapshot_type_unknown_count: 9,
        known_snapshot_type_count: 9,
        known_source_observed_at_count: 0,
        known_captured_at_count: 0,
        capture_time_status_unknown_count: 18,
        closing_observation_count: 9,
        first_collection_observation_count: 9,
        unknown_temporal_semantics_observation_count: 0,
    };
    const semantics = { snapshot_type: 'mixed', source_observed_at: 'known', capture_time: 'known', plain_series_opening_status: 'not_proven', c_series_closing_status: 'proven', plain_series_first_collection_status: 'proven', provider_contract_id: 'football-data-provider-contract/v1' };
    const readiness = classifyTemporalEvaluationReadiness(facts, semantics);
    assert.equal(readiness.temporal_value_evaluation, 'NOT_READY_FOR_TEMPORAL_VALUE_EVALUATION');
    // 即便 C closing 已证明：facts 的观察/采集时间缺失 + plain opening 不可证明 → NOT_READY。
    assert.ok(readiness.reasons.some(reason => reason.includes('plain series opening status is not proven')));
});

test('temporal: the classifier is a genuine function — READY is reachable only with proven facts and semantics', t => {
    const facts = {
        observation_count: 2,
        accepted_count: 2,
        quarantine_count: 0,
        snapshot_type_unknown_count: 0,
        known_snapshot_type_count: 2,
        known_source_observed_at_count: 2,
        known_captured_at_count: 2,
        capture_time_status_unknown_count: 0,
        closing_observation_count: 2,
        first_collection_observation_count: 0,
        unknown_temporal_semantics_observation_count: 0,
    };
    const semantics = { snapshot_type: 'known', source_observed_at: 'known', capture_time: 'known', plain_series_opening_status: 'proven', c_series_closing_status: 'proven', plain_series_first_collection_status: 'proven', provider_contract_id: 'football-data-provider-contract/v1' };
    const readiness = classifyTemporalEvaluationReadiness(facts, semantics);
    assert.equal(readiness.temporal_value_evaluation, 'READY_FOR_TEMPORAL_VALUE_EVALUATION');
    assert.equal(readiness.strict_decision_time_value_evaluation_ready, 'YES');
    assert.equal(readiness.closing_odds_semantics_ready, 'YES');
    assert.equal(readiness.closing_market_benchmark_semantics_ready, 'YES');
    // 语义声称 first_collection proven 但没有观测携带该 phase → 该维度必须 NO（fail closed）。
    assert.equal(readiness.first_collection_semantics_ready, 'NO');
});

test('temporal: a hand-edited READY receipt is REJECTED by output-aware verification', t => {
    const fixture = canonicalFixture(t);
    runRebuild(canonicalRunOptions(fixture), canonicalRunDependencies(fixture));
    const receiptPath = path.join(fixture.emitDir, 'receipt.json');
    const receipt = JSON.parse(fs.readFileSync(receiptPath, 'utf8'));
    receipt.evaluation_readiness.temporal_value_evaluation = 'READY_FOR_TEMPORAL_VALUE_EVALUATION';
    fs.writeFileSync(receiptPath, `${JSON.stringify(receipt)}\n`, 'utf8');
    const result = verifyEmitDirectory(fixture.emitDir, canonicalRunDependencies(fixture));
    assert.equal(result.valid, false);
    assert.ok(result.errors.some(error => error.includes('classifier')));
});

test('temporal: hand-edited plain-series opening=proven is REJECTED unconditionally', t => {
    // M3-R2: provider 官方措辞 "collected after market opening"，第一组永不称为 opening；
    // 即使观测快照语义已 known（C series closing），plain opening 仍不可证明。
    const fixture = canonicalFixture(t);
    runRebuild(canonicalRunOptions(fixture), canonicalRunDependencies(fixture));
    const receiptPath = path.join(fixture.emitDir, 'receipt.json');
    const receipt = JSON.parse(fs.readFileSync(receiptPath, 'utf8'));
    receipt.temporal_semantics.plain_series_opening_status = 'proven';
    fs.writeFileSync(receiptPath, `${JSON.stringify(receipt)}\n`, 'utf8');
    const result = verifyEmitDirectory(fixture.emitDir, canonicalRunDependencies(fixture));
    assert.equal(result.valid, false);
    assert.ok(result.errors.some(error => error.includes('contradiction')));
});

test('temporal: hand-edited c_series_closing_status=not_proven against proven closing facts is REJECTED', t => {
    const fixture = canonicalFixture(t);
    runRebuild(canonicalRunOptions(fixture), canonicalRunDependencies(fixture));
    const receiptPath = path.join(fixture.emitDir, 'receipt.json');
    const receipt = JSON.parse(fs.readFileSync(receiptPath, 'utf8'));
    // The classifier recomputes closing_odds_semantics_ready from the facts: a
    // receipt claiming closing not proven while 27 emitted observations carry the
    // closing phase fails the classifier comparison (fail closed on downgrade too).
    receipt.temporal_semantics.c_series_closing_status = 'not_proven';
    fs.writeFileSync(receiptPath, `${JSON.stringify(receipt)}\n`, 'utf8');
    const result = verifyEmitDirectory(fixture.emitDir, canonicalRunDependencies(fixture));
    assert.equal(result.valid, false);
    assert.ok(result.errors.some(error => error.includes('classifier') || error.includes('contradiction')));
});

test('temporal: hand-edited provider_contract_id is REJECTED by output-aware verification', t => {
    const fixture = canonicalFixture(t);
    runRebuild(canonicalRunOptions(fixture), canonicalRunDependencies(fixture));
    const receiptPath = path.join(fixture.emitDir, 'receipt.json');
    const receipt = JSON.parse(fs.readFileSync(receiptPath, 'utf8'));
    receipt.temporal_semantics.provider_contract_id = 'tampered-contract/v999';
    receipt.provider_semantic_contract.contract_id = 'tampered-contract/v999';
    fs.writeFileSync(receiptPath, `${JSON.stringify(receipt)}\n`, 'utf8');
    const result = verifyEmitDirectory(fixture.emitDir, canonicalRunDependencies(fixture));
    assert.equal(result.valid, false);
    assert.ok(result.errors.some(error => error.includes('provider_contract_id') || error.includes('contract_id')));
});

test('temporal: hand-edited series_semantics_distribution is REJECTED by output-aware verification', t => {
    // Codex F-01: the distribution is a pure projection of the facts; a tampered
    // distribution (closing 0 vs facts 27) must fail even though facts/semantics
    // still match the emitted output.
    const fixture = canonicalFixture(t);
    runRebuild(canonicalRunOptions(fixture), canonicalRunDependencies(fixture));
    const receiptPath = path.join(fixture.emitDir, 'receipt.json');
    const receipt = JSON.parse(fs.readFileSync(receiptPath, 'utf8'));
    receipt.series_semantics_distribution = {
        closing_observation_count: 0,
        first_collection_observation_count: 54,
        unknown_temporal_semantics_observation_count: 0,
    };
    fs.writeFileSync(receiptPath, `${JSON.stringify(receipt)}\n`, 'utf8');
    const result = verifyEmitDirectory(fixture.emitDir, canonicalRunDependencies(fixture));
    assert.equal(result.valid, false);
    assert.ok(result.errors.some(error => error.includes('series_semantics_distribution')));
});

test('temporal: a consistently downgraded receipt (closing not_proven + readiness NO) is REJECTED', t => {
    // Codex R2 F-01: status fields are pure functions of the facts — a hand-edit
    // that downgrades c_series_closing_status AND flips the readiness dimensions
    // consistently must still fail, otherwise audits trust under-claimed semantics.
    const fixture = canonicalFixture(t);
    runRebuild(canonicalRunOptions(fixture), canonicalRunDependencies(fixture));
    const receiptPath = path.join(fixture.emitDir, 'receipt.json');
    const receipt = JSON.parse(fs.readFileSync(receiptPath, 'utf8'));
    receipt.temporal_semantics.c_series_closing_status = 'not_proven';
    receipt.evaluation_readiness.closing_odds_semantics_ready = 'NO';
    receipt.evaluation_readiness.closing_market_benchmark_semantics_ready = 'NO';
    fs.writeFileSync(receiptPath, `${JSON.stringify(receipt)}\n`, 'utf8');
    const result = verifyEmitDirectory(fixture.emitDir, canonicalRunDependencies(fixture));
    assert.equal(result.valid, false);
    assert.ok(result.errors.some(error => error.includes('c_series_closing_status')));
});

test('temporal: hand-edited provider_semantic_contract provenance fields are REJECTED', t => {
    // Codex R2 F-02: every provenance field must match the committed contract,
    // not just contract_id.
    const fixture = canonicalFixture(t);
    runRebuild(canonicalRunOptions(fixture), canonicalRunDependencies(fixture));
    const receiptPath = path.join(fixture.emitDir, 'receipt.json');
    const receipt = JSON.parse(fs.readFileSync(receiptPath, 'utf8'));
    receipt.provider_semantic_contract.provider_id = 'some-other-provider';
    receipt.provider_semantic_contract.evidence_checked_at = '2020-01-01';
    fs.writeFileSync(receiptPath, `${JSON.stringify(receipt)}\n`, 'utf8');
    const result = verifyEmitDirectory(fixture.emitDir, canonicalRunDependencies(fixture));
    assert.equal(result.valid, false);
    assert.ok(result.errors.some(error => error.includes('provider_id') && error.includes('committed provider contract')));
});

test('temporal: hand-edited readiness dimensions are REJECTED by output-aware verification', t => {
    const fixture = canonicalFixture(t);
    runRebuild(canonicalRunOptions(fixture), canonicalRunDependencies(fixture));
    const receiptPath = path.join(fixture.emitDir, 'receipt.json');
    const receipt = JSON.parse(fs.readFileSync(receiptPath, 'utf8'));
    receipt.evaluation_readiness.closing_odds_semantics_ready = 'NO';
    fs.writeFileSync(receiptPath, `${JSON.stringify(receipt)}\n`, 'utf8');
    const result = verifyEmitDirectory(fixture.emitDir, canonicalRunDependencies(fixture));
    assert.equal(result.valid, false);
    assert.ok(result.errors.some(error => error.includes('classifier')));
});

test('temporal: recovery provenance (recovered_at / commit_timestamp) cannot make readiness READY', t => {
    const fixture = canonicalFixture(t);
    runRebuild(canonicalRunOptions(fixture), canonicalRunDependencies(fixture));
    const receiptPath = path.join(fixture.emitDir, 'receipt.json');
    const receipt = JSON.parse(fs.readFileSync(receiptPath, 'utf8'));
    // The only "timestamps" a canonical rebuild can prove are staging recovery and
    // git commit times — never observation capture times; a READY claim built on
    // them must fail closed because the emitted observations carry no timestamps.
    receipt.evaluation_readiness.temporal_value_evaluation = 'READY_FOR_TEMPORAL_VALUE_EVALUATION';
    receipt.temporal_semantics.source_observed_at = 'known';
    receipt.temporal_semantics.capture_time = 'known';
    receipt.evaluation_readiness.reasons = ['recovered_at and commit_timestamp are known'];
    fs.writeFileSync(receiptPath, `${JSON.stringify(receipt)}\n`, 'utf8');
    const result = verifyEmitDirectory(fixture.emitDir, canonicalRunDependencies(fixture));
    assert.equal(result.valid, false);
    assert.ok(result.errors.some(error => error.includes('classifier')));
});

test('temporal: hand-edited semantics fields contradicting the facts are REJECTED', t => {
    const fixture = canonicalFixture(t);
    runRebuild(canonicalRunOptions(fixture), canonicalRunDependencies(fixture));
    const receiptPath = path.join(fixture.emitDir, 'receipt.json');
    const receipt = JSON.parse(fs.readFileSync(receiptPath, 'utf8'));
    // Flipping snapshot_type to 'known' while every emitted observation stays
    // unknown must fail: the semantics fields are recomputed from the facts.
    receipt.temporal_semantics.snapshot_type = 'known';
    fs.writeFileSync(receiptPath, `${JSON.stringify(receipt)}\n`, 'utf8');
    const result = verifyEmitDirectory(fixture.emitDir, canonicalRunDependencies(fixture));
    assert.equal(result.valid, false);
    assert.ok(result.errors.some(error => error.includes('snapshot_type')));
});

test('rebuild_status: the machine-readable rebuild status contract is emitted and enforced', t => {
    // No candidates -> source rebuild SUCCESS, linkage rebuild NOT_EXECUTED, and
    // the validator refuses a receipt whose linkage_rebuild contradicts linkage.
    const fixture = canonicalFixture(t);
    const receipt = runRebuild(canonicalRunOptions(fixture), canonicalRunDependencies(fixture));
    assert.deepEqual(receipt.rebuild_status, { source_rebuild: 'SUCCESS', linkage_rebuild: 'NOT_EXECUTED' });
    assert.equal(validateRebuildReceipt(receipt).valid, true);

    const mutated = { ...receipt, rebuild_status: { source_rebuild: 'SUCCESS', linkage_rebuild: 'EXECUTED' } };
    const validation = validateRebuildReceipt(mutated);
    assert.equal(validation.valid, false);
    assert.ok(validation.errors.some(error => error.includes('linkage_rebuild')));

    const mutatedLinkage = { ...receipt, linkage: { classification: {}, distinct_matched_fotmob_ids: 0, conflict_samples: [] } };
    const validationLinkage = validateRebuildReceipt(mutatedLinkage);
    assert.equal(validationLinkage.valid, false);
    assert.ok(validationLinkage.errors.some(error => error.includes('linkage_rebuild')));

    // NOT_EXECUTED is also inconsistent with a carried candidates_artifact.
    const mutatedArtifact = { ...receipt, candidates_artifact: { basename: 'x.json', raw_sha256: 'a'.repeat(64), declared_business_content_sha256: null } };
    const validationArtifact = validateRebuildReceipt(mutatedArtifact);
    assert.equal(validationArtifact.valid, false);
    assert.ok(validationArtifact.errors.some(error => error.includes('candidates_artifact')));
});
