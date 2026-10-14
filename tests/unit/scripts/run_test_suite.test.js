'use strict';
// lifecycle: permanent — canonical JS test discovery and exit-code contract coverage.

const assert = require('node:assert/strict');
const { createHash } = require('node:crypto');
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const PROJECT_ROOT = path.resolve(__dirname, '../../..');
const runner = require('../../../scripts/test/run_test_suite');

function writeFile(filePath, content = '') {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    fs.writeFileSync(filePath, content, 'utf8');
}

test('递归收集测试文件、稳定排序且排除 fixture/coverage 目录', () => {
    const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'test-suite-discovery-'));
    try {
        writeFile(path.join(tempRoot, 'z.test.js'));
        writeFile(path.join(tempRoot, 'nested', 'a.test.js'));
        writeFile(path.join(tempRoot, 'fixtures', 'ignored.test.js'));
        writeFile(path.join(tempRoot, 'coverage', 'ignored.test.js'));
        writeFile(path.join(tempRoot, 'nested', 'not-a-test.js'));

        const files = runner.collectTestFiles(tempRoot);
        assert.deepEqual(
            files.map(file => path.relative(tempRoot, file)),
            ['nested/a.test.js', 'z.test.js'],
        );
        assert.equal(new Set(files).size, files.length);
    } finally {
        fs.rmSync(tempRoot, { recursive: true, force: true });
    }
});

test('当前 unit 根目录会纳入嵌套测试且不会重复收集', () => {
    const unitRoot = path.join(PROJECT_ROOT, 'tests', 'unit');
    const files = runner.collectTestFiles(unitRoot);
    const directFiles = fs
        .readdirSync(unitRoot, { withFileTypes: true })
        .filter(entry => entry.isFile() && entry.name.endsWith('.test.js'));

    assert.ok(files.length > directFiles.length);
    assert.ok(files.some(file => file.includes(`${path.sep}tests${path.sep}unit${path.sep}scripts${path.sep}ops${path.sep}`)));
    assert.equal(new Set(files).size, files.length);
});

test('静态仓库数据路径会进入 affected 测试依赖图', () => {
    const dependencies = runner.collectStaticProjectDataDependencies(
        [
            "const state = readText('docs/data/FOTMOB_CURRENT_STATE.md');",
            "const leagues = 'config/leagues.json';",
            "const outside = '../../outside.md';",
        ].join('\n'),
    );

    assert.deepEqual(
        dependencies.map(file => path.relative(PROJECT_ROOT, file)),
        ['config/leagues.json', 'docs/data/FOTMOB_CURRENT_STATE.md'],
    );

    const affected = runner.resolveAffectedTestFiles(
        ['docs/data/FOTMOB_CURRENT_STATE.md'],
        runner.collectTestFiles(path.join(PROJECT_ROOT, 'tests', 'unit')),
    );
    assert.ok(
        affected.some(file => file.endsWith('fotmob_ligue1_adg55_acceptance_mutation_planning.test.js')),
        'current-state 变更必须选中通过静态数据路径读取它的测试',
    );
});

test('相对 docs 字面量会按读取文件位置进入 affected 测试依赖图', () => {
    const reader = path.join(
        PROJECT_ROOT,
        'tests',
        'unit',
        'fotmob_ligue1_corrected_source_discovery_adg21.test.js',
    );
    const manifest = 'docs/_manifests/fotmob_ligue1_corrected_source_discovery.adg21.json';
    const dependencies = runner.collectStaticProjectDataDependencies(
        fs.readFileSync(reader, 'utf8'),
        reader,
    );

    assert.deepEqual(
        dependencies.map(file => path.relative(PROJECT_ROOT, file)),
        [manifest],
    );

    const affected = runner.resolveAffectedTestFiles(
        [manifest],
        runner.collectTestFiles(path.join(PROJECT_ROOT, 'tests', 'unit')),
    );
    assert.ok(
        affected.some(file => file.endsWith('fotmob_ligue1_corrected_source_discovery_adg21.test.js')),
        'manifest 变更必须选中通过相对 docs 路径读取它的测试',
    );
});

