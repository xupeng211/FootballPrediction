'use strict';
// lifecycle: permanent — canonical JS test discovery and exit-code contract coverage.

const assert = require('node:assert/strict');
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
