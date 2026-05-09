'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

const {
    buildClientHintHeaders,
    mergeContextExtraHTTPHeaders,
    normalizeHeaderName,
    normalizeHeaders,
} = require('../../src/infrastructure/shared/helpers/browserHeaderUtils');
const {
    buildHttpStatusError,
    closeTargetWithTimeout,
    pageClosed,
    resolveBrowserProcessHandle,
    waitForDelay,
} = require('../../src/infrastructure/shared/helpers/browserUtils');
const {
    buildDiscoveryMatchId,
    extractDiscoveryDate,
    getDiscoveryExternalId,
    getDiscoveryTeamSeed,
    hasDiscoveryTeams,
    safeJsonPreview,
    toIsoTimestamp,
} = require('../../src/infrastructure/shared/helpers/discoveryParserShared');
const {
    buildDomScanPayload,
    dedupeById,
    extractPrimaryLeagueData,
} = require('../../src/infrastructure/shared/helpers/fotMobExtractionHelpers');
const {
    buildDeterministicMatchHash,
    parseMatchTeams,
    slugifyPathSegment,
} = require('../../src/infrastructure/shared/helpers/oddsPortalUrlUtils');
const { OddsPortalURLParser } = require('../../src/infrastructure/shared/helpers/OddsPortalURLParser');
const {
    buildForceOverwriteParams,
    buildMappingInsertPayload,
    buildMappingInsertQuery,
    buildMismatchInsertPayload,
    buildMismatchInsertQuery,
    buildOrderedMappings,
    buildStatusUpdateStatement,
    getConfidenceThreshold,
} = require('../../src/infrastructure/shared/helpers/reconMappingSqlBuilders');
const {
    decodeCandidateTeamSegment,
    extractCandidatePathname,
    extractTeamsFromH2hPath,
    hasTextualTeamName,
    isPlaceholderTeamName,
    isPlaceholderToken,
    normalizeDictionaryComparableName,
    normalizeLeaguePlaceComparableName,
    normalizeTeamName,
    splitCompositeTeamName,
    tokenizeIdentityName,
} = require('../../src/infrastructure/shared/helpers/reconNameHelpers');

test('browser header helpers cover normalization and client hint branches', () => {
    assert.equal(normalizeHeaderName(' Accept-Language '), 'accept-language');
    assert.deepEqual(
        normalizeHeaders({
            ' X-Test ': ' value ',
            Empty: '   ',
            Nullish: null,
            '': 'ignored',
        }),
        { 'x-test': 'value' }
    );

    assert.deepEqual(buildClientHintHeaders('Mozilla/5.0 Edg/125.0.0.0', 'Win32'), {
        'sec-ch-ua': '"Chromium";v="125", "Microsoft Edge";v="125", "Not_A Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
    });
    assert.equal(buildClientHintHeaders('Mozilla/5.0 Chrome/126.0.0.0', 'MacIntel')['sec-ch-ua-platform'], '"macOS"');
    assert.equal(
        buildClientHintHeaders('Mozilla/5.0 Chrome/126.0.0.0 Linux x86_64', 'Win32')['sec-ch-ua-platform'],
        '"Linux"'
    );
    assert.deepEqual(buildClientHintHeaders('plain-agent', 'Win32'), {});

    const merged = mergeContextExtraHTTPHeaders({
        baseHeaders: {
            'Accept-Language': 'fr-FR',
            'Sec-Ch-Ua': 'existing',
        },
        extraHeaders: {
            'X-Test': ' ok ',
            'Sec-Fetch-Dest': 'iframe',
        },
        userAgent: ' BrowserUA ',
        platform: 'Linux',
    });

    assert.equal(merged['accept-language'], 'fr-FR');
    assert.equal(merged['sec-ch-ua'], 'existing');
    assert.equal(merged['sec-fetch-dest'], 'iframe');
    assert.equal(merged['x-test'], 'ok');
    assert.equal(merged['user-agent'], 'BrowserUA');

    const defaults = mergeContextExtraHTTPHeaders();
    assert.equal(defaults['accept-language'], 'en-US,en;q=0.9');
    assert.equal(defaults['sec-fetch-mode'], 'navigate');
    assert.equal(defaults['user-agent'], undefined);
});

