'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const http = require('node:http');
const https = require('node:https');
const net = require('node:net');
const childProcess = require('node:child_process');
const Module = require('node:module');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const SCRIPT_PATH = path.join(PROJECT_ROOT, 'scripts/ops/single_target_acquisition_pre_network_runbook_validate.js');
const RUNBOOK_PATH = path.join(
    PROJECT_ROOT,
    'docs/runbooks/SINGLE_TARGET_ACQUISITION_PRE_NETWORK_DRY_RUN_RUNBOOK_TEMPLATE.md'
);
const ARTIFACT_SCHEMA = path.join(PROJECT_ROOT, 'schemas/acquisition/single_target_staging_artifact.schema.json');
const MANIFEST_SCHEMA = path.join(PROJECT_ROOT, 'schemas/acquisition/source_manifest_candidate.schema.json');
const SAMPLE_ARTIFACT = path.join(
    PROJECT_ROOT,
    'tests/fixtures/acquisition/sample_single_target_staging_artifact_phase480d.json'
);
const SAMPLE_MANIFEST = path.join(
    PROJECT_ROOT,
    'tests/fixtures/acquisition/sample_source_manifest_candidate_phase480d.json'
);
const RUNBOOK_TEXT = fs.readFileSync(RUNBOOK_PATH, 'utf8');

function loadValidatorFresh() {
    delete require.cache[SCRIPT_PATH];
    return require(SCRIPT_PATH);
}

function buildArgs(overrides = {}) {
    return {
        runbook: RUNBOOK_PATH,
        artifact_schema: ARTIFACT_SCHEMA,
        manifest_schema: MANIFEST_SCHEMA,
        artifact: SAMPLE_ARTIFACT,
        manifest: SAMPLE_MANIFEST,
        output_root: 'docs/_staging_preview/acquisition/single_target',
        target_source: 'fotmob',
        target_engine_family: 'titan_discovery',
        target_scope_type: 'match_id',
        target_match_id: 'sample-match-001',
        terms_approval: 'no',
        network_dry_run_authorization: 'no',
        allow_browser_runtime: 'no',
        allow_proxy_runtime: 'no',
        allow_external_network: 'no',
        allow_staging_write: 'no',
        confirm_single_target_scope: 'yes',
        staging_write_authorization: 'no',
        final_human_confirmation: 'no',
        ...overrides,
    };
}

function buildDependencies(overrides = {}) {
    return {
        cwd: PROJECT_ROOT,
        existsSync: targetPath => fs.existsSync(targetPath),
        readFileSync: (targetPath, encoding) => fs.readFileSync(targetPath, encoding),
        ...overrides,
    };
}

function installExecutionGuards(t) {
    const originalHttpRequest = http.request;
    const originalHttpsRequest = https.request;
    const originalFetch = global.fetch;
    const originalSpawn = childProcess.spawn;
    const originalExec = childProcess.exec;
    const originalExecFile = childProcess.execFile;
    const originalWriteFile = fs.writeFile;
    const originalWriteFileSync = fs.writeFileSync;
    const originalCreateWriteStream = fs.createWriteStream;
    const originalMkdir = fs.mkdir;
    const originalMkdirSync = fs.mkdirSync;
    const originalNetConnect = net.connect;
    const originalLoad = Module._load;
    const fail = name => () => {
        throw new Error(`${name} should not be called by single_target_acquisition_pre_network_runbook_validate`);
    };

    http.request = fail('http.request');
    https.request = fail('https.request');
    global.fetch = fail('global.fetch');
    childProcess.spawn = fail('child_process.spawn');
    childProcess.exec = fail('child_process.exec');
    childProcess.execFile = fail('child_process.execFile');
    fs.writeFile = fail('fs.writeFile');
    fs.writeFileSync = fail('fs.writeFileSync');
    fs.createWriteStream = fail('fs.createWriteStream');
    fs.mkdir = fail('fs.mkdir');
    fs.mkdirSync = fail('fs.mkdirSync');
    net.connect = fail('net.connect');
    Module._load = function patchedLoad(request, parent, isMain) {
        const blockedImports = new Set([
            'http',
            'node:http',
            'https',
            'node:https',
            'child_process',
            'node:child_process',
            'pg',
            'redis',
            'ioredis',
            'playwright',
            'playwright-core',
        ]);
        if (blockedImports.has(request)) {
            throw new Error(`blocked import: ${request}`);
        }
        if (/titan_discovery|DiscoveryService|FixtureRepository/i.test(request)) {
            throw new Error(`blocked import: ${request}`);
        }
        return originalLoad.call(this, request, parent, isMain);
    };

    t.after(() => {
        http.request = originalHttpRequest;
        https.request = originalHttpsRequest;
        global.fetch = originalFetch;
        childProcess.spawn = originalSpawn;
        childProcess.exec = originalExec;
        childProcess.execFile = originalExecFile;
        fs.writeFile = originalWriteFile;
        fs.writeFileSync = originalWriteFileSync;
        fs.createWriteStream = originalCreateWriteStream;
        fs.mkdir = originalMkdir;
        fs.mkdirSync = originalMkdirSync;
        net.connect = originalNetConnect;
        Module._load = originalLoad;
    });
}

