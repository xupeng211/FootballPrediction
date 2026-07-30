#!/usr/bin/env node
'use strict';

// lifecycle: permanent
// Controlled M3 canonical inventory operator. Default is a local, no-write
// contract preflight. The separately labelled disposable PostgreSQL proof is
// executable only through its Make data-* safety gate, never this direct CLI.

const { readOrdinaryArtifact } = require('../../src/infrastructure/canonical/CanonicalInventoryContract');
const { SCHEMA_BASELINE } = require('../../src/infrastructure/canonical/CanonicalInventoryWriter');

function parseArgs(argv) {
    const args = { execute: false };
    for (let index = 0; index < argv.length; index += 1) {
        const token = argv[index];
        if (token === '--execute-disposable') {
            args.execute = true;
            continue;
        }
        if (token === '--help') {
            args.help = true;
            continue;
        }
        if (!token.startsWith('--')) throw new Error(`unknown argument ${token}`);
        const key = token.slice(2);
        const value = argv[index + 1];
        if (!value || value.startsWith('--')) throw new Error(`${token} requires a value`);
        args[key] = value;
        index += 1;
    }
    return args;
}

function print(value) {
    process.stdout.write(`${JSON.stringify(value)}\n`);
}

async function main(argv = process.argv.slice(2)) {
    const args = parseArgs(argv);
    if (args.help) {
        print({
            usage: 'canonical:inventory:writer --artifact /abs/file --artifact-sha256 <sha> [--parent-artifact /abs/file --parent-artifact-sha256 <sha>]',
            default:
                'no-write preflight; disposable writes are available only through make data-m3-canonical-inventory-disposable-proof',
        });
        return 0;
    }
    if (args.execute) {
        throw new Error(
            'direct execution is disabled: use make data-m3-canonical-inventory-disposable-proof for the fixed synthetic disposable proof'
        );
    }
    if (Boolean(args['parent-artifact']) !== Boolean(args['parent-artifact-sha256'])) {
        throw new Error('--parent-artifact and --parent-artifact-sha256 must be provided together');
    }
    const expected = { sha256: args['artifact-sha256'] };
    if (!expected.sha256) throw new Error('--artifact-sha256 is required');
    const allowSyntheticTestOnly = args['target-classification'] === 'disposable';
    if (args['parent-artifact']) {
        const parent = readOrdinaryArtifact(args['parent-artifact'], {
            sha256: args['parent-artifact-sha256'],
            allowSyntheticTestOnly,
        });
        expected.parentArtifactPath = parent.path;
    }
    const artifact = readOrdinaryArtifact(args.artifact, {
        ...expected,
        allowSyntheticTestOnly,
    });
    const preflight = {
        status: 'no_write_preflight_complete',
        operation: args.operation || null,
        artifact: {
            sha256: artifact.sha256,
            byte_size: artifact.byte_size,
            kind: artifact.artifact.kind,
            candidate_count: artifact.candidates.length,
            business_hash: artifact.artifact.business_hash,
            identity_projection_hash: artifact.artifact.identity_projection_hash,
        },
        schema_baseline: SCHEMA_BASELINE,
        write_performed: false,
    };
    print(preflight);
    return 0;
}

if (require.main === module) {
    main().catch(error => {
        print({
            status: 'blocked',
            code: error.code || 'OPERATOR_FAILURE',
            message: error.message,
            write_performed: false,
        });
        process.exitCode = 1;
    });
}

module.exports = { main, parseArgs };