test('browser utility helpers cover close, delay, and process handle branches', async () => {
    assert.equal(pageClosed(null), true);
    assert.equal(pageClosed({ isClosed: () => true }), true);
    assert.equal(pageClosed({ isClosed: () => false }), false);
    assert.equal(pageClosed({}), false);

    let waited = 0;
    await waitForDelay(
        {
            waitForTimeout: async ms => {
                waited = ms;
            },
            isClosed: () => false,
        },
        3
    );
    assert.equal(waited, 3);
    await waitForDelay(
        {
            waitForTimeout: async () => {
                throw new Error('should not wait on closed page');
            },
            isClosed: () => true,
        },
        1
    );
    await waitForDelay(null, 0);

    const statusError = buildHttpStatusError(503, 'upstream unavailable', { retryable: true });
    assert.equal(statusError.statusCode, 503);
    assert.equal(statusError.retryable, true);

    const directHandle = { pid: 1001 };
    assert.equal(resolveBrowserProcessHandle({ process: () => directHandle }, null), directHandle);
    const contextHandle = { pid: 1002 };
    assert.equal(
        resolveBrowserProcessHandle({ process: () => null }, { browser: () => ({ process: () => contextHandle }) }),
        contextHandle
    );
    assert.equal(resolveBrowserProcessHandle({}, {}), null);

    assert.equal(await closeTargetWithTimeout('missing', null), false);
    assert.equal(await closeTargetWithTimeout('skipped', { close: async () => {} }, { skip: true }), false);
    assert.equal(await closeTargetWithTimeout('success', { close: async () => {} }, { timeoutMs: 5 }), false);

    const warnings = [];
    assert.equal(
        await closeTargetWithTimeout(
            'rejecting',
            {
                close: async () => {
                    throw new Error('close failed');
                },
            },
            {
                logger: { warn: (...args) => warnings.push(args) },
                meta: { workerId: 7 },
                eventName: 'target_close_failed',
            }
        ),
        true
    );
    assert.equal(warnings[0][0], 'target_close_failed');
    assert.equal(warnings[0][1].workerId, 7);
    assert.equal(warnings[0][1].timedOut, false);

    assert.equal(
        await closeTargetWithTimeout(
            'timeout',
            { close: () => new Promise(() => {}) },
            {
                timeoutMs: 1,
                logger: { warn: (...args) => warnings.push(args) },
            }
        ),
        true
    );
    assert.equal(warnings[1][1].timedOut, true);
});

test('discovery parser shared helpers cover id, date, preview, and match-id branches', () => {
    assert.equal(getDiscoveryExternalId({ id: 1001 }), 1001);
    assert.equal(getDiscoveryExternalId({ matchId: 'm-2' }), 'm-2');
    assert.equal(getDiscoveryExternalId({ match_id: 'm-3' }), 'm-3');
    assert.equal(getDiscoveryExternalId({}), null);

    assert.equal(getDiscoveryTeamSeed({ homeTeam: 'Arsenal' }, 'home'), 'Arsenal');
    assert.equal(getDiscoveryTeamSeed({ away_team: 'Chelsea' }, 'away'), 'Chelsea');
    assert.equal(getDiscoveryTeamSeed({ home_name: 'Spurs' }, 'home'), 'Spurs');
    assert.equal(getDiscoveryTeamSeed({}, 'home'), null);
    assert.equal(hasDiscoveryTeams({ home: 'A', away: 'B' }), true);
    assert.equal(hasDiscoveryTeams({ home: 'A' }), false);

    assert.equal(
        extractDiscoveryDate({ status: { utcTime: '2026-01-02T03:04:05Z' } }).toISOString(),
        '2026-01-02T03:04:05.000Z'
    );
    assert.equal(
        extractDiscoveryDate({ kickoff: { datetime: '2026-02-03T04:05:06Z' } }).toISOString(),
        '2026-02-03T04:05:06.000Z'
    );
    assert.equal(extractDiscoveryDate({ date: 'not-a-date' }), null);
    assert.equal(extractDiscoveryDate({}), null);

    assert.equal(safeJsonPreview({ value: 'abcdef' }, 12), '{"value":"ab');
    assert.equal(safeJsonPreview(undefined), '');
    const circular = {};
    circular.self = circular;
    assert.equal(safeJsonPreview(circular), '[unserializable response]');

    assert.equal(buildDiscoveryMatchId(47, '2024', 12345), '47_2024_12345');
    assert.equal(buildDiscoveryMatchId(47, '2024/2025', 12345), '47_20242025_12345');
    assert.equal(buildDiscoveryMatchId(47, '2024/2026', 12345), '47_20242026_12345');
    assert.equal(toIsoTimestamp('invalid-date'), null);
});