function replaceInTemplate(searchValue, replaceValue) {
    assert.match(RUNBOOK_TEXT, new RegExp(searchValue.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
    return RUNBOOK_TEXT.replace(searchValue, replaceValue);
}

function removeLineFromTemplate(line) {
    return RUNBOOK_TEXT.replace(`${line}\n`, '');
}

function withTempRunbook(markdownText, callback) {
    const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'phase483d-'));
    const runbookPath = path.join(tempDir, 'runbook.md');
    fs.writeFileSync(runbookPath, markdownText, 'utf8');
    try {
        callback(runbookPath);
    } finally {
        fs.rmSync(tempDir, { recursive: true, force: true });
    }
}

function runMain(gate, argv, dependencies = buildDependencies()) {
    let stdout = '';
    let stderr = '';
    const status = gate.main(
        argv,
        {
            stdout: text => {
                stdout += text;
            },
            stderr: text => {
                stderr += text;
            },
        },
        dependencies
    );
    return { status, stdout, stderr };
}

function extractLastJsonObject(stdout) {
    const trimmed = String(stdout || '').trim();
    const startIndex = trimmed.lastIndexOf('\n{');
    const jsonText = startIndex >= 0 ? trimmed.slice(startIndex + 1) : trimmed;
    return JSON.parse(jsonText);
}

test('缺 runbook 参数时失败', () => {
    const gate = loadValidatorFresh();
    const args = buildArgs();
    delete args.runbook;
    const payload = gate.runValidation(args, buildDependencies());

    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /missing runbook path/i);
});

test('runbook 缺 YAML block 失败', () => {
    const gate = loadValidatorFresh();
    withTempRunbook('# no yaml\n', runbookPath => {
        const payload = gate.runValidation({ ...buildArgs(), runbook: runbookPath }, buildDependencies());
        assert.equal(payload.ok, false);
        assert.match(payload.errors.join('\n'), /missing YAML block/i);
    });
});

test('runbook invalid YAML 失败', () => {
    const gate = loadValidatorFresh();
    withTempRunbook('```yaml\nnot yaml\n```\n', runbookPath => {
        const payload = gate.runValidation({ ...buildArgs(), runbook: runbookPath }, buildDependencies());
        assert.equal(payload.ok, false);
        assert.match(payload.errors.join('\n'), /unsupported YAML line/i);
    });
});

test('runbook missing phase 失败', () => {
    const gate = loadValidatorFresh();
    withTempRunbook(
        removeLineFromTemplate('phase: PHASE4.83D_SINGLE_TARGET_ACQUISITION_PRE_NETWORK_RUNBOOK_DRAFT'),
        runbookPath => {
            const payload = gate.runValidation({ ...buildArgs(), runbook: runbookPath }, buildDependencies());
            assert.equal(payload.ok, false);
            assert.match(payload.errors.join('\n'), /missing required fields: phase/);
        }
    );
});

test('runbook missing runbook_status 失败', () => {
    const gate = loadValidatorFresh();
    withTempRunbook(removeLineFromTemplate('runbook_status: draft_only'), runbookPath => {
        const payload = gate.runValidation({ ...buildArgs(), runbook: runbookPath }, buildDependencies());
        assert.equal(payload.ok, false);
        assert.match(payload.errors.join('\n'), /runbook_status/);
    });
});

test('runbook_status 非 draft_only 失败', () => {
    const gate = loadValidatorFresh();
    withTempRunbook(replaceInTemplate('runbook_status: draft_only', 'runbook_status: approved'), runbookPath => {
        const payload = gate.runValidation({ ...buildArgs(), runbook: runbookPath }, buildDependencies());
        assert.equal(payload.ok, false);
        assert.match(payload.errors.join('\n'), /draft_only/);
    });
});

