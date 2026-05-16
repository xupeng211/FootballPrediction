'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

const {
    RAW_MATCH_DATA_VERSIONS,
    DEFAULT_CANONICAL_VERSION_PRIORITY,
    classifyRawDataVersion,
    isCanonicalFotMobVersion,
    isSyntheticOrUnknownVersion,
    filterRowsByAllowedVersions,
    selectCanonicalRawMatchData,
    requireSingleVersionRow,
    buildVersionAwareLookupSpec,
} = require('../../src/infrastructure/services/RawMatchDataVersionSelector');

function row(overrides = {}) {
    return {
        id: 1,
        match_id: '53_20252026_4830747',
        external_id: '4830747',
        data_version: RAW_MATCH_DATA_VERSIONS.FOTMOB_HTML_HYD_V1,
        data_hash: 'hash',
        ...overrides,
    };
}

test('classify fotmob_pageprops_v2', () => {
    assert.equal(classifyRawDataVersion(RAW_MATCH_DATA_VERSIONS.FOTMOB_PAGEPROPS_V2), 'canonical_fotmob_pageprops');
});

test('classify fotmob_html_hyd_v1', () => {
    assert.equal(classifyRawDataVersion(RAW_MATCH_DATA_VERSIONS.FOTMOB_HTML_HYD_V1), 'canonical_fotmob_transformed');
});

test('classify PHASE4.43_SYNTHETIC', () => {
    assert.equal(classifyRawDataVersion(RAW_MATCH_DATA_VERSIONS.PHASE4_43_SYNTHETIC), 'legacy_synthetic');
});

test('classify PHASE4.23', () => {
    assert.equal(classifyRawDataVersion(RAW_MATCH_DATA_VERSIONS.PHASE4_23), 'legacy_unknown');
});

test('classify unknown', () => {
    assert.equal(classifyRawDataVersion('other_version'), 'unknown');
});

test('isCanonicalFotMobVersion true for v2/v1', () => {
    assert.equal(isCanonicalFotMobVersion(RAW_MATCH_DATA_VERSIONS.FOTMOB_PAGEPROPS_V2), true);
    assert.equal(isCanonicalFotMobVersion(RAW_MATCH_DATA_VERSIONS.FOTMOB_HTML_HYD_V1), true);
});

test('synthetic/unknown excluded by default', () => {
    const rows = [
        row({ id: 1, data_version: RAW_MATCH_DATA_VERSIONS.FOTMOB_HTML_HYD_V1 }),
        row({ id: 2, data_version: RAW_MATCH_DATA_VERSIONS.PHASE4_43_SYNTHETIC }),
        row({ id: 3, data_version: 'untracked' }),
    ];
    const filtered = filterRowsByAllowedVersions({ rows });
    assert.deepEqual(
        filtered.map(item => item.id),
        [1]
    );
    assert.equal(isSyntheticOrUnknownVersion(RAW_MATCH_DATA_VERSIONS.PHASE4_43_SYNTHETIC), true);
    assert.equal(isSyntheticOrUnknownVersion('untracked'), true);
});

test('select v2 over v1', () => {
    const selected = selectCanonicalRawMatchData({
        rows: [
            row({ id: 1, data_version: RAW_MATCH_DATA_VERSIONS.FOTMOB_HTML_HYD_V1 }),
            row({ id: 2, data_version: RAW_MATCH_DATA_VERSIONS.FOTMOB_PAGEPROPS_V2 }),
        ],
    });
    assert.equal(selected.id, 2);
});

test('select v1 fallback when v2 absent', () => {
    const selected = selectCanonicalRawMatchData({
        rows: [row({ id: 1, data_version: RAW_MATCH_DATA_VERSIONS.FOTMOB_HTML_HYD_V1 })],
    });
    assert.equal(selected.id, 1);
});

test('return missing when only synthetic', () => {
    const selected = selectCanonicalRawMatchData({
        rows: [row({ id: 1, data_version: RAW_MATCH_DATA_VERSIONS.PHASE4_43_SYNTHETIC })],
    });
    assert.equal(selected, null);
});

test('return missing when only unknown', () => {
    const selected = selectCanonicalRawMatchData({
        rows: [row({ id: 1, data_version: 'unknown_version' })],
    });
    assert.equal(selected, null);
});

test('duplicate same version throws controlled error', () => {
    assert.throws(
        () =>
            selectCanonicalRawMatchData({
                rows: [
                    row({ id: 1, data_version: RAW_MATCH_DATA_VERSIONS.FOTMOB_HTML_HYD_V1 }),
                    row({ id: 2, data_version: RAW_MATCH_DATA_VERSIONS.FOTMOB_HTML_HYD_V1 }),
                ],
            }),
        /RAW_MATCH_DATA_DUPLICATE_VERSION/
    );
});

test('requireSingleVersionRow returns missing for 0 rows', () => {
    assert.deepEqual(
        requireSingleVersionRow([], {
            expectedMatchId: '53_20252026_4830747',
            expectedDataVersion: RAW_MATCH_DATA_VERSIONS.FOTMOB_HTML_HYD_V1,
        }),
        { found: false, row: null, rows: 0 }
    );
});

test('requireSingleVersionRow returns row for exactly 1', () => {
    const expected = row();
    const result = requireSingleVersionRow([expected], {
        expectedMatchId: expected.match_id,
        expectedDataVersion: expected.data_version,
    });
    assert.equal(result.found, true);
    assert.equal(result.row, expected);
    assert.equal(result.rows, 1);
});

test('requireSingleVersionRow errors for >1', () => {
    assert.throws(
        () =>
            requireSingleVersionRow([row({ id: 1 }), row({ id: 2 })], {
                expectedMatchId: '53_20252026_4830747',
                expectedDataVersion: RAW_MATCH_DATA_VERSIONS.FOTMOB_HTML_HYD_V1,
            }),
        /RAW_MATCH_DATA_VERSION_LOOKUP_DUPLICATE/
    );
});

test('requireSingleVersionRow rejects wrong match_id', () => {
    assert.throws(
        () =>
            requireSingleVersionRow([row({ match_id: 'wrong' })], {
                expectedMatchId: '53_20252026_4830747',
                expectedDataVersion: RAW_MATCH_DATA_VERSIONS.FOTMOB_HTML_HYD_V1,
            }),
        /expected match_id/
    );
});

test('requireSingleVersionRow rejects wrong data_version', () => {
    assert.throws(
        () =>
            requireSingleVersionRow([row({ data_version: RAW_MATCH_DATA_VERSIONS.FOTMOB_PAGEPROPS_V2 })], {
                expectedMatchId: '53_20252026_4830747',
                expectedDataVersion: RAW_MATCH_DATA_VERSIONS.FOTMOB_HTML_HYD_V1,
            }),
        /expected data_version/
    );
});

test('buildVersionAwareLookupSpec contains match_id and data_version', () => {
    const spec = buildVersionAwareLookupSpec();
    assert.match(spec.where, /match_id = \$1/);
    assert.match(spec.where, /data_version = \$2/);
    assert.deepEqual(DEFAULT_CANONICAL_VERSION_PRIORITY, [
        RAW_MATCH_DATA_VERSIONS.FOTMOB_PAGEPROPS_V2,
        RAW_MATCH_DATA_VERSIONS.FOTMOB_HTML_HYD_V1,
    ]);
});

test('conflict target is match_id,data_version', () => {
    const spec = buildVersionAwareLookupSpec();
    assert.deepEqual(spec.conflict_target, ['match_id', 'data_version']);
    assert.equal(spec.conflict_target_sql, '(match_id, data_version)');
});