test('FotMob extraction helpers cover fallback, pageProps, DOM payload, and dedupe branches', () => {
    const logs = [];
    const resultFromLeagueIdParam = extractPrimaryLeagueData(
        {
            fallback: {
                '/api/data/leagues?leagueId=54&season=20242025': { fixtures: [{ id: 'target' }] },
            },
        },
        '54',
        '2024/2025',
        data => data.fixtures.length,
        { info: message => logs.push(message) }
    );

    assert.equal(resultFromLeagueIdParam.matchCount, 1);
    assert.deepEqual(resultFromLeagueIdParam.data.fixtures, [{ id: 'target' }]);
    assert.equal(logs.length, 1);

    const resultFromPath = extractPrimaryLeagueData(
        {
            fallback: {
                '/api/data/leagues/47/overview': { fixtures: [{ id: 'from-path' }] },
            },
        },
        47,
        '2024/2025',
        data => data.fixtures.length,
        { info() {} }
    );
    assert.equal(resultFromPath.data.fixtures[0].id, 'from-path');

    const resultFromAllMatches = extractPrimaryLeagueData(
        { allMatches: [{ id: 'm1' }], marker: 'allMatches' },
        47,
        '2024/2025',
        data => data.fixtures.length,
        { info() {} }
    );
    assert.equal(resultFromAllMatches.matchCount, 1);
    assert.equal(resultFromAllMatches.data.marker, 'allMatches');

    assert.deepEqual(
        extractPrimaryLeagueData({ fallback: null }, 47, '2024/2025', () => 0, { info() {} }),
        { data: null, matchCount: 0 }
    );
    assert.deepEqual(buildDomScanPayload([{ id: 'dom-1' }], 47, '2024/2025'), {
        fixtures: { allMatches: [{ id: 'dom-1' }] },
        leagueId: 47,
        season: '2024/2025',
        _source: 'dom_scan',
    });
    assert.deepEqual(dedupeById([{ id: 'a' }, { id: 'a' }, { id: 'b' }]), [{ id: 'a' }, { id: 'b' }]);
});

test('OddsPortal URL helpers cover slug, hash, and team parsing branches', () => {
    assert.equal(slugifyPathSegment('Real Madrid & Barça!!'), 'real-madrid-and-barca');
    assert.equal(buildDeterministicMatchHash('/Football/England/Match'), '09d70035');
    assert.deepEqual(parseMatchTeams(''), { home_team: null, away_team: null });
    assert.deepEqual(parseMatchTeams('manchester-united-vs-chelsea'), {
        home_team: 'Manchester United',
        away_team: 'Chelsea',
    });
    assert.deepEqual(parseMatchTeams('arsenal'), {
        home_team: 'Arsenal',
        away_team: null,
    });
    assert.deepEqual(parseMatchTeams('real-madrid-barcelona'), {
        home_team: 'Real Madrid',
        away_team: 'Barcelona',
    });
    assert.deepEqual(parseMatchTeams('newcastle-united-west-ham'), {
        home_team: 'Newcastle United',
        away_team: 'West Ham United',
    });
});

