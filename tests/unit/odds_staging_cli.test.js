'use strict';

// lifecycle: permanent；验证唯一离线 CLI 的默认无写入、外部临时 emit 与退出码边界。

const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const { EXIT_CODES, main } = require('../../scripts/ops/odds_staging_dry_run');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const CSV_FIXTURE = path.join(PROJECT_ROOT, 'tests/fixtures/odds_staging/football_data_explicit.fixture.csv');
const HTML_FIXTURE = path.join(PROJECT_ROOT, 'tests/fixtures/odds_staging/oddsportal_explicit.fixture.html');

function sha256File(filePath) {
    return crypto.createHash('sha256').update(fs.readFileSync(filePath)).digest('hex');
}

function createTempDirectory(t) {
    const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'fp-odds-staging-cli-'));
    t.after(() => fs.rmSync(directory, { recursive: true, force: true }));
    return directory;
}

function writeInputs(t, rawPath, adapter) {
    const directory = createTempDirectory(t);
    const manifestPath = path.join(directory, 'source-manifest.fixture.json');
    const candidatesPath = path.join(directory, 'candidates.fixture.json');
    const html = adapter === 'oddsportal-explicit-envelope-html';
    const sourceMatchId = html ? 'fixture-html-001' : 'fixture-fd-001';
    fs.writeFileSync(
        manifestPath,
        `${JSON.stringify({
            schema_version: 'odds-source-manifest/v1',
            source_provider: html ? 'oddsportal-fixture' : 'football-data-fixture',
            acquisition_mode: 'fixture',
            source_url: html
                ? 'fixture://oddsportal-explicit-envelope/fixture-html-001'
                : 'fixture://football-data/fixture-fd-001',
            source_match_id: null,
            captured_at: '2025-08-01T10:00:00Z',
            source_timezone: 'UTC',
            raw_path: rawPath,
            raw_media_type: html ? 'text/html' : 'text/csv',
            raw_size_bytes: fs.statSync(rawPath).size,
            raw_sha256: sha256File(rawPath),
            adapter,
            adapter_version: '1.0.0',
            provenance_status: 'fixture',
        })}\n`,
        'utf8'
    );
    fs.writeFileSync(
        candidatesPath,
        `${JSON.stringify([
            {
                id: 'local-match-001',
                source_provider: html ? 'oddsportal-fixture' : 'football-data-fixture',
                source_match_id: sourceMatchId,
                competition: 'Fixture League',
                season: '2025/2026',
                kickoff_at: html ? '2025-08-02T18:00:00Z' : '2025-08-01T18:00:00Z',
                home_team: html ? 'Gamma FC' : 'Alpha FC',
                away_team: html ? 'Delta FC' : 'Beta FC',
            },
        ])}\n`,
        'utf8'
    );
    return { candidatesPath, directory, manifestPath };
}

function invoke(argv) {
    let stdout = '';
    let stderr = '';
    const status = main(argv, {
        clock: () => '2026-07-16T00:00:00.000Z',
        repositoryRoot: PROJECT_ROOT,
        stdout: text => {
            stdout += text;
        },
        stderr: text => {
            stderr += text;
        },
    });
    return { status, stdout, stderr };
}

test('CLI 默认 dry-run 仅输出摘要且不创建任何文件', t => {
    const inputs = writeInputs(t, CSV_FIXTURE, 'football-data-csv');
    const before = fs.readdirSync(inputs.directory).sort();
    const result = invoke([
        '--source',
        CSV_FIXTURE,
        '--manifest',
        inputs.manifestPath,
        '--adapter',
        'football-data-csv',
        '--candidates',
        inputs.candidatesPath,
    ]);

    assert.equal(result.status, EXIT_CODES.success);
    assert.equal(result.stderr, '');
    assert.deepEqual(fs.readdirSync(inputs.directory).sort(), before);
    const summary = JSON.parse(result.stdout);
    assert.equal(summary.default_mode, 'dry_run_no_write');
    assert.deepEqual(summary.emitted_files, []);
    assert.equal(summary.accepted_count, 9);
});

