'use strict';

// lifecycle: permanent

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const { main, parseArgs } = require('../../scripts/ops/canonical_inventory_writer');
const {
    buildDocument,
    parentMetadata,
    syntheticCandidates,
    writeDocument,
} = require('../helpers/canonicalInventoryFixtures');

test('operator defaults to no write and parses the deprecated execution switch only to fail closed', () => {
    assert.equal(parseArgs(['--artifact', '/tmp/artifact.json', '--artifact-sha256', 'a'.repeat(64)]).execute, false);
    const execute = parseArgs(['--execute-disposable', '--operation', 'canonical_inventory_disposable_proof']);
    assert.equal(execute.execute, true);
    assert.equal(execute.operation, 'canonical_inventory_disposable_proof');
    assert.throws(() => parseArgs(['--force']), /requires a value/);
});

test('direct operator execution fails before accepting a database target or receipt', async () => {
    await assert.rejects(
        () => main(['--execute-disposable', '--database-url', 'postgres://persistent.example/football_db']),
        /direct execution is disabled/
    );
});

test('no-write operator requires and forwards a physical parent artifact for bounded canaries', async () => {
    await assert.rejects(
        () =>
            main([
                '--artifact',
                '/tmp/child.json',
                '--artifact-sha256',
                'a'.repeat(64),
                '--parent-artifact',
                '/tmp/parent.json',
            ]),
        /must be provided together/
    );
    const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'fp-canonical-operator-'));
    try {
        const master = buildDocument(syntheticCandidates());
        const masterFile = writeDocument(directory, 'master.json', master);
        const canary = buildDocument(master.candidates.slice(0, 1), {
            kind: 'canary',
            parentMaster: parentMetadata(master, masterFile),
        });
        const canaryFile = writeDocument(directory, 'canary.json', canary);
        assert.equal(
            await main([
                '--artifact',
                canaryFile.path,
                '--artifact-sha256',
                canaryFile.sha256,
                '--parent-artifact',
                masterFile.path,
                '--parent-artifact-sha256',
                masterFile.sha256,
                '--target-classification',
                'disposable',
            ]),
            0
        );
    } finally {
        fs.rmSync(directory, { recursive: true, force: true });
    }
});