test('删除后的静态数据路径仍保留为 affected 反向依赖', () => {
    const reader = path.join(PROJECT_ROOT, 'tests', 'unit', 'selector_reader.test.js');
    const dependencies = runner.collectStaticProjectDataDependencies(
        [
            "const direct = 'docs/_manifests/deleted_by_pr.json';",
            "const relative = path.resolve(__dirname, '../../config/deleted_by_pr.json');",
            "const escaped = 'docs/../src/not_a_data_dependency.js';",
        ].join('\n'),
        reader,
    );

    assert.deepEqual(
        dependencies.map(file => path.relative(PROJECT_ROOT, file)),
        ['config/deleted_by_pr.json', 'docs/_manifests/deleted_by_pr.json'],
    );
});

test('拆分 path.join 构造的数据文件会进入 affected 测试依赖图', () => {
    const reader = path.join(
        PROJECT_ROOT,
        'tests',
        'unit',
        'fotmob_ligue1_adg60_next_batch_no_write_authorization.test.js',
    );
    const manifest = 'docs/_manifests/fotmob_ligue1_adg60_next_batch_no_write_authorization.json';
    const dependencies = runner.collectStaticProjectDataDependencies(
        fs.readFileSync(reader, 'utf8'),
        reader,
    );

    assert.ok(
        dependencies.some(file => path.relative(PROJECT_ROOT, file) === manifest),
        'join(ROOT, dataDirectory, filename) 的字面量调用必须保留具体文件依赖',
    );

    const affected = runner.resolveAffectedTestFiles(
        [manifest],
        runner.collectTestFiles(path.join(PROJECT_ROOT, 'tests', 'unit')),
    );
    assert.ok(
        affected.some(file => file.endsWith('fotmob_ligue1_adg60_next_batch_no_write_authorization.test.js')),
        'manifest 变更必须选中通过拆分 path.join 构造读取它的测试',
    );
});

test('单行 path.resolve helper 构造的数据文件会进入 affected 测试依赖图', () => {
    const reader = path.join(
        PROJECT_ROOT,
        'tests',
        'unit',
        'fotmob_ligue1_controlled_correction_application_adg27.test.js',
    );
    const manifest = 'docs/_manifests/fotmob_ligue1_corrected_source_inventory.adg27.json';
    const dependencies = runner.collectStaticProjectDataDependencies(
        fs.readFileSync(reader, 'utf8'),
        reader,
    );

    assert.ok(
        dependencies.some(file => path.relative(PROJECT_ROOT, file) === manifest),
        '单行 path.resolve helper 的字面量调用必须保留具体文件依赖',
    );

    const affected = runner.resolveAffectedTestFiles(
        [manifest],
        runner.collectTestFiles(path.join(PROJECT_ROOT, 'tests', 'unit')),
    );
    assert.ok(
        affected.some(file => file.endsWith('fotmob_ligue1_controlled_correction_application_adg27.test.js')),
        'manifest 变更必须选中通过单行 path.resolve helper 读取它的测试',
    );
});

test('全字面量分段 path.join 构造的数据文件会进入 affected 测试依赖图', () => {
    const reader = path.join(PROJECT_ROOT, 'scripts', 'ops', 'total_war_pipeline.js');
    const config = 'config/recon_config.json';
    const dependencies = runner.collectStaticProjectDataDependencies(
        fs.readFileSync(reader, 'utf8'),
        reader,
    );

    assert.ok(
        dependencies.some(file => path.relative(PROJECT_ROOT, file) === config),
        'path.join(ROOT, config, filename) 的全字面量构造必须保留具体文件依赖',
    );

    const affected = runner.resolveAffectedTestFiles(
        [config],
        runner.collectTestFiles(path.join(PROJECT_ROOT, 'tests', 'unit')),
    );
    assert.ok(
        affected.some(file => file.endsWith('TotalWarPipeline.Config.test.js')),
        'config 变更必须选中通过全字面量 path.join 读取它的测试',
    );
});

test('空测试集合返回非零，不静默成功', () => {
    assert.equal(runner.runNodeTests([], { label: '空测试集合行为测试' }), 1);
});

test('子测试失败时 runner 传递非零退出码', () => {
    const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'test-suite-failure-'));
    try {
        const failingTest = path.join(tempRoot, 'failing.test.js');
        writeFile(
            failingTest,
            "const test = require('node:test'); test('intentional failure', () => { throw new Error('intentional failure'); });\n",
        );

        assert.notEqual(
            runner.runNodeTests([failingTest], { label: '失败退出码行为测试' }),
            0,
        );
    } finally {
        fs.rmSync(tempRoot, { recursive: true, force: true });
    }
});