test('OddsPortal URL parser covers invalid, non-soccer, explicit hash, and deterministic hash branches', () => {
    assert.equal(OddsPortalURLParser.parseMatchURL('not a url'), null);
    assert.equal(OddsPortalURLParser.parseMatchURL('https://www.oddsportal.com/soccer/england/'), null);
    assert.equal(
        OddsPortalURLParser.parseMatchURL('https://www.oddsportal.com/tennis/england/premier-league-2024-2025/a/b/'),
        null
    );

    const explicit = OddsPortalURLParser.parseMatchURL(
        'https://www.oddsportal.com/soccer/england/premier-league-2024-2025/AbC12345/arsenal-chelsea/'
    );
    assert.equal(explicit.league, 'premier-league');
    assert.equal(explicit.season, '2024/2025');
    assert.equal(explicit.match_hash, 'abc12345');
    assert.equal(explicit.home_team, 'Arsenal');
    assert.equal(explicit.away_team, 'Chelsea');

    const deterministic = OddsPortalURLParser.parseMatchURL(
        'https://www.oddsportal.com/soccer/spain/laliga/real-madrid-vs-barcelona/'
    );
    assert.equal(deterministic.season, null);
    assert.equal(deterministic.match_hash, buildDeterministicMatchHash(deterministic.full_path));
    assert.equal(deterministic.home_team, 'Real Madrid');
    assert.equal(deterministic.away_team, 'Barcelona');
});

test('recon name helpers cover normalization, URL extraction, and placeholder branches', () => {
    assert.equal(normalizeTeamName(' St. Etienne FC '), 'st etienne fc');
    assert.equal(normalizeDictionaryComparableName('Arsenal (Women) [U21]'), 'arsenal');
    assert.equal(normalizeLeaguePlaceComparableName('AS St-Etienne FC'), 'fc saint etienne');
    assert.deepEqual(splitCompositeTeamName(' Alpha / Beta\\Gamma '), ['Alpha', 'Beta', 'Gamma']);
    assert.equal(hasTextualTeamName('123 Alpha'), true);
    assert.equal(hasTextualTeamName('12345'), false);
    assert.equal(hasTextualTeamName(null), false);

    assert.equal(
        extractCandidatePathname('https://www.oddsportal.com/football/h2h/team-a/team-b/?x=1#top'),
        '/football/h2h/team-a/team-b/'
    );
    assert.equal(extractCandidatePathname('/football/h2h/team-a/team-b?x=1#top'), '/football/h2h/team-a/team-b');
    assert.equal(extractCandidatePathname(''), '');
    assert.equal(decodeCandidateTeamSegment('manchester-united-ABC12345'), 'Manchester United');
    assert.equal(decodeCandidateTeamSegment(''), '');
    assert.deepEqual(extractTeamsFromH2hPath('/football/h2h/manchester-united-ABC12345/chelsea/'), {
        homeTeam: 'Manchester United',
        awayTeam: 'Chelsea',
    });
    assert.equal(extractTeamsFromH2hPath('/football/results/'), null);
    assert.deepEqual(tokenizeIdentityName('São Paulo FC!'), ['sao', 'paulo', 'fc']);

    assert.equal(isPlaceholderToken('12abc'), true);
    assert.equal(isPlaceholderToken('abc12'), false);
    assert.equal(isPlaceholderTeamName(''), false);
    assert.equal(isPlaceholderTeamName('Play-off winner'), true);
    assert.equal(isPlaceholderTeamName('Winner Semi Final'), true);
    assert.equal(isPlaceholderTeamName('1a 2b'), true);
    assert.equal(isPlaceholderTeamName('Team 1a'), false);
});

