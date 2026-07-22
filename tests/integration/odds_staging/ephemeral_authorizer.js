'use strict';

// lifecycle: permanent; integration-test-only authorizer. It is never imported by runtime source modules.

const CONFIRMATION = 'I_UNDERSTAND_THIS_DATABASE_WILL_BE_DESTROYED';
const PREFIX = 'fp_m3_d4c_ephemeral_';
const SERVICE = 'ephemeral-postgres';

class EphemeralDatabaseAuthorizationError extends Error {
    constructor(message) {
        super(message);
        this.name = 'EphemeralDatabaseAuthorizationError';
    }
}

function assertEphemeralConfig(config) {
    if (config.allow !== '1') throw new EphemeralDatabaseAuthorizationError('ALLOW_EPHEMERAL_DB_TEST=1 is required');
    if (config.confirmation !== CONFIRMATION) throw new EphemeralDatabaseAuthorizationError('ephemeral confirmation is required');
    if (!String(config.database || '').startsWith(PREFIX)) throw new EphemeralDatabaseAuthorizationError('database name is not D4C ephemeral');
    if (config.host !== SERVICE) throw new EphemeralDatabaseAuthorizationError('host must be the dedicated ephemeral-postgres service');
    if (/(host\.docker\.internal|gateway|prod|production|stage|staging|dev-db|football_prediction_db)/i.test(config.host)) {
        throw new EphemeralDatabaseAuthorizationError('unsafe database host');
    }
}

async function authorizeEphemeralDatabase({ config, client }) {
    assertEphemeralConfig(config);
    const identity = await client.query('SELECT current_database() AS database_name, current_user AS user_name, inet_server_addr()::text AS server_address, inet_server_port() AS server_port');
    if (identity.rows[0]?.database_name !== config.database) throw new EphemeralDatabaseAuthorizationError('connected database identity mismatch');
    await client.query('CREATE TABLE IF NOT EXISTS m3_d4c_session_marker (id BOOLEAN PRIMARY KEY DEFAULT TRUE, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())');
    await client.query('INSERT INTO m3_d4c_session_marker (id) VALUES (TRUE) ON CONFLICT (id) DO NOTHING');
    return identity.rows[0];
}

module.exports = { CONFIRMATION, EphemeralDatabaseAuthorizationError, assertEphemeralConfig, authorizeEphemeralDatabase };