test('临时测试输出不会修改仓库工作树', () => {
    const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'test-suite-isolation-'));
    const before = runner.snapshotWorkspaceStatus();
    try {
        const isolatedTest = path.join(tempRoot, 'isolated.test.js');
        writeFile(
            isolatedTest,
            "const fs = require('node:fs'); const path = require('node:path'); const test = require('node:test'); test('writes only to runner temp dir', () => fs.writeFileSync(path.join(process.env.FP_TEST_TMP_DIR, 'child.txt'), 'ok'));\n",
        );

        assert.equal(runner.runNodeTests([isolatedTest], { label: '隔离行为测试' }), 0);
    } finally {
        fs.rmSync(tempRoot, { recursive: true, force: true });
    }

    const after = runner.snapshotWorkspaceStatus();
    assert.equal(before.ok, true);
    assert.equal(after.ok, true);
    assert.equal(after.status, before.status);
});

test('CLI runner 会在退出前刷新完整的子测试输出', () => {
    const result = spawnSync(
        process.execPath,
        [path.join(PROJECT_ROOT, 'scripts/test/run_test_suite.js'), 'affected', 'src/infrastructure/browser/BrowserFactory.js'],
        {
            cwd: PROJECT_ROOT,
            encoding: 'utf8',
            env: { ...process.env },
            maxBuffer: 100 * 1024 * 1024,
        },
    );

    assert.equal(result.error, undefined);
    assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
    assert.match(
        `${result.stdout}\n${result.stderr}`,
        /\[TEST-GATE\] 增量 JS 测试通过/,
    );
});

// 有界离线反例：每个子进程 128MiB heap、10s、每条捕获流最多 2MiB。
function runOutputChild(source) {
    const result = spawnSync(process.execPath, ['--max-old-space-size=128', '-e', source], {
        cwd: PROJECT_ROOT,
        env: { ...process.env, NODE_OPTIONS: '--max-old-space-size=128' },
        timeout: 10000,
        maxBuffer: 2 * 1024 * 1024,
    });
    assert.ifError(result.error);
    return result;
}

function sha256(buffer) {
    return createHash('sha256').update(buffer).digest('hex');
}

function outputFixture(t, source) {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'test-suite-output-'));
    t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    const file = path.join(root, 'output.test.js');
    writeFile(file, source);
    return { root, file };
}

