'use strict';

// Bootstrap only.  Publication, locks and staging writes deliberately belong
// to later construction units.
const fs = require('node:fs');
const path = require('node:path');
const { loadVerifiedAllocationAuthority } = require('../fixture_universe/AllocationAuthorityArtifact');
const { isUtcTimestamp } = require('./contracts');
const { STORE_SCHEMA_VERSION, STORE_TYPE, TRANSACTION_SCHEMA_VERSION, canonicalBytes, canonicalJson, hashCanonical, validateAllocationBinding, computeAuthorityStateHash, assertPlainObject } = require('./transactionContract');

const STORE_FILE = 'STORE.json';
function lstatRegular(filePath, label) { const stat = fs.lstatSync(filePath); if (stat.isSymbolicLink() || !stat.isFile()) throw new Error(`${label} must be a regular file`); return stat; }
function ensureDirectory(dir, label) {
    if (fs.existsSync(dir)) { const stat = fs.lstatSync(dir); if (stat.isSymbolicLink() || !stat.isDirectory()) throw new Error(`${label} must be a non-symlink directory`); return; }
    fs.mkdirSync(dir, { recursive: true, mode: 0o700 });
}
function writeExclusive(filePath, bytes) {
    let fd;
    try {
        fd = fs.openSync(filePath, fs.constants.O_WRONLY | fs.constants.O_CREAT | fs.constants.O_EXCL | (fs.constants.O_NOFOLLOW || 0), 0o444);
        const data = Buffer.from(bytes, 'utf8'); let offset = 0;
        while (offset < data.length) { const written = fs.writeSync(fd, data, offset, data.length - offset); if (!Number.isInteger(written) || written <= 0 || written > data.length - offset) throw new Error('STORE.json short write made no progress'); offset += written; }
        fs.fsyncSync(fd);
    } finally { if (fd !== undefined) fs.closeSync(fd); }
    fs.chmodSync(filePath, 0o444);
}
function allocationBindingFromPath(allocationArtifactPath) {
    const allocation = loadVerifiedAllocationAuthority({ artifactPath: allocationArtifactPath });
    return { allocation_schema_version: allocation.allocationSnapshot.schema_version, allocation_content_hash: allocation.allocationHash, allocation_artifact_sha256: allocation.artifactHash, allocation_provenance_raw_sha256: allocation.provenanceRawSha256, allocation_snapshot: allocation.allocationSnapshot };
}
function validateStoreDocument(store) {
    assertPlainObject(store, 'STORE.json');
    const keys = ['schema_version', 'store_type', 'authority_owner', 'authority_created_at', 'allocation', 'genesis_state_hash', 'transaction_schema_version', 'bootstrap_metadata', 'store_sha256'];
    if (Object.keys(store).some(key => !keys.includes(key)) || keys.some(key => !Object.prototype.hasOwnProperty.call(store, key))) throw new Error('STORE.json fields are invalid');
    if (store.schema_version !== STORE_SCHEMA_VERSION || store.store_type !== STORE_TYPE || store.authority_owner !== 'FootballPrediction' || store.transaction_schema_version !== TRANSACTION_SCHEMA_VERSION) throw new Error('STORE.json identity is invalid');
    if (!isUtcTimestamp(store.authority_created_at)) throw new Error('STORE.json authority_created_at is invalid');
    const allocation = validateAllocationBinding(store.allocation);
    assertPlainObject(store.bootstrap_metadata, 'STORE.json bootstrap_metadata');
    const expectedGenesis = computeAuthorityStateHash({ allocation, decisions: [], latestDecisions: [], activeMatched: [], registryState: [], observationIndex: [] });
    if (store.genesis_state_hash !== expectedGenesis) throw new Error('STORE.json genesis_state_hash is invalid');
    const unsigned = { ...store }; delete unsigned.store_sha256;
    if (store.store_sha256 !== hashCanonical(unsigned)) throw new Error('STORE.json store_sha256 is invalid');
    return Object.freeze({ ...store, allocation });
}
function readStoreContract({ storeRoot, allocationArtifactPath }) {
    if (typeof storeRoot !== 'string' || !storeRoot) throw new Error('storeRoot is required');
    const root = path.resolve(storeRoot); const stat = fs.lstatSync(root); if (stat.isSymbolicLink() || !stat.isDirectory()) throw new Error('transaction store root must be a non-symlink directory');
    const storePath = path.join(root, STORE_FILE); const storeStat = lstatRegular(storePath, 'STORE.json'); if ((storeStat.mode & 0o222) !== 0) throw new Error('STORE.json must be read-only');
    const bytes = fs.readFileSync(storePath, 'utf8'); let parsed;
    try { parsed = JSON.parse(bytes); } catch (error) { throw new Error(`STORE.json is invalid JSON: ${error.message}`, { cause: error }); }
    if (bytes !== canonicalBytes(parsed)) throw new Error('STORE.json must use canonical serialization');
    const store = validateStoreDocument(parsed);
    if (allocationArtifactPath) {
        const expected = allocationBindingFromPath(allocationArtifactPath);
        if (canonicalJson(expected) !== canonicalJson(store.allocation)) throw new Error('STORE.json is bound to a different allocation authority');
    }
    return Object.freeze({ root, store, storePath });
}
function bootstrapMarketEvidenceTransactionStore({ storeRoot, allocationArtifactPath, bootstrapMetadata = {} }) {
    if (typeof storeRoot !== 'string' || !storeRoot || typeof allocationArtifactPath !== 'string' || !allocationArtifactPath) throw new Error('storeRoot and allocationArtifactPath are required');
    assertPlainObject(bootstrapMetadata, 'bootstrapMetadata');
    const root = path.resolve(storeRoot); ensureDirectory(root, 'transaction store root');
    ensureDirectory(path.join(root, '.staging'), 'transaction staging directory'); ensureDirectory(path.join(root, 'committed'), 'transaction committed directory');
    const storePath = path.join(root, STORE_FILE);
    if (fs.existsSync(storePath)) {
        const existing = readStoreContract({ storeRoot: root, allocationArtifactPath });
        if (canonicalJson(existing.store.bootstrap_metadata) !== canonicalJson(bootstrapMetadata)) throw new Error('STORE.json already exists with different content');
        return existing;
    }
    const allocation = allocationBindingFromPath(allocationArtifactPath);
    const genesisStateHash = computeAuthorityStateHash({ allocation, decisions: [], latestDecisions: [], activeMatched: [], registryState: [], observationIndex: [] });
    const unsigned = { schema_version: STORE_SCHEMA_VERSION, store_type: STORE_TYPE, authority_owner: 'FootballPrediction', authority_created_at: new Date().toISOString(), allocation, genesis_state_hash: genesisStateHash, transaction_schema_version: TRANSACTION_SCHEMA_VERSION, bootstrap_metadata: bootstrapMetadata };
    const document = { ...unsigned, store_sha256: hashCanonical(unsigned) }; const bytes = canonicalBytes(document);
    writeExclusive(storePath, bytes);
    return readStoreContract({ storeRoot: root, allocationArtifactPath });
}

module.exports = { STORE_FILE, bootstrapMarketEvidenceTransactionStore, readStoreContract, validateStoreDocument, allocationBindingFromPath };
