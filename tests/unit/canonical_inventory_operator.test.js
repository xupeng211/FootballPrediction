'use strict';

// lifecycle: permanent

const assert = require('node:assert/strict');
const test = require('node:test');
const { parseArgs } = require('../../scripts/ops/canonical_inventory_writer');

test('operator defaults to no write and exposes only the explicit disposable execution switch', () => {
    assert.equal(parseArgs(['--artifact', '/tmp/artifact.json', '--artifact-sha256', 'a'.repeat(64)]).execute, false);
    const execute = parseArgs(['--execute-disposable', '--operation', 'canonical_inventory_disposable_proof']);
    assert.equal(execute.execute, true);
    assert.equal(execute.operation, 'canonical_inventory_disposable_proof');
    assert.throws(() => parseArgs(['--force']), /requires a value/);
});
