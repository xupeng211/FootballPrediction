#!/usr/bin/env node
'use strict';

// lifecycle: permanent
// Controlled M3 canonical inventory operator. Default is a local, no-write
// contract preflight. The only executable operation in this implementation is
// the separately labelled disposable PostgreSQL proof.

const fs = require('node:fs');
const path = require('node:path');
const { Pool } = require('pg');
const { readOrdinaryArtifact } = require('../../src/infrastructure/canonical/CanonicalInventoryContract');
const {
    CanonicalInventoryWriter,
    SCHEMA_BASELINE,
} = require('../../src/infrastructure/canonical/CanonicalInventoryWriter');
const { DISPOSABLE_OPERATION } = require('../../src/infrastructure/canonical/CanonicalInventoryAuthorization');

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

function readJsonOrdinary(filePath, label) {
    if (!filePath || !path.isAbsolute(filePath)) throw new Error(`${label} must be an absolute ordinary file path`);
    const stat = fs.lstatSync(filePath);
    if (!stat.isFile() || stat.isSymbolicLink()) throw new Error(`${label} must be an ordinary non-symlink file`);
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function print(value) {
    process.stdout.write(`${JSON.stringify(value)}\n`);
}

async function main(argv = process.argv.slice(2)) {
    const args = parseArgs(argv);
    if (args.help) {
        print({
            usage: 'canonical:inventory:writer --artifact /abs/file --artifact-sha256 <sha> [--execute-disposable --operation canonical_inventory_disposable_proof --runtime-authorization /abs/file --provenance /abs/file --database-url <url> --target-database <name> --target-service <identity>]',
            default: 'no-write preflight',
        });
        return 0;
    }
    const expected = { sha256: args['artifact-sha256'] };
    if (!expected.sha256) throw new Error('--artifact-sha256 is required');
    if (args['parent-artifact']) {
        const parent = readOrdinaryArtifact(args['parent-artifact'], { sha256: args['parent-artifact-sha256'] });
        expected.parentDocument = parent.document;
        expected.parentBinding = { sha256: parent.sha256, byte_size: parent.byte_size };
    }
    const artifact = readOrdinaryArtifact(args.artifact, expected);
    const preflight = {
        status: args.execute ? 'preflight_complete' : 'no_write_preflight_complete',
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
    if (!args.execute) {
        print(preflight);
        return 0;
    }
    if (args.operation !== DISPOSABLE_OPERATION) throw new Error(`--operation must be ${DISPOSABLE_OPERATION}`);
    if (args['target-classification'] !== 'disposable') {
        throw new Error('persistent target rejected: --target-classification disposable is required');
    }
    if (!args['database-url'] || !args['target-database'] || !args['target-service']) {
        throw new Error('execute requires database URL and explicit target identities');
    }
    const runtimeAuthorization = readJsonOrdinary(args['runtime-authorization'], 'runtime authorization receipt');
    const provenanceReceipt = readJsonOrdinary(args.provenance, 'provenance receipt');
    const pool = new Pool({ connectionString: args['database-url'], max: 1 });
    try {
        const writer = new CanonicalInventoryWriter({
            pool,
            target: { databaseIdentity: args['target-database'], serviceIdentity: args['target-service'] },
            codeRevision: args['code-revision'] || 'operator',
        });
        const result = await writer.execute({ ...artifact, runtimeAuthorization, provenanceReceipt });
        print({ ...result, write_performed: true });
    } finally {
        await pool.end();
    }
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

module.exports = { main, parseArgs, readJsonOrdinary };