test('network_dry_run_ready=true 失败', () => {
    const gate = loadValidatorFresh();
    withTempRunbook(replaceInTemplate('network_dry_run_ready: false', 'network_dry_run_ready: true'), runbookPath => {
        const payload = gate.runValidation({ ...buildArgs(), runbook: runbookPath }, buildDependencies());
        assert.equal(payload.ok, false);
        assert.match(payload.errors.join('\n'), /network_dry_run_ready must remain false/);
    });
});

test('network_dry_run_authorized=true 失败', () => {
    const gate = loadValidatorFresh();
    withTempRunbook(
        replaceInTemplate('network_dry_run_authorized: false', 'network_dry_run_authorized: true'),
        runbookPath => {
            const payload = gate.runValidation({ ...buildArgs(), runbook: runbookPath }, buildDependencies());
            assert.equal(payload.ok, false);
            assert.match(payload.errors.join('\n'), /network_dry_run_authorized true in template/);
        }
    );
});

test('staging_write_authorized=true 失败', () => {
    const gate = loadValidatorFresh();
    withTempRunbook(
        replaceInTemplate('staging_write_authorized: false', 'staging_write_authorized: true'),
        runbookPath => {
            const payload = gate.runValidation({ ...buildArgs(), runbook: runbookPath }, buildDependencies());
            assert.equal(payload.ok, false);
            assert.match(payload.errors.join('\n'), /staging_write_authorized true in template/);
        }
    );
});

test('db_write_authorized=true 失败', () => {
    const gate = loadValidatorFresh();
    withTempRunbook(replaceInTemplate('db_write_authorized: false', 'db_write_authorized: true'), runbookPath => {
        const payload = gate.runValidation({ ...buildArgs(), runbook: runbookPath }, buildDependencies());
        assert.equal(payload.ok, false);
        assert.match(payload.errors.join('\n'), /db_write_authorized true in template/);
    });
});

test('training_authorized=true 失败', () => {
    const gate = loadValidatorFresh();
    withTempRunbook(replaceInTemplate('training_authorized: false', 'training_authorized: true'), runbookPath => {
        const payload = gate.runValidation({ ...buildArgs(), runbook: runbookPath }, buildDependencies());
        assert.equal(payload.ok, false);
        assert.match(payload.errors.join('\n'), /training_authorized true in template/);
    });
});

test('prediction_authorized=true 失败', () => {
    const gate = loadValidatorFresh();
    withTempRunbook(replaceInTemplate('prediction_authorized: false', 'prediction_authorized: true'), runbookPath => {
        const payload = gate.runValidation({ ...buildArgs(), runbook: runbookPath }, buildDependencies());
        assert.equal(payload.ok, false);
        assert.match(payload.errors.join('\n'), /prediction_authorized true in template/);
    });
});

test('final_human_confirmation=true 失败', () => {
    const gate = loadValidatorFresh();
    withTempRunbook(
        replaceInTemplate('final_human_confirmation: false', 'final_human_confirmation: true'),
        runbookPath => {
            const payload = gate.runValidation({ ...buildArgs(), runbook: runbookPath }, buildDependencies());
            assert.equal(payload.ok, false);
            assert.match(payload.errors.join('\n'), /final_human_confirmation true in template/);
        }
    );
});

test('缺 artifact schema 失败', () => {
    const gate = loadValidatorFresh();
    const args = buildArgs();
    delete args.artifact_schema;
    const payload = gate.runValidation(args, buildDependencies());
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /missing runbook path or required CLI values/i);
});

test('缺 manifest schema 失败', () => {
    const gate = loadValidatorFresh();
    const args = buildArgs();
    delete args.manifest_schema;
    const payload = gate.runValidation(args, buildDependencies());
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /required CLI values/i);
});

test('缺 artifact 失败', () => {
    const gate = loadValidatorFresh();
    const args = buildArgs();
    delete args.artifact;
    const payload = gate.runValidation(args, buildDependencies());
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /required CLI values/i);
});

test('缺 manifest 失败', () => {
    const gate = loadValidatorFresh();
    const args = buildArgs();
    delete args.manifest;
    const payload = gate.runValidation(args, buildDependencies());
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /required CLI values/i);
});

test('packet preview validation failure 失败', () => {
    const gate = loadValidatorFresh();
    const args = buildArgs({ target_match_id: 'wrong-match-id' });
    const payload = gate.runValidation(args, buildDependencies());
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /packet preview failed/i);
});