test('CLI 只在明确外部 emit 目录写四个确定性文件', t => {
    const inputs = writeInputs(t, HTML_FIXTURE, 'oddsportal-explicit-envelope-html');
    const emitDirectory = createTempDirectory(t);
    const result = invoke([
        '--source',
        HTML_FIXTURE,
        '--manifest',
        inputs.manifestPath,
        '--adapter',
        'oddsportal-explicit-envelope-html',
        '--candidates',
        inputs.candidatesPath,
        '--emit-dir',
        emitDirectory,
        '--ingested-at',
        '2026-07-16T00:00:00.000Z',
    ]);

    assert.equal(result.status, EXIT_CODES.success);
    assert.deepEqual(fs.readdirSync(emitDirectory).sort(), [
        'accepted-observations.jsonl',
        'quarantine.jsonl',
        'source-manifest.normalized.json',
        'summary.json',
    ]);
    assert.equal(fs.existsSync(path.join(emitDirectory, path.basename(HTML_FIXTURE))), false);
    assert.equal(JSON.parse(result.stdout).emitted_files.length, 4);
});

test('CLI 拒绝仓库内 emit 目录和网络 source 输入', t => {
    const inputs = writeInputs(t, CSV_FIXTURE, 'football-data-csv');
    const repositoryEmit = invoke([
        '--source',
        CSV_FIXTURE,
        '--manifest',
        inputs.manifestPath,
        '--adapter',
        'football-data-csv',
        '--candidates',
        inputs.candidatesPath,
        '--emit-dir',
        PROJECT_ROOT,
        '--ingested-at',
        '2026-07-16T00:00:00.000Z',
    ]);
    assert.equal(repositoryEmit.status, EXIT_CODES.safety_boundary_error);
    assert.match(repositoryEmit.stderr, /outside the Git repository/);

    const networkSource = invoke([
        '--source',
        'https://example.invalid/input.csv',
        '--manifest',
        inputs.manifestPath,
        '--adapter',
        'football-data-csv',
        '--candidates',
        inputs.candidatesPath,
    ]);
    assert.equal(networkSource.status, EXIT_CODES.safety_boundary_error);
    assert.match(networkSource.stderr, /local path, not a network URL/);
});

test('strict 模式遇到 quarantine 返回专用退出码且不输出原始内容', t => {
    const directory = createTempDirectory(t);
    const rawPath = path.join(directory, 'generic-triplet.fixture.html');
    fs.writeFileSync(rawPath, '<script data-odds-staging="explicit">{"triplet":[2.1,3.2,3.4]}</script>', 'utf8');
    const inputs = writeInputs(t, rawPath, 'oddsportal-explicit-envelope-html');
    const result = invoke([
        '--source',
        rawPath,
        '--manifest',
        inputs.manifestPath,
        '--adapter',
        'oddsportal-explicit-envelope-html',
        '--candidates',
        inputs.candidatesPath,
        '--strict',
    ]);

    assert.equal(result.status, EXIT_CODES.strict_quarantine);
    assert.equal(result.stderr, '');
    assert.equal(result.stdout.includes('generic-triplet.fixture.html'), false);
    assert.equal(JSON.parse(result.stdout).quarantine_count, 1);
});

test('CLI help 和输入错误具有文档化退出码', () => {
    const help = invoke(['--help']);
    const missing = invoke(['--adapter', 'football-data-csv']);

    assert.equal(help.status, EXIT_CODES.success);
    assert.match(help.stdout, /Exit codes:/);
    assert.match(help.stdout, /--candidates/);
    assert.match(help.stdout, /completion does not mean every record was accepted/);
    assert.equal(missing.status, EXIT_CODES.input_error);
    assert.match(missing.stderr, /--source is required/);
});

