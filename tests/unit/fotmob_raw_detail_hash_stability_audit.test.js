'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const MODULE_PATH = path.join(PROJECT_ROOT, 'scripts/ops/fotmob_raw_detail_hash_stability_audit.js');

function loadFresh() {
    delete require.cache[MODULE_PATH];
    return require(MODULE_PATH);
}

test('audit blocks allow-network=yes and allow-db-write=yes', () => {
    const audit = loadFresh();
    const result = audit.runAudit({
        source: 'fotmob',
        externalId: '4830747',
        homeTeam: 'Auxerre',
        awayTeam: 'Nice',
        allowNetwork: true,
        allowDbWrite: true,
    });
    assert.equal(result.ok, false);
    assert.match(result.controlled_error, /allow-network=yes is blocked/);
});

test('audit proves stable hash ignores metadata drift but raw_data_with_meta_hash changes', () => {
    const audit = loadFresh();
    const result = audit.runAudit({
        source: 'fotmob',
        externalId: '4830747',
        homeTeam: 'Auxerre',
        awayTeam: 'Nice',
        allowNetwork: false,
        allowDbWrite: false,
    });
    assert.equal(result.ok, true);
    assert.equal(result.hash_strategy, 'stable_raw_payload_v1');
    assert.equal(result.stable_hash_unchanged_when_meta_changes, true);
    assert.equal(result.raw_data_with_meta_hash_changes_when_meta_changes, true);
    assert.equal(result.stable_hash_changes_when_payload_changes, true);
    assert.equal(result.match_id, '4830747');
    assert.equal(result.match_id_source, 'input_external_id_fallback');
    assert.equal(result.db_write_executed, false);
    assert.equal(result.network_used, false);
});

test('audit runCli help returns usage and invalid args return non-zero payload', async () => {
    const audit = loadFresh();
    let helpStdout = '';
    const helpStatus = await audit.runCli(['--help'], {
        stdout: text => {
            helpStdout += text;
        },
    });
    assert.equal(helpStatus, 0);
    assert.match(helpStdout, /Phase 5\.20L2D audit is local-only/);

    let invalidStdout = '';
    const invalidStatus = await audit.runCli(['--source=fotmob', '--external-id=bad'], {
        stdout: text => {
            invalidStdout += text;
        },
    });
    assert.equal(invalidStatus, 1);
    const payload = JSON.parse(invalidStdout);
    assert.equal(payload.ok, false);
    assert.match(payload.controlled_error, /external-id must be numeric/);
});