test('target_source mismatch 失败', () => {
    const gate = loadValidatorFresh();
    withTempRunbook(replaceInTemplate('  target_source:', '  target_source: other'), runbookPath => {
        const payload = gate.runValidation({ ...buildArgs(), runbook: runbookPath }, buildDependencies());
        assert.equal(payload.ok, false);
        assert.match(payload.errors.join('\n'), /target mismatch/i);
    });
});

test('unsupported engine family 失败', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(buildArgs({ target_engine_family: 'run_production' }), buildDependencies());
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /unsupported engine family/);
});

test('unsupported scope type bulk 失败', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(buildArgs({ target_scope_type: 'bulk' }), buildDependencies());
    assert.equal(payload.ok, false);
    assert.match(payload.errors.join('\n'), /unsupported scope type "bulk"|unsupported scope type bulk/);
});

test('valid runbook validate 成功', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(buildArgs(), buildDependencies());

    assert.equal(payload.ok, true);
    assert.equal(payload.phase, 'PHASE4.83D_SINGLE_TARGET_ACQUISITION_PRE_NETWORK_RUNBOOK_DRAFT');
    assert.equal(payload.runbook_draft_only, true);
    assert.equal(payload.runbook_valid, true);
    assert.equal(payload.packet_preview_passed, true);
    assert.equal(payload.network_dry_run_ready, false);
    assert.equal(payload.network_dry_run_authorized, false);
    assert.equal(payload.staging_write_authorized, false);
    assert.equal(payload.db_write_authorized, false);
    assert.equal(payload.training_authorized, false);
    assert.equal(payload.prediction_authorized, false);
    assert.equal(payload.would_access_network, false);
    assert.equal(payload.would_launch_browser, false);
    assert.equal(payload.would_use_proxy, false);
    assert.equal(payload.would_execute_engine, false);
    assert.equal(payload.would_write_staging, false);
    assert.equal(payload.would_create_staging_directory, false);
    assert.equal(payload.would_write_source_manifest, false);
    assert.equal(payload.would_write_packet_file, false);
    assert.equal(payload.would_write_db, false);
    assert.equal(payload.would_train, false);
    assert.equal(payload.would_predict, false);
    assert.equal(payload.would_spawn_child_process, false);
    assert.equal(payload.commit_gate, 'blocked');
});

test('all authorization yes in CLI 仍 no-op / not authorized', () => {
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(
        buildArgs({
            terms_approval: 'yes',
            network_dry_run_authorization: 'yes',
            allow_browser_runtime: 'yes',
            allow_proxy_runtime: 'yes',
            allow_external_network: 'yes',
            allow_staging_write: 'yes',
            staging_write_authorization: 'yes',
            final_human_confirmation: 'yes',
        }),
        buildDependencies()
    );

    assert.equal(payload.ok, true);
    assert.equal(payload.network_dry_run_authorized, false);
    assert.equal(payload.staging_write_authorized, false);
    assert.equal(payload.db_write_authorized, false);
    assert.equal(payload.would_access_network, false);
    assert.equal(payload.would_launch_browser, false);
    assert.equal(payload.would_use_proxy, false);
    assert.equal(payload.would_execute_engine, false);
    assert.equal(payload.would_write_staging, false);
    assert.equal(payload.would_write_db, false);
});

test('--commit blocked', () => {
    const gate = loadValidatorFresh();
    const result = runMain(gate, ['--runbook', RUNBOOK_PATH, '--commit'], buildDependencies());

    assert.equal(result.status, 1);
    const payload = JSON.parse(result.stdout);
    assert.match(payload.errors.join('\n'), /not wired in Phase 4.83D/);
});

