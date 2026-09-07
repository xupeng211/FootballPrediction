'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

const modulePath = path.resolve(__dirname, '../../../scripts/ops/stage_c_the_odds_api_live_smoke.js');
const pathVariables = [
    'STAGE_C_FOTMOB_RAW_PATH',
    'STAGE_C_ODDS_RAW_PATH',
    'STAGE_C_ODDS_RECEIPT_PATH',
    'STAGE_C_IDENTITY_ALLOCATION_PATH',
];

function withConfiguredPaths(values, callback) {
    const previous = Object.fromEntries(pathVariables.map(name => [name, process.env[name]]));
    try {
        Object.assign(process.env, {
            STAGE_C_FOTMOB_RAW_PATH: values.fotmobRawPath,
            STAGE_C_ODDS_RAW_PATH: values.oddsRawPath,
            STAGE_C_ODDS_RECEIPT_PATH: values.receiptPath,
            STAGE_C_IDENTITY_ALLOCATION_PATH: values.allocationPath,
        });
        delete require.cache[modulePath];
        return callback(require(modulePath));
    } finally {
        for (const name of pathVariables) {
            if (previous[name] === undefined) delete process.env[name];
            else process.env[name] = previous[name];
        }
        delete require.cache[modulePath];
    }
}

function bundle(root) {
    return {
        fotmobRawPath: path.join(root, 'fotmob.html'),
        oddsRawPath: path.join(root, 'stale-odds.json'),
        receiptPath: path.join(root, 'stale-receipt.json'),
        allocationPath: path.join(root, 'allocation.json'),
    };
}

test('complete offline bundle remains selected without live capture', t => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'stage-c-live-paths-'));
    t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    const paths = bundle(root);
    for (const filePath of Object.values(paths)) fs.writeFileSync(filePath, 'fixture');

    withConfiguredPaths(paths, ({ offlineInputPaths }) => {
        assert.deepEqual(offlineInputPaths(), paths);
    });
});

test('fresh live capture preserves configured fixture and allocation inputs while replacing odds evidence', t => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'stage-c-live-paths-'));
    t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    const paths = bundle(root);
    fs.writeFileSync(paths.fotmobRawPath, 'fixture');
    fs.writeFileSync(paths.allocationPath, 'allocation');

    withConfiguredPaths(paths, ({ offlineInputPaths, liveCaptureInputPaths }) => {
        assert.equal(offlineInputPaths(), null, 'a stale/missing Odds bundle must not erase configured inputs');
        const livePaths = liveCaptureInputPaths({
            oddsRawPath: path.join(root, 'raw', 'content-addressed.json'),
            receiptPath: path.join(root, 'receipts', 'live.json'),
        });
        assert.equal(livePaths.fotmobRawPath, paths.fotmobRawPath);
        assert.equal(livePaths.allocationPath, paths.allocationPath);
        assert.match(livePaths.oddsRawPath, /content-addressed\.json$/);
        assert.match(livePaths.receiptPath, /live\.json$/);
    });
});

test('missing fixture or allocation remains visible to downstream readiness after live handoff', t => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'stage-c-live-paths-'));
    t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    const paths = bundle(root);

    withConfiguredPaths(paths, ({ liveCaptureInputPaths }) => {
        const livePaths = liveCaptureInputPaths({ oddsRawPath: 'new-odds.json', receiptPath: 'new-receipt.json' });
        assert.equal(livePaths.fotmobRawPath, paths.fotmobRawPath);
        assert.equal(livePaths.allocationPath, paths.allocationPath);
        assert.equal(fs.existsSync(livePaths.fotmobRawPath), false);
        assert.equal(fs.existsSync(livePaths.allocationPath), false);
    });
});
