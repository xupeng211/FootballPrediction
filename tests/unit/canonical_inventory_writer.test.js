'use strict';

// lifecycle: permanent

const assert = require('node:assert/strict');
const test = require('node:test');
const {
    CanonicalInventoryWriter,
    CanonicalInventoryWriterError,
    classifyProviderDifference,
} = require('../../src/infrastructure/canonical/CanonicalInventoryWriter');

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
                target: { databaseIdentity: 'db', serviceIdentity: 'service', classification: 'persistent' },
                authorizationAuthority: { public_key: 'not-used' },
            }),
        error => error instanceof CanonicalInventoryWriterError && error.code === 'TARGET_CLASSIFICATION_MISMATCH'
    );
    assert.throws(
        () =>
            new CanonicalInventoryWriter({
                pool,
                target: { databaseIdentity: 'db', serviceIdentity: 'service', classification: 'disposable' },
            }),
        error => error instanceof CanonicalInventoryWriterError && error.code === 'AUTHORIZATION_AUTHORITY_MISSING'
    );
});