test('CLI 标准 staging 强制要求 candidates，缺失时不会开始解析', t => {
    const inputs = writeInputs(t, CSV_FIXTURE, 'football-data-csv');
    const result = invoke([
        '--source',
        CSV_FIXTURE,
        '--manifest',
        inputs.manifestPath,
        '--adapter',
        'football-data-csv',
    ]);

    assert.equal(result.status, EXIT_CODES.input_error);
    assert.match(result.stderr, /--candidates is required/);
    assert.equal(result.stdout, '');
});

test('emit 必须显式提供严格 ingested_at，拒绝时输出目录保持不变', t => {
    const inputs = writeInputs(t, CSV_FIXTURE, 'football-data-csv');
    const emitDirectory = createTempDirectory(t);
    const missingIngestedAt = invoke([
        '--source',
        CSV_FIXTURE,
        '--manifest',
        inputs.manifestPath,
        '--adapter',
        'football-data-csv',
        '--candidates',
        inputs.candidatesPath,
        '--emit-dir',
        emitDirectory,
    ]);
    assert.equal(missingIngestedAt.status, EXIT_CODES.input_error);
    assert.match(missingIngestedAt.stderr, /--ingested-at is required with --emit-dir for deterministic output/);
    assert.deepEqual(fs.readdirSync(emitDirectory), []);

    const naive = invoke([
        '--source',
        CSV_FIXTURE,
        '--manifest',
        inputs.manifestPath,
        '--adapter',
        'football-data-csv',
        '--candidates',
        inputs.candidatesPath,
        '--ingested-at',
        '2026-07-16T18:00:00',
    ]);
    assert.equal(naive.status, EXIT_CODES.input_error);
    assert.match(naive.stderr, /explicit numeric offset/);
});

test('固定 ingested_at 的两次 emit 产生四个字节级相同文件', t => {
    const inputs = writeInputs(t, CSV_FIXTURE, 'football-data-csv');
    const firstDirectory = createTempDirectory(t);
    const secondDirectory = createTempDirectory(t);
    const baseArgs = [
        '--source',
        CSV_FIXTURE,
        '--manifest',
        inputs.manifestPath,
        '--adapter',
        'football-data-csv',
        '--candidates',
        inputs.candidatesPath,
        '--ingested-at',
        '2026-07-16T00:00:00.000Z',
    ];
    const first = invoke([...baseArgs, '--emit-dir', firstDirectory]);
    const second = invoke([...baseArgs, '--emit-dir', secondDirectory]);
    assert.equal(first.status, EXIT_CODES.success);
    assert.equal(second.status, EXIT_CODES.success);
    const expectedFiles = [
        'accepted-observations.jsonl',
        'quarantine.jsonl',
        'source-manifest.normalized.json',
        'summary.json',
    ];
    assert.deepEqual(fs.readdirSync(firstDirectory).sort(), expectedFiles);
    assert.deepEqual(fs.readdirSync(secondDirectory).sort(), expectedFiles);
    for (const filename of expectedFiles) {
        assert.equal(sha256File(path.join(firstDirectory, filename)), sha256File(path.join(secondDirectory, filename)));
    }
});

test('CLI 将 null explicit envelope 作为 adapter quarantine，而非裸 TypeError', t => {
    const directory = createTempDirectory(t);
    const rawPath = path.join(directory, 'null-envelope.fixture.html');
    fs.writeFileSync(rawPath, '<script data-odds-staging="explicit">null</script>', 'utf8');
    const inputs = writeInputs(t, rawPath, 'oddsportal-explicit-envelope-html');
    const result = invoke([
        '--source',
        rawPath,
        '--manifest',
        inputs.manifestPath,
        '--adapter',
        'oddsportal-explicit-envelope-html',
        '--candidates',
        inputs.candidatesPath,
    ]);
    assert.equal(result.status, EXIT_CODES.success);
    assert.equal(result.stderr, '');
    assert.equal(JSON.parse(result.stdout).quarantine_count, 1);
});
