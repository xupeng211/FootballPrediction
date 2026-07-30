'use strict';

// lifecycle: test-fixture
// Reopens only the task-labelled restored disposable database as the actual
// insert-only writer role and runs the production baseline verifier. This keeps
// backup/restore proof tied to the same least-privilege contract as a write.

const { Pool } = require('pg');
const { CanonicalInventoryWriter } = require('../../../src/infrastructure/canonical/CanonicalInventoryWriter');
const { testAuthorizationAuthority } = require('../../helpers/canonicalInventoryFixtures');

function required(name) {
    const value = process.env[name];
    if (!value) throw new Error(`missing ${name}`);
    return value;
}

async function main() {
    const database = required('M3_CANONICAL_DB_NAME');
    const writerRole = required('M3_CANONICAL_DB_WRITER_USER');
    const pool = new Pool({
        host: required('M3_CANONICAL_DB_HOST'),
        port: Number(required('M3_CANONICAL_DB_PORT')),
        database,
        user: writerRole,
        password: required('M3_CANONICAL_DB_WRITER_PASSWORD'),
        max: 1,
    });
    const writer = new CanonicalInventoryWriter({
        pool,
        target: {
            classification: 'disposable',
            databaseIdentity: database,
            serviceIdentity: 'fp_m3_canonical_disposable_postgres15',
            writerRole,
        },
        authorizationAuthority: testAuthorizationAuthority(),
        codeRevision: required('M3_CANONICAL_WRITER_CODE_REVISION'),
    });
    try {
        const client = await pool.connect();
        try {
            await writer.inspectTarget(client);
            const result = await client.query('SELECT COUNT(*)::integer AS matches FROM public.matches');
            const adminRole = await client.query(
                "SELECT rolcanlogin FROM pg_roles WHERE rolname = 'm3_canonical_admin'"
            );
            if (adminRole.rows[0]?.rolcanlogin !== false) {
                throw new Error('restored disposable admin login must be disabled before writer baseline verification');
            }
            process.stdout.write(
                `${JSON.stringify({ status: 'restored_writer_baseline_verified', database, matches: result.rows[0].matches })}\n`
            );
        } finally {
            client.release();
        }
    } finally {
        await pool.end();
    }
}

main().catch(error => {
    if (error?.evidence) process.stderr.write(`${JSON.stringify({ code: error.code, evidence: error.evidence })}\n`);
    process.stderr.write(`${error.stack || error}\n`);
    process.exitCode = 1;
});
