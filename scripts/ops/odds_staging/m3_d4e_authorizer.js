'use strict';

// lifecycle: permanent；只为固定本地 M3 sandbox 的 D4E 合成写入提供 fail-closed 双重授权。

const { TARGET_TABLES } = require('../../../src/infrastructure/odds_staging/persistenceRepository');

const AUTHORIZATION_PHRASE = 'I_AUTHORIZE_M3_D4E_PERSISTENT_SANDBOX_WRITE';
const DATABASE = 'fp_m3_persistent_sandbox';
const PROJECT = 'fp_m3_persistent_sandbox';
const SERVICE = 'm3-persistent-postgres';
const WRITER = 'fp_m3_sandbox_writer';

class D4EAuthorizationError extends Error {
    constructor(message) { super(message); this.name = 'D4EAuthorizationError'; this.code = 'D4E_AUTHORIZATION_DENIED'; }
}

function assertD4EConfig(config = process.env) {
    if (config.ALLOW_M3_D4E_PERSISTENT_SANDBOX_WRITE !== '1') throw new D4EAuthorizationError('D4E allow flag is required');
    if (config.M3_D4E_AUTHORIZATION_PHRASE !== AUTHORIZATION_PHRASE) throw new D4EAuthorizationError('D4E authorization phrase mismatch');
    if (config.M3_D4E_SAMPLE_KIND !== 'synthetic') throw new D4EAuthorizationError('only deterministic synthetic sample kind is allowed');
    if (config.M3_D4E_DATABASE !== DATABASE || config.M3_D4E_PROJECT !== PROJECT || config.M3_D4E_SERVICE !== SERVICE) throw new D4EAuthorizationError('fixed sandbox identity mismatch');
    if (config.M3_D4E_WRITER !== WRITER) throw new D4EAuthorizationError('writer identity mismatch');
    if (config.M3_D4E_PRODUCTION !== 'false' || config.M3_D4E_STAGING !== 'false') throw new D4EAuthorizationError('non-production identity is required');
    if (['localhost', 'host.docker.internal'].includes(config.PGHOST) || !config.PGHOST) throw new D4EAuthorizationError('sandbox network host is required');
}

async function authorizeD4EWrite(request, config = process.env) {
    assertD4EConfig(config);
    const tables = [...(request?.tables || [])].sort();
    const operations = [...(request?.operations || [])].sort();
    if (JSON.stringify(tables) !== JSON.stringify([...TARGET_TABLES].sort()) || JSON.stringify(operations) !== JSON.stringify(['INSERT', 'UPDATE'])) {
        throw new D4EAuthorizationError('D4E table/operation contract mismatch');
    }
}

module.exports = { AUTHORIZATION_PHRASE, D4EAuthorizationError, DATABASE, PROJECT, SERVICE, WRITER, assertD4EConfig, authorizeD4EWrite };
