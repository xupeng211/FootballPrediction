#!/usr/bin/env node
'use strict';

// lifecycle: permanent
// Canonical offline-only entrypoint for frozen FotMob replay packaging.

const path = require('node:path');
const { buildReplaySourceIndex } = require('../../src/infrastructure/fotmob/FotMobFrozenReplayPackaging');

function parseArgs(argv) {
    const args = {};
    for (const token of argv) {
        if (!token.startsWith('--') || !token.includes('=')) throw Object.assign(new Error(`expected --key=value, got ${token}`), { code: 'INPUT_ERROR' });
        const [key, ...rest] = token.slice(2).split('=');
        args[key] = rest.join('=');
    }
    return args;
}

function main(argv = process.argv.slice(2)) {
    const args = parseArgs(argv);
    const required = ['freeze', 'asset-manifest', 'input', 'output-root'];
    const missing = required.filter(key => !args[key]);
    if (missing.length) throw Object.assign(new Error(`missing: ${missing.join(', ')}`), { code: 'INPUT_ERROR' });
    const result = buildReplaySourceIndex({
        freezePath: args.freeze,
        assetManifestPath: args['asset-manifest'],
        inputPath: args.input,
        outputRoot: args['output-root'],
        repositoryRoot: path.resolve(__dirname, '..', '..'),
    });
    process.stdout.write(`${JSON.stringify({ status: 'complete', ...result.summary })}\n`);
}

if (require.main === module) {
    try { main(); } catch (error) { process.stderr.write(`${error.code || 'ERROR'}: ${error.message}\n`); process.exitCode = 1; }
}

module.exports = { main, parseArgs };
