'use strict';

// lifecycle: permanent

const assert = require('node:assert/strict');
const test = require('node:test');
const {
    CanonicalInventoryWriter,
    CanonicalInventoryWriterError,
    EXPECTED_INVENTORY_CHECK_EXPRESSIONS,
    classifyProviderDifference,
    findInventoryCheckDrift,
} = require('../../src/infrastructure/canonical/CanonicalInventoryWriter');
const { SYNTHETIC_TEST_CODE_REVISION } = require('../helpers/canonicalInventoryFixtures');

const candidate = {
    competition: 'Premier League',
    season: '2022/2023',
    home_team: 'Synthetic Home',
    away_team: 'Synthetic Away',
    kickoff_at: '2022-08-01T12:00:00Z',
};

function existing(overrides = {}) {
    return {
        league_name: candidate.competition,
        season: candidate.season,
        home_team: candidate.home_team,
        away_team: candidate.away_team,
        match_date: candidate.kickoff_at,
        ...overrides,
    };
}

test('provider identity divergence has deterministic fail-closed terminals', () => {
    assert.equal(
        classifyProviderDifference(candidate, existing({ league_name: 'Other League' })),
        'conflict_competition'
    );
    assert.equal(classifyProviderDifference(candidate, existing({ season: '2023/2024' })), 'conflict_season');
    assert.equal(classifyProviderDifference(candidate, existing({ home_team: 'Other Home' })), 'conflict_home_away');
    assert.equal(
        classifyProviderDifference(candidate, existing({ match_date: '2022-08-01T12:30:00Z' })),
        'conflict_kickoff'
    );
    assert.equal(classifyProviderDifference(candidate, existing()), 'conflict_external_id');
});

test('writer requires independently configured disposable target and trusted authorization authority', () => {
    const pool = { connect: async () => ({}) };
    assert.throws(
        () =>
            new CanonicalInventoryWriter({
                pool,
                target: {
                    databaseIdentity: 'db',
                    serviceIdentity: 'service',
                    writerRole: 'writer',
                    classification: 'persistent',
                },
                authorizationAuthority: { public_key: 'not-used' },
                codeRevision: SYNTHETIC_TEST_CODE_REVISION,
            }),
        error => error instanceof CanonicalInventoryWriterError && error.code === 'TARGET_CLASSIFICATION_MISMATCH'
    );
    assert.throws(
        () =>
            new CanonicalInventoryWriter({
                pool,
                target: {
                    databaseIdentity: 'db',
                    serviceIdentity: 'service',
                    writerRole: 'writer',
                    classification: 'disposable',
                },
                codeRevision: SYNTHETIC_TEST_CODE_REVISION,
            }),
        error => error instanceof CanonicalInventoryWriterError && error.code === 'AUTHORIZATION_AUTHORITY_MISSING'
    );
    assert.throws(
        () =>
            new CanonicalInventoryWriter({
                pool,
                target: {
                    databaseIdentity: 'db',
                    serviceIdentity: 'service',
                    writerRole: 'writer',
                    classification: 'disposable',
                },
                authorizationAuthority: { public_key: 'not-used' },
                codeRevision: 'not-a-git-revision',
            }),
        error => error instanceof CanonicalInventoryWriterError && error.code === 'CODE_REVISION_MISSING'
    );
});