test('子测试临时目录按批次隔离，覆盖率使用工作区且成功/失败都完整清理', t => {
    const before = runner.snapshotWorkspaceStatus();
    const parentTmpDir = os.tmpdir();
    for (const coverage of [false, true]) {
        const fixture = outputFixture(t, '');
        const recorded = path.join(fixture.root, 'temp-paths.json');
        const unused = coverage
            ? Array.from({ length: 100 }, (_, i) => `function unused${i}() { return ${i}; }`).join('\n')
            : '';
        writeFile(fixture.file, `${unused}\n
            const fs = require('node:fs');
            const os = require('node:os');
            const path = require('node:path');
            require('node:test')('leaves a temporary fixture for batch cleanup', () => {
                const tmp = os.tmpdir();
                const root = process.env.FP_TEST_TMP_DIR;
                fs.writeFileSync(${JSON.stringify(recorded)}, JSON.stringify({
                    tmp, root, rawCoverage: process.env.NODE_V8_COVERAGE,
                }));
                fs.writeFileSync(path.join(tmp, 'unremoved-fixture'), '保留到批次清理');
                fs.mkdirSync(path.join(root, '.stage-d-runtime-trust'));
            });
        `);
        const result = runOutputChild(`
            const runner = require('./scripts/test/run_test_suite');
            process.exitCode = runner.runNodeTests([${JSON.stringify(fixture.file)}], { coverage: ${coverage} });
        `);
        assert.equal(result.status, coverage ? 1 : 0, result.stderr.toString());
        assert.match(result.stdout.toString(), /# pass 1\n# fail 0/);
        if (coverage) assert.match(`${result.stdout}${result.stderr}`, /coverage.*threshold|覆盖率未达标/i);
        const paths = JSON.parse(fs.readFileSync(recorded, 'utf8'));
        assert.equal(paths.tmp, path.join(paths.root, 'tmp'));
        assert.equal(path.dirname(paths.root), parentTmpDir);
        assert.ok(!paths.tmp.startsWith(PROJECT_ROOT + path.sep));
        if (coverage) {
            assert.equal(path.dirname(path.dirname(path.dirname(paths.rawCoverage))),
                path.join(PROJECT_ROOT, 'reports', 'coverage', 'node'));
            assert.notEqual(path.dirname(paths.rawCoverage), paths.tmp);
            assert.match(path.basename(paths.rawCoverage), /^node-coverage-/);
            assert.equal(fs.existsSync(paths.rawCoverage), false);
            assert.equal(fs.existsSync(path.dirname(path.dirname(paths.rawCoverage))), false);
        }
        assert.equal(fs.existsSync(paths.root), false);
        assert.equal(os.tmpdir(), parentTmpDir);
    }
    assert.deepEqual(runner.snapshotWorkspaceStatus(), before);
});

test('真实进程和管道完整转发超过 64KiB 的 UTF-8 stdout/stderr', t => {
    const stdout = Buffer.from(`${'中文🙂stdout完整字节'.repeat(8192)}\nSTDOUT_TAIL_完成\n`);
    const stderr = Buffer.from(`${'诊断🚦stderr完整字节'.repeat(8192)}\nSTDERR_TAIL_完成\n`);
    assert.ok(stdout.length > 65536 && stderr.length > 65536);
    const fixture = outputFixture(t, '');
    const metricsPath = path.join(fixture.root, 'pipe-write-metrics.json');
    const producer = "process.stdout.write('中文🙂stdout完整字节'.repeat(8192) + '\\nSTDOUT_TAIL_完成\\n');"
        + "process.stderr.write('诊断🚦stderr完整字节'.repeat(8192) + '\\nSTDERR_TAIL_完成\\n');";
    const result = runOutputChild(`
        const fs = require('node:fs');
        const { spawnSync } = require('node:child_process');
        const runner = require('./scripts/test/run_test_suite');
        const child = spawnSync(process.execPath, ['--max-old-space-size=128', '-e', ${JSON.stringify(producer)}], {
            encoding: 'utf8', timeout: 5000, maxBuffer: 1024 * 1024
        });
        if (child.error) throw child.error;
        if (child.status !== 0) throw new Error('producer failed');
        const original = fs.writeSync;
        const metrics = { calls: 0, partial: 0, temporary_errors: 0 };
        fs.writeSync = (fd, buffer, offset, length) => {
            metrics.calls++;
            try {
                const written = original(fd, buffer, offset, length);
                if (written < length) metrics.partial++;
                return written;
            } catch (error) {
                if (['EINTR', 'EAGAIN', 'EWOULDBLOCK'].includes(error.code)) metrics.temporary_errors++;
                throw error;
            }
        };
        try {
            runner.writeCompleteOutputSync(1, child.stdout);
            runner.writeCompleteOutputSync(2, child.stderr);
        } finally {
            fs.writeSync = original;
            fs.writeFileSync(${JSON.stringify(metricsPath)}, JSON.stringify(metrics));
        }
    `);
    assert.equal(result.status, 0, result.stderr.toString().slice(-1000));
    assert.equal(result.stdout.length, stdout.length);
    assert.equal(result.stderr.length, stderr.length);
    assert.equal(sha256(result.stdout), sha256(stdout));
    assert.equal(sha256(result.stderr), sha256(stderr));
    assert.deepEqual(result.stdout, stdout);
    assert.deepEqual(result.stderr, stderr);
    assert.ok(result.stdout.toString().endsWith('STDOUT_TAIL_完成\n'));
    assert.ok(result.stderr.toString().endsWith('STDERR_TAIL_完成\n'));
    t.diagnostic(JSON.stringify({
        long_stdout: { bytes: stdout.length, expected_sha256: sha256(stdout), actual_sha256: sha256(result.stdout), tail: true },
        long_stderr: { bytes: stderr.length, expected_sha256: sha256(stderr), actual_sha256: sha256(result.stderr), tail: true },
        actual_pipe_writes: JSON.parse(fs.readFileSync(metricsPath, 'utf8')),
    }));
});

test('短写按实际字节偏移推进，跨中文和 emoji 字节不重复不丢失', t => {
    const expected = Buffer.from('中文🙂短写\nTAIL_完整');
    for (const fd of [1, 2]) {
        const pieces = [];
        let nextOffset = 0;
        t.mock.method(fs, 'writeSync', (actualFd, buffer, offset, length) => {
            assert.equal(actualFd, fd);
            assert.equal(offset, nextOffset);
            assert.equal(length, expected.length - offset);
            const written = Math.min(3, length);
            pieces.push(Buffer.from(buffer.subarray(offset, offset + written)));
            nextOffset += written;
            return written;
        });
        try {
            runner.writeCompleteOutputSync(fd, expected.toString());
        } finally {
            t.mock.restoreAll();
        }
        assert.deepEqual(Buffer.concat(pieces), expected);
        assert.equal(nextOffset, expected.length);
    }
});

test('EINTR/EAGAIN/EWOULDBLOCK 等待后重试同一偏移并完成输出', t => {
    for (const code of ['EINTR', 'EAGAIN', 'EWOULDBLOCK']) {
        const expected = Buffer.from('中断恢复🙂');
        const pieces = [];
        const waits = [];
        let attempts = 0;
        t.mock.method(fs, 'writeSync', (fd, buffer, offset, length) => {
            if (attempts++ === 0) {
                assert.equal(offset, 0);
                throw Object.assign(new Error(code), { code });
            }
            const written = Math.min(2, length);
            pieces.push(Buffer.from(buffer.subarray(offset, offset + written)));
            return written;
        });
        t.mock.method(Atomics, 'wait', (array, index, value, milliseconds) => waits.push(milliseconds));
        try {
            runner.writeCompleteOutputSync(1, expected.toString());
        } finally {
            t.mock.restoreAll();
        }
        assert.deepEqual(Buffer.concat(pieces), expected);
        assert.deepEqual(waits, [10]);
    }
});

test('持续暂时错误有界失败，每次重试等待而不忙等', t => {
    for (const code of ['EINTR', 'EAGAIN', 'EWOULDBLOCK']) {
        let attempts = 0;
        const waits = [];
        const error = Object.assign(new Error(code), { code });
        t.mock.method(fs, 'writeSync', () => { attempts++; throw error; });
        t.mock.method(Atomics, 'wait', (array, index, value, milliseconds) => waits.push(milliseconds));
        try {
            assert.throws(() => runner.writeCompleteOutputSync(2, '仍未输出'), value => value === error);
        } finally {
            t.mock.restoreAll();
        }
        assert.equal(attempts, 101);
        assert.equal(waits.length, 100);
        assert.ok(waits.every(milliseconds => milliseconds === 10));
    }
});

test('零进展和非法字节数显式失败，不静默丢失或无限循环', t => {
    for (const written of [0, -1, NaN, 1000]) {
        let attempts = 0;
        t.mock.method(fs, 'writeSync', () => { attempts++; return written; });
        try {
            assert.throws(() => runner.writeCompleteOutputSync(1, '字节'), /未取得有效字节进展/);
        } finally {
            t.mock.restoreAll();
        }
        assert.equal(attempts, 1);
    }
});

test('EPIPE/EIO 永久错误立即传播，不尝试掩盖失败', t => {
    for (const code of ['EPIPE', 'EIO']) {
        let attempts = 0;
        const error = Object.assign(new Error(code), { code });
        t.mock.method(fs, 'writeSync', () => { attempts++; throw error; });
        try {
            assert.throws(() => runner.writeCompleteOutputSync(2, '未写出的诊断'), value => value === error);
        } finally {
            t.mock.restoreAll();
        }
        assert.equal(attempts, 1);
    }
});

test('真实子测试成功但输出失败时 runner 进程非零退出且工作区不变', t => {
    const fixture = outputFixture(t, "require('node:test')('passes', () => {});\n");
    const before = runner.snapshotWorkspaceStatus();
    const result = runOutputChild(`
        const fs = require('node:fs');
        const runner = require('./scripts/test/run_test_suite');
        fs.writeSync = () => { throw Object.assign(new Error('broken pipe'), { code: 'EPIPE' }); };
        process.exitCode = runner.runNodeTests([${JSON.stringify(fixture.file)}], { label: '输出失败反例' });
    `);
    assert.equal(result.status, 1);
    assert.match(result.stderr.toString(), /broken pipe/);
    assert.doesNotMatch(result.stdout.toString(), /输出失败反例通过/);
    assert.deepEqual(runner.snapshotWorkspaceStatus(), before);
});

test('runNodeTests 长 TAP 保留尾部统计；原失败摘要和覆盖率门禁仍传播非零', t => {
    const payload = `${'真实TAP中文🙂'.repeat(8192)}TAP_OUTPUT_TAIL`;
    const passing = outputFixture(t, `require('node:test')('long pass', () => console.log(${JSON.stringify(payload)}));\n`);
    const invoke = (file, options, nativeTapPath) => runOutputChild(`
        const nativeTapPath = ${JSON.stringify(nativeTapPath)};
        const fixturePath = ${JSON.stringify(file)};
        const childProcess = require('node:child_process');
        const originalSpawnSync = childProcess.spawnSync;
        let matchCount = 0;
        const observedProcesses = [];
        if (nativeTapPath) {
            // 只记录真实子进程结果，不替换执行或改写返回值。
            childProcess.spawnSync = (command, argv, spawnOptions) => {
                const matches = command === 'node' && Array.isArray(argv)
                    && argv.includes('--test')
                    && argv.some(arg => require('node:path').resolve(
                        spawnOptions?.cwd || process.cwd(), arg
                    ) === fixturePath);
                observedProcesses.push({ command, argv, captured: matches });
                if (matches && ++matchCount !== 1) throw new Error('目标测试进程多次命中');
                const result = originalSpawnSync(command, argv, spawnOptions);
                if (matches) {
                    require('node:fs').writeFileSync(nativeTapPath, result.stdout || '', { flag: 'wx' });
                }
                return result;
            };
        }
        try {
            const runner = require('./scripts/test/run_test_suite');
            process.exitCode = runner.runNodeTests([fixturePath], ${JSON.stringify(options)});
            if (nativeTapPath && matchCount !== 1) throw new Error('目标测试进程未命中');
        } finally {
            childProcess.spawnSync = originalSpawnSync;
            if (nativeTapPath) require('node:fs').writeFileSync(nativeTapPath + '.json', JSON.stringify({
                matchCount, observedProcesses, restored: childProcess.spawnSync === originalSpawnSync
            }));
        }
    `);
    const nativeTapPath = path.join(passing.root, 'native-tap.stdout');
    const passed = invoke(passing.file, { label: '长 TAP 回归' }, nativeTapPath);
    assert.equal(passed.status, 0);
    const capture = JSON.parse(fs.readFileSync(nativeTapPath + '.json', 'utf8'));
    assert.equal(capture.matchCount, 1);
    assert.equal(capture.observedProcesses.filter(item => item.captured).length, 1);
    assert.ok(capture.observedProcesses.some(item => item.command === 'git' && !item.captured));
    assert.equal(capture.restored, true);
    // 原生 TAP 会把长 console.log 分为多条注释；比较真实 reporter 的完整字节。
    const nativeTap = fs.readFileSync(nativeTapPath);
    assert.ok(nativeTap.length > Buffer.byteLength(payload));
    assert.deepEqual(passed.stdout.subarray(0, nativeTap.length), nativeTap);
    assert.match(nativeTap.toString(), /^TAP version 13\n/);
    assert.match(nativeTap.toString(), /# [^\n]*TAP_OUTPUT_TAIL\n/);
    assert.match(nativeTap.toString(), /# tests 1\n# suites 0\n# pass 1\n# fail 0\n# cancelled 0\n# skipped 0\n# todo 0\n/);
    assert.match(passed.stdout.toString(), /# pass 1\n# fail 0/);
    assert.match(passed.stdout.toString(), /长 TAP 回归通过/);
    t.diagnostic(JSON.stringify({
        native_tap_bytes: nativeTap.length,
        native_tap_sha256: sha256(nativeTap),
        forwarded_tap_sha256: sha256(passed.stdout.subarray(0, nativeTap.length)),
        payload_bytes: Buffer.byteLength(payload),
        tail_and_statistics_preserved: true,
        capture,
    }));

    const failing = outputFixture(t, "require('node:test')('intentional output regression failure', () => { throw new Error('original failure preserved'); });\n");
    const failed = invoke(failing.file, { label: '失败摘要回归' });
    assert.equal(failed.status, 1);
    assert.match(failed.stderr.toString(), /首个失败用例: intentional output regression failure/);
    assert.match(failed.stderr.toString(), /original failure preserved/);

    const uncovered = outputFixture(t, `${Array.from({ length: 100 }, (_, i) => `function unused${i}() { return ${i}; }`).join('\n')}\nrequire('node:test')('assertion passes but coverage fails', () => {});\n`);
    const coverage = invoke(uncovered.file, { coverage: true, label: '覆盖率门禁回归' });
    assert.notEqual(coverage.status, 0);
    assert.match(coverage.stdout.toString(), /# pass 1\n# fail 0/);
    assert.match(`${coverage.stdout}${coverage.stderr}`, /coverage.*threshold|覆盖率未达标/i);
    t.diagnostic('长 TAP 回归尾部统计完整；测试失败 exit=1；低覆盖率 fixture 被原门禁拒绝。');
});