test('recon mapping SQL builders cover optional field and fallback branches without executing SQL', () => {
    const hashFor = matchId => `hash-${matchId}`;
    const evidence = {
        match_id: 'm-1',
        full_url: '',
        season: '2024/2025',
        league_name: 'Premier League',
        home_team: 'Arsenal',
        away_team: 'Chelsea',
        match_confidence: 0.72,
        mapping_method: '',
        is_reversed: true,
        candidate_name: '',
    };
    const allOptional = {
        match_confidence: true,
        mapping_method: true,
        is_reversed: true,
        candidate_name: true,
        is_evidence_only: true,
    };
    const mismatchPayload = buildMismatchInsertPayload(evidence, allOptional, hashFor);

    assert.deepEqual(mismatchPayload.columns.slice(-5), [
        'match_confidence',
        'mapping_method',
        'is_reversed',
        'candidate_name',
        'is_evidence_only',
    ]);
    assert.equal(mismatchPayload.params[1], 'hash-m-1');
    assert.match(mismatchPayload.params[2], /^evidence:\/\/recon\/m-1$/);
    assert.equal(mismatchPayload.params.at(-4), 'unknown');
    assert.equal(mismatchPayload.params.at(-2), null);
    assert.equal(mismatchPayload.params.at(-1), true);
    assert.match(
        buildMismatchInsertQuery(mismatchPayload.columns, mismatchPayload.values, allOptional),
        /is_evidence_only = TRUE/
    );

    const minimalStatus = buildStatusUpdateStatement('m-1', 'RECON_LINKED');
    assert.deepEqual(minimalStatus.params, ['m-1', 'RECON_LINKED']);
    assert.doesNotMatch(minimalStatus.query, /NOT EXISTS/);

    const guardedStatus = buildStatusUpdateStatement('m-2', 'RECON_MISMATCH', {
        expectedCurrentStatus: 'harvested',
        requireNoMapping: true,
    });
    assert.deepEqual(guardedStatus.params, ['m-2', 'RECON_MISMATCH', 'harvested']);
    assert.match(guardedStatus.query, /NOT EXISTS/);

    assert.deepEqual(
        buildOrderedMappings([{ match_id: 'b' }, { match_id: 'a' }]).map(mapping => mapping.match_id),
        ['a', 'b']
    );

    assert.equal(getConfidenceThreshold(), undefined);
    assert.equal(getConfidenceThreshold({ matching: { confidence_threshold: 0.66 } }), 0.66);

    const mappingPayload = buildMappingInsertPayload(
        {
            match_id: 'm-3',
            oddsportal_hash: 'op-hash',
            full_url: 'https://example.test/match',
            season: '2024/2025',
            league_name: 'Premier League',
            home_team: 'Spurs',
            away_team: 'Everton',
            status: '',
            match_confidence: undefined,
            mapping_method: '',
            is_reversed: false,
        },
        allOptional,
        { matching: { confidence_threshold: 0.81 } }
    );

    assert.equal(mappingPayload.params[7], 'pending');
    assert.equal(mappingPayload.params.at(-4), 0.81);
    assert.equal(mappingPayload.params.at(-3), 'protocol_extract');
    assert.equal(mappingPayload.params.at(-2), false);
    assert.equal(mappingPayload.params.at(-1), false);

    const defaultInsertQuery = buildMappingInsertQuery({}, mappingPayload, allOptional);
    assert.match(defaultInsertQuery, /match_confidence = EXCLUDED\.match_confidence/);
    assert.match(defaultInsertQuery, /candidate_name = NULL/);
    assert.match(defaultInsertQuery, /is_evidence_only = FALSE/);

    const templatedQuery = buildMappingInsertQuery(
        { save_mapping: 'columns={columns}; values={values}; updates={optional_updates}' },
        mappingPayload,
        { match_confidence: true }
    );
    assert.match(templatedQuery, /^columns=match_id/);
    assert.match(templatedQuery, /updates=, match_confidence = EXCLUDED\.match_confidence$/);

    assert.deepEqual(
        buildForceOverwriteParams(
            { match_id: 'existing' },
            {
                match_id: 'incoming',
                full_url: 'https://example.test/incoming',
                league_name: 'LaLiga',
                home_team: 'Real Madrid',
                away_team: 'Barcelona',
                status: '',
                match_confidence: undefined,
                mapping_method: '',
                is_reversed: true,
                season: '2024/2025',
                oddsportal_hash: 'incoming-hash',
            },
            allOptional,
            { matching: { confidence_threshold: 0.77 } }
        ),
        [
            'incoming',
            'https://example.test/incoming',
            'LaLiga',
            'Real Madrid',
            'Barcelona',
            'pending',
            0.77,
            'protocol_extract',
            true,
            '2024/2025',
            'incoming-hash',
            'existing',
        ]
    );
    assert.equal(buildForceOverwriteParams({ match_id: 'existing' }, { match_id: 'incoming' }, {}, {})[6], null);
});