function validInventoryCheckRows() {
    return [
        {
            table_name: 'm3_canonical_target_identity',
            expression: "binding_key = 'canonical_inventory_v1'::character varying",
        },
        {
            table_name: 'm3_canonical_target_identity',
            expression: "(service_identity)::text ~ '^[a-z0-9][a-z0-9_.:-]{2,127}$'::text",
        },
        {
            table_name: 'm3_canonical_source_artifacts',
            expression: "(artifact_sha256)::text ~ '^[0-9a-f]{64}$'::text",
        },
        {
            table_name: 'm3_canonical_source_artifacts',
            expression: "artifact_kind = ANY (ARRAY['master'::character varying, 'canary'::character varying])",
        },
        {
            table_name: 'm3_canonical_source_artifacts',
            expression: "(business_hash)::text ~ '^[0-9a-f]{64}$'::text",
        },
        { table_name: 'm3_canonical_source_artifacts', expression: 'byte_size > 0' },
        { table_name: 'm3_canonical_source_artifacts', expression: 'candidate_count > 0' },
        {
            table_name: 'm3_canonical_source_artifacts',
            expression: "competition = 'Premier League'::character varying",
        },
        {
            table_name: 'm3_canonical_source_artifacts',
            expression: "(identity_projection_hash)::text ~ '^[0-9a-f]{64}$'::text",
        },
        {
            table_name: 'm3_canonical_source_artifacts',
            expression: "status_mapping_version = 'fotmob-status-to-matches-status/v1'::character varying",
        },
        {
            table_name: 'm3_canonical_source_artifacts',
            expression:
                "((artifact_kind = 'master'::character varying) AND (parent_artifact_id IS NULL)) OR ((artifact_kind = 'canary'::character varying) AND (parent_artifact_id IS NOT NULL))",
        },
        {
            table_name: 'm3_canonical_import_runs',
            expression: "(authorization_receipt_sha256)::text ~ '^[0-9a-f]{64}$'::text",
        },
        {
            table_name: 'm3_canonical_match_lineages',
            expression: "(immutable_fingerprint)::text ~ '^[0-9a-f]{64}$'::text",
        },
        {
            table_name: 'm3_canonical_match_lineages',
            expression: "status_mapping_version = 'fotmob-status-to-matches-status/v1'::character varying",
        },
    ];
}

test('inventory CHECK constraint sets match exactly when the schema is untampered', () => {
    assert.deepEqual(findInventoryCheckDrift(validInventoryCheckRows()), []);
});

test('inventory CHECK drift fails closed on weakened, widened, missing and duplicated constraints', () => {
    const weakened = validInventoryCheckRows().map(row =>
        row.table_name === 'm3_canonical_source_artifacts' && /parent_artifact_id/.test(row.expression)
            ? { ...row, expression: 'true' }
            : row
    );
    const weakenedDrift = findInventoryCheckDrift(weakened);
    assert.equal(weakenedDrift.length, 1);
    assert.equal(weakenedDrift[0].table, 'm3_canonical_source_artifacts');
    assert.deepEqual(weakenedDrift[0].unexpected, ['true']);
    assert.deepEqual(weakenedDrift[0].missing, [EXPECTED_INVENTORY_CHECK_EXPRESSIONS.m3_canonical_source_artifacts[0]]);

    const widened = validInventoryCheckRows().map(row =>
        row.table_name === 'm3_canonical_source_artifacts' && /competition/.test(row.expression)
            ? {
                  ...row,
                  expression:
                      "competition = ANY (ARRAY['Premier League'::character varying, 'Championship'::character varying])",
              }
            : row
    );
    const widenedDrift = findInventoryCheckDrift(widened);
    assert.equal(widenedDrift.length, 1);
    assert.deepEqual(widenedDrift[0].missing, ["competition='premierleague'"]);
    assert.deepEqual(widenedDrift[0].unexpected, ["competition=anyarray['premierleague','championship']"]);

    const wrongVersion = validInventoryCheckRows().map(row =>
        row.table_name === 'm3_canonical_match_lineages' && /status_mapping_version/.test(row.expression)
            ? {
                  ...row,
                  expression: "status_mapping_version = 'fotmob-status-to-matches-status/v2'::character varying",
              }
            : row
    );
    assert.equal(findInventoryCheckDrift(wrongVersion)[0].table, 'm3_canonical_match_lineages');

    const missingTable = validInventoryCheckRows().filter(row => row.table_name !== 'm3_canonical_import_runs');
    const missingDrift = findInventoryCheckDrift(missingTable);
    assert.deepEqual(missingDrift[0].missing, ["authorization_receipt_sha256~'^[0-9a-f]{64}$'"]);

    const duplicated = [
        ...validInventoryCheckRows(),
        { table_name: 'm3_canonical_source_artifacts', expression: 'byte_size > 0' },
    ];
    assert.deepEqual(findInventoryCheckDrift(duplicated)[0].unexpected, ['byte_size>0']);

    const tamperedBindingKey = validInventoryCheckRows().map(row =>
        row.table_name === 'm3_canonical_target_identity' && /binding_key/.test(row.expression)
            ? { ...row, expression: 'true' }
            : row
    );
    assert.deepEqual(findInventoryCheckDrift(tamperedBindingKey)[0].missing, ["binding_key='canonical_inventory_v1'"]);
});
