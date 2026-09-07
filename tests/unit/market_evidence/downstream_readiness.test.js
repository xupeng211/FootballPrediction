'use strict';

// Fully offline contract tests.  No provider client or network transport is
// imported here: the gate must be decidable before a scarce live request.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');
const { sha256Text } = require('../../../src/infrastructure/market_evidence/contracts');
const { seedFotMobFixtureUniverse } = require('../../../src/infrastructure/fixture_universe/FixtureUniverse');
const { persistVerifiedAllocationAuthority } = require('../../../src/infrastructure/fixture_universe/AllocationAuthorityArtifact');
const { bootstrapMarketEvidenceTransactionStore } = require('../../../src/infrastructure/market_evidence/transactionStore');
const { assertDownstreamInputReadiness } = require('../../../src/infrastructure/market_evidence/downstreamReadiness');
const { preparePreflight, executePreparedPreflight } = require('../../../src/infrastructure/market_evidence/preflightRunner');

function tempRoot(t) {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'downstream-readiness-'));
    t.after(() => fs.rmSync(root, { recursive: true, force: true }));
    return root;
}

function fixtureHtml() {
    const teams = ['Arsenal', 'Aston Villa', 'Bournemouth', 'Brentford', 'Brighton', 'Chelsea', 'Crystal Palace', 'Everton', 'Fulham', 'Leeds', 'Leicester', 'Liverpool', 'Man City', 'Man United', 'Newcastle', 'Southampton', 'Tottenham', 'West Ham', 'Wolves', 'Nottingham Forest'];
    const matches = Array.from({ length: 380 }, (_, index) => ({
        id: String(900000 + index),
        home: { name: teams[index % teams.length] },
        away: { name: teams[(index + 3) % teams.length] },
        status: { utcTime: `2026-${String((index % 12) + 1).padStart(2, '0')}-${String((index % 28) + 1).padStart(2, '0')}T15:00:00Z` },
    }));
    return `<script id="__NEXT_DATA__" type="application/json">${JSON.stringify({ query: { season: '2026/2027' }, props: { pageProps: { details: { id: 47 }, fixtures: { allMatches: matches } } } })}</script>`;
}

function readyInputs(t) {
    const root = tempRoot(t);
    const raw = fixtureHtml();
    const rawPath = path.join(root, 'fotmob.html');
    const allocationPath = path.join(root, 'allocation.json');
    fs.writeFileSync(rawPath, raw, { mode: 0o600 });
    const universe = seedFotMobFixtureUniverse({ rawHtml: raw, rawSha256: sha256Text(raw), mode: 'INITIAL_SEED' });
    fs.writeFileSync(allocationPath, JSON.stringify(universe.allocationSnapshot), { mode: 0o600 });
    const storeRoot = path.join(root, 'transactions');
    const allocationArtifactPath = path.join(storeRoot, 'allocation.authority.json');
    persistVerifiedAllocationAuthority({ artifactPath: allocationArtifactPath, allocationAuthority: universe.allocationAuthority });
    bootstrapMarketEvidenceTransactionStore({ storeRoot, allocationArtifactPath, bootstrapMetadata: { test: 'downstream-readiness' } });
    return { root, fotmobRawPath: rawPath, allocationPath, storeRoot, allocationArtifactPath };
}

test('valid fixture, identity, and transaction authorities make a target transport-eligible', t => {
    const inputs = readyInputs(t);
    const result = assertDownstreamInputReadiness(inputs);
    assert.equal(result.ready, true);
    assert.equal(result.fixture_count, 380);
    assert.equal(result.transaction_authority, 'EXISTING_AUTHORITY_VERIFIED');
});

test('missing, non-regular, malformed, incompatible, and missing identity authorities fail closed', t => {
    const inputs = readyInputs(t);
    fs.unlinkSync(inputs.fotmobRawPath);
    assert.throws(() => assertDownstreamInputReadiness(inputs), /FotMob fixture authority/);

    const nonRegular = readyInputs(t);
    fs.unlinkSync(nonRegular.fotmobRawPath);
    fs.mkdirSync(nonRegular.fotmobRawPath);
    assert.throws(() => assertDownstreamInputReadiness(nonRegular), /readable regular file/);

    const malformed = readyInputs(t);
    fs.writeFileSync(malformed.fotmobRawPath, '<html>not fixture evidence</html>');
    assert.throws(() => assertDownstreamInputReadiness(malformed), /authorized EPL/);

    const incompatible = readyInputs(t);
    const allocation = JSON.parse(fs.readFileSync(incompatible.allocationPath, 'utf8'));
    allocation.identity_ruleset_version = 'incompatible';
    fs.writeFileSync(incompatible.allocationPath, JSON.stringify(allocation));
    assert.throws(() => assertDownstreamInputReadiness(incompatible), /content hash|ruleset/);

    const missingAllocation = readyInputs(t);
    fs.unlinkSync(missingAllocation.allocationPath);
    assert.throws(() => assertDownstreamInputReadiness(missingAllocation), /identity allocation authority/);
});

test('failed downstream readiness cannot arm or invoke a transport', async t => {
    const inputs = readyInputs(t);
    fs.unlinkSync(inputs.allocationPath);
    const prepared = preparePreflight({ rootDir: path.join(inputs.root, 'audit'), requestMetadata: { regions: 'uk', markets: 'h2h', oddsFormat: 'decimal' }, credentialPresent: true });
    let calls = 0;
    await assert.rejects(() => executePreparedPreflight({
        prepared,
        captureId: 'downstream-not-ready',
        preTransportCheck: () => assertDownstreamInputReadiness(inputs),
        transport: async () => { calls += 1; throw new Error('must not run'); },
    }), /identity allocation authority/);
    assert.equal(calls, 0);
    assert.equal(fs.existsSync(path.join(prepared.root, 'attempts', 'preflight.armed.json')), false);
});

test('an incomplete existing transaction authority fails closed without mutation', t => {
    const inputs = readyInputs(t);
    fs.rmSync(inputs.storeRoot, { recursive: true });
    fs.mkdirSync(inputs.storeRoot);
    fs.writeFileSync(path.join(inputs.storeRoot, 'STORE.json'), '{}');
    assert.throws(() => assertDownstreamInputReadiness(inputs), /incomplete/);
});

test('a missing transaction authority fails closed and cannot bootstrap identities during live preflight', t => {
    const inputs = readyInputs(t);
    fs.rmSync(inputs.storeRoot, { recursive: true });
    assert.throws(() => assertDownstreamInputReadiness(inputs), /cannot bootstrap canonical identities/);
});