test('Makefile validate 成功', () => {
    const result = childProcess.spawnSync(
        'make',
        [
            'data-single-target-acquisition-pre-network-runbook-validate',
            'PRE_NETWORK_RUNBOOK_NODE=node',
            `RUNBOOK=${RUNBOOK_PATH}`,
            `ARTIFACT_SCHEMA=${ARTIFACT_SCHEMA}`,
            `MANIFEST_SCHEMA=${MANIFEST_SCHEMA}`,
            `ARTIFACT=${SAMPLE_ARTIFACT}`,
            `MANIFEST=${SAMPLE_MANIFEST}`,
            'OUTPUT_ROOT=docs/_staging_preview/acquisition/single_target',
            'TARGET_SOURCE=fotmob',
            'TARGET_ENGINE_FAMILY=titan_discovery',
            'TARGET_SCOPE_TYPE=match_id',
            'TARGET_MATCH_ID=sample-match-001',
            'TERMS_APPROVAL=no',
            'NETWORK_DRY_RUN_AUTHORIZATION=no',
            'ALLOW_BROWSER_RUNTIME=no',
            'ALLOW_PROXY_RUNTIME=no',
            'ALLOW_EXTERNAL_NETWORK=no',
            'ALLOW_STAGING_WRITE=no',
            'CONFIRM_SINGLE_TARGET_SCOPE=yes',
            'STAGING_WRITE_AUTHORIZATION=no',
            'FINAL_HUMAN_CONFIRMATION=no',
        ],
        {
            cwd: PROJECT_ROOT,
            encoding: 'utf8',
            shell: false,
        }
    );

    assert.equal(result.status, 0, result.stderr);
    const payload = extractLastJsonObject(result.stdout);
    assert.equal(payload.ok, true);
});

test('Makefile commit blocked', () => {
    const result = childProcess.spawnSync(
        'make',
        [
            'data-single-target-acquisition-pre-network-runbook-commit',
            'CONFIRM_SINGLE_TARGET_ACQUISITION_PRE_NETWORK_RUNBOOK=1',
        ],
        {
            cwd: PROJECT_ROOT,
            encoding: 'utf8',
            shell: false,
        }
    );

    assert.notEqual(result.status, 0);
    assert.match(result.stdout, /not wired in Phase 4.83D/);
});

test('不访问网络', t => {
    installExecutionGuards(t);
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(buildArgs(), buildDependencies());
    assert.equal(payload.ok, true);
    assert.equal(payload.would_access_network, false);
});

test('不启动 browser', t => {
    installExecutionGuards(t);
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(buildArgs(), buildDependencies());
    assert.equal(payload.ok, true);
    assert.equal(payload.would_launch_browser, false);
});

test('不执行 proxy runtime', t => {
    installExecutionGuards(t);
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(buildArgs(), buildDependencies());
    assert.equal(payload.ok, true);
    assert.equal(payload.would_use_proxy, false);
});

test('不执行 engine', t => {
    installExecutionGuards(t);
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(buildArgs(), buildDependencies());
    assert.equal(payload.ok, true);
    assert.equal(payload.would_execute_engine, false);
});

test('不写 staging', t => {
    installExecutionGuards(t);
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(buildArgs(), buildDependencies());
    assert.equal(payload.ok, true);
    assert.equal(payload.would_write_staging, false);
});

test('不创建目录', t => {
    installExecutionGuards(t);
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(buildArgs(), buildDependencies());
    assert.equal(payload.ok, true);
    assert.equal(payload.would_create_staging_directory, false);
});

test('不写 source manifest', t => {
    installExecutionGuards(t);
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(buildArgs(), buildDependencies());
    assert.equal(payload.ok, true);
    assert.equal(payload.would_write_source_manifest, false);
});

test('不写 packet file', t => {
    installExecutionGuards(t);
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(buildArgs(), buildDependencies());
    assert.equal(payload.ok, true);
    assert.equal(payload.would_write_packet_file, false);
});

test('不写 DB', t => {
    installExecutionGuards(t);
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(buildArgs(), buildDependencies());
    assert.equal(payload.ok, true);
    assert.equal(payload.would_write_db, false);
});

test('不 spawn child process', t => {
    installExecutionGuards(t);
    const gate = loadValidatorFresh();
    const payload = gate.runValidation(buildArgs(), buildDependencies());
    assert.equal(payload.ok, true);
    assert.equal(payload.would_spawn_child_process, false);
});

test('source audit: 不 import forbidden modules', () => {
    const source = fs.readFileSync(SCRIPT_PATH, 'utf8');
    assert.ok(!/require\s*\(\s*['"].*titan_discovery/.test(source));
    assert.ok(!/require\s*\(\s*['"].*DiscoveryService/.test(source));
    assert.ok(!/require\s*\(\s*['"].*FixtureRepository/.test(source));
    assert.ok(!/require\s*\(\s*['"]pg['"]/.test(source));
    assert.ok(!/require\s*\(\s*['"]redis['"]/.test(source));
    assert.ok(!/require\s*\(\s*['"]ioredis['"]/.test(source));
    assert.ok(!/require\s*\(\s*['"]playwright/.test(source));
});
