'use strict';

// Read-only pre-transport checks for the real Stage C canonical inputs.  This
// intentionally validates the same immutable FotMob/allocation contracts that
// the offline pipeline consumes, without allocating identities or mutating a
// transaction store.
const fs = require('node:fs');
const path = require('node:path');
const { extractNextData, extractPageIdentity, extractFixtures } = require('../fotmob/FotMobCandidateExporter');
const { validateAllocationSnapshot, RULESET_VERSION, RESOLVER_VERSION } = require('../fixture_universe/FixtureUniverse');
const { normalizeIdentityText } = require('../fixture_universe/identityRules');
const { sha256Text, stableStringify } = require('./contracts');
const { readStoreContract } = require('./transactionStore');
const { loadVerifiedAllocationAuthority } = require('../fixture_universe/AllocationAuthorityArtifact');
const { openMarketEvidenceAuthoritySnapshot } = require('./authorityReader');

const COMPETITION_ID = 'cmp_epl';
const SEASON = '2026/2027';

function regularText(filePath, label) {
    if (typeof filePath !== 'string' || !filePath.trim()) throw new Error(`${label} path is required`);
    let stat;
    try {
        stat = fs.lstatSync(filePath);
    } catch (error) {
        if (error && error.code === 'ENOENT') throw new Error(`${label} is missing`);
        throw error;
    }
    if (stat.isSymbolicLink() || !stat.isFile()) throw new Error(`${label} must be a readable regular file`);
    fs.accessSync(filePath, fs.constants.R_OK);
    const text = fs.readFileSync(filePath, 'utf8');
    if (!text.trim()) throw new Error(`${label} is empty`);
    return text;
}

function regularJson(filePath, label) {
    const text = regularText(filePath, label);
    try {
        return JSON.parse(text);
    } catch (error) {
        throw new Error(`${label} is invalid JSON: ${error.message}`, { cause: error });
    }
}

function assertFixtureAndAllocationReady({ fotmobRawPath, allocationPath }) {
    const fotmobRawText = regularText(fotmobRawPath, 'FotMob fixture authority');
    const fotmobRawSha256 = sha256Text(fotmobRawText);
    const page = extractPageIdentity(extractNextData(fotmobRawText));
    const extraction = extractFixtures(extractNextData(fotmobRawText));
    if (page?.league_id !== '47' || page?.season_canonical !== SEASON || extraction.fixtures.length !== 380) {
        throw new Error('FotMob fixture authority is not the authorized EPL 2026/2027 universe');
    }
    const allocation = regularJson(allocationPath, 'identity allocation authority');
    validateAllocationSnapshot(allocation, fotmobRawSha256);
    if (allocation.identity_ruleset_version !== RULESET_VERSION || allocation.resolver_version !== RESOLVER_VERSION) {
        throw new Error('identity allocation ruleset/resolver version is incompatible');
    }
    const fixtureIds = new Set(extraction.fixtures.map(row => row.id));
    const teamNames = new Set(extraction.fixtures.flatMap(row => [normalizeIdentityText(row.home), normalizeIdentityText(row.away)]));
    if (allocation.fixtures.length !== fixtureIds.size || allocation.fixtures.some(row => !fixtureIds.has(row.fotmob_event_id))) {
        throw new Error('identity allocation fixture coverage is incompatible with FotMob fixture authority');
    }
    if (allocation.teams.length !== teamNames.size || allocation.teams.some(row => !teamNames.has(normalizeIdentityText(row.fotmob_name)))) {
        throw new Error('identity allocation team coverage is incompatible with FotMob fixture authority');
    }
    return Object.freeze({ fotmobRawSha256, fixtureCount: fixtureIds.size, teamCount: teamNames.size, allocation });
}

function assertTransactionAuthorityReady({ storeRoot, allocationArtifactPath }) {
    const root = path.resolve(storeRoot);
    const storePath = path.join(root, 'STORE.json');
    const storeExists = fs.existsSync(storePath);
    const artifactExists = fs.existsSync(allocationArtifactPath);
    if (storeExists !== artifactExists) throw new Error('transaction authority is incomplete: STORE.json and allocation artifact must coexist');
    if (!storeExists) {
        if (fs.existsSync(root)) {
            const stat = fs.lstatSync(root);
            if (stat.isSymbolicLink() || !stat.isDirectory()) throw new Error('transaction authority bootstrap root must be a non-symlink directory');
            if (fs.readdirSync(root).length !== 0) throw new Error('transaction authority bootstrap root contains incomplete state');
        }
        return Object.freeze({ mode: 'BOOTSTRAP_ELIGIBLE' });
    }
    readStoreContract({ storeRoot, allocationArtifactPath });
    const verified = loadVerifiedAllocationAuthority({ artifactPath: allocationArtifactPath });
    openMarketEvidenceAuthoritySnapshot({ storeRoot, allocationArtifactPath });
    return Object.freeze({ mode: 'EXISTING_AUTHORITY_VERIFIED', allocation: verified.allocationSnapshot });
}

function assertDownstreamInputReadiness({ fotmobRawPath, allocationPath, storeRoot, allocationArtifactPath }) {
    if (typeof storeRoot !== 'string' || !storeRoot.trim() || typeof allocationArtifactPath !== 'string' || !allocationArtifactPath.trim()) {
        throw new Error('transaction authority paths are required');
    }
    const fixture = assertFixtureAndAllocationReady({ fotmobRawPath, allocationPath });
    const transaction = assertTransactionAuthorityReady({ storeRoot, allocationArtifactPath });
    if (transaction.allocation && stableStringify(transaction.allocation) !== stableStringify(fixture.allocation)) {
        throw new Error('transaction allocation authority is incompatible with the configured identity allocation');
    }
    return Object.freeze({ ready: true, competition_id: COMPETITION_ID, season: SEASON, fixture_count: fixture.fixtureCount, team_count: fixture.teamCount, transaction_authority: transaction.mode });
}

module.exports = { assertDownstreamInputReadiness, assertFixtureAndAllocationReady, assertTransactionAuthorityReady };
