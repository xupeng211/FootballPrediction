'use strict';

// lifecycle: permanent

const assert = require('node:assert/strict');
const test = require('node:test');
const { main, parseArgs } = require('../../scripts/ops/canonical_inventory_writer');

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
