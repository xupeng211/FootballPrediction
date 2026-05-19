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
const {
    calculateVolatilityMetrics,
    extractOddsArray,
    extractOddsArrays,
    findBookieById,
    findValuesByKey,
    normalizeOddsTriplet,
    normalizeTimestampValue,
    validatePurity,
} = require('../../src/infrastructure/shared/helpers/oddsPortalShared');
const {
    deepParseOddsData,
    extractClosingOdds,
    extractOpeningOdds,
    processOddsTimeline,
    recursiveHistoryScanner,
} = require('../../src/infrastructure/shared/helpers/oddsPortalTimeline');
const {
    extractAndTransform,
    extractFromHtml,
    extractNextData,
    transformToApiFormat,
    validateNextDataStructure,
} = require('../../src/parsers/fotmob/NextDataParser');
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
    assertFunctionDependency,
    assertMismatchEvidenceFields,
    assertObjectDependency,
    assertRequiredFields,
    assertSuccessfulRebind,
    buildEvidenceOnlyHash,
    buildForceOverwriteAssignments,
    classifyWriteError,
    getPreserveLinkedStatusFlag,
    isSeasonHashUniqueViolation,
    scoreFixturePair,
    scoreUrlAgainstMatch,
    shouldForceOverwriteEvidenceOnlyConflict,
    shouldPreferIncomingProtocolOverwrite,
    shouldPreferIncomingSequentialHashOverwrite,
} = require('../../src/infrastructure/shared/helpers/reconMappingStoreShared');
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

test('NextDataParser covers safe pageProps extraction and transform failure branches without browser runtime', async () => {
    const nextData = {
        props: {
            pageProps: {
                content: {
                    stats: { xg: [1.1, 0.8] },
                    lineup: { home: [] },
                    shotmap: [{ id: 1 }],
                },
                general: { matchId: 'detail-1' },
                header: { teams: ['Home', 'Away'] },
            },
        },
    };
    const html = `<html><script id="__NEXT_DATA__" type="application/json">${JSON.stringify(nextData)}</script></html>`;
    const extracted = extractFromHtml(html);
    assert.equal(extracted.success, true);
    assert.deepEqual(extracted.data.props.pageProps.general, { matchId: 'detail-1' });

    const alt = extractFromHtml(
        `<script type="application/json" id="__NEXT_DATA__">${JSON.stringify(nextData)}</script>`
    );
    assert.equal(alt.success, true);
    assert.equal(extractFromHtml(null).error, 'INVALID_INPUT:HTML 不是有效字符串');
    assert.match(extractFromHtml('<html></html>').error, /^NO_NEXT_DATA:/);
    assert.match(extractFromHtml('<script id="__NEXT_DATA__">{bad</script>').error, /^PARSE_ERROR:/);
    assert.match(
        extractFromHtml('<script type="application/json" id="__NEXT_DATA__">{bad</script>').error,
        /^PARSE_ERROR:/
    );

    const api = transformToApiFormat(nextData, 'match-1');
    assert.equal(api.matchId, 'match-1');
    assert.equal(api._meta.hasStats, true);
    assert.equal(api._meta.hasLineup, true);
    assert.equal(api._meta.hasShotmap, true);
    assert.equal(transformToApiFormat(null, 'match-1'), null);
    assert.equal(transformToApiFormat({ props: { pageProps: {} } }, 'match-1'), null);

    assert.deepEqual(validateNextDataStructure(null), { valid: false, missing: ['nextData'] });
    assert.deepEqual(validateNextDataStructure({}), { valid: false, missing: ['props'] });
    assert.deepEqual(validateNextDataStructure({ props: {} }), { valid: false, missing: ['props.pageProps'] });
    assert.deepEqual(validateNextDataStructure({ props: { pageProps: {} } }), {
        valid: false,
        missing: ['props.pageProps.content'],
    });
    assert.deepEqual(validateNextDataStructure(nextData), { valid: true, missing: [] });

    const makePage = value => ({
        evaluate: async callback => {
            global.document = {
                getElementById: () => value,
            };
            try {
                return callback();
            } finally {
                delete global.document;
            }
        },
    });
    assert.equal((await extractNextData(makePage({ innerHTML: JSON.stringify(nextData) }))).success, true);
    assert.match((await extractNextData(makePage(null))).error, /^NO_NEXT_DATA:/);
    assert.match((await extractNextData(makePage({ innerHTML: '{bad' }))).error, /^PARSE_ERROR:/);
    assert.match(
        (
            await extractNextData({
                evaluate: async () => {
                    throw new Error('safe evaluate failure');
                },
            })
        ).error,
        /^EXTRACT_ERROR:/
    );

    assert.equal(
        (await extractAndTransform(makePage({ innerHTML: JSON.stringify(nextData) }), 'match-2')).success,
        true
    );
    assert.match((await extractAndTransform(makePage(null), 'match-2')).error, /^NO_NEXT_DATA:/);
    assert.match(
        (await extractAndTransform(makePage({ innerHTML: JSON.stringify({ props: {} }) }), 'match-2')).error,
        /^INVALID_STRUCTURE:/
    );
    assert.match(
        (
            await extractAndTransform(
                makePage({ innerHTML: JSON.stringify({ props: { pageProps: { content: { ok: true } } } }) }),
                'match-2'
            )
        ).data.matchId,
        /^match-2$/
    );
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

test('OddsPortal shared and timeline helpers cover pure parser branches', () => {
    assert.equal(normalizeTimestampValue(null), null);
    assert.equal(normalizeTimestampValue(''), null);
    assert.equal(normalizeTimestampValue('2026-01-02T03:04:05Z'), 1767323045);
    assert.equal(normalizeTimestampValue(1767323045000), 1767323045);
    assert.equal(normalizeOddsTriplet(['2.10', '3.40', '3.20']).join(','), '2.1,3.4,3.2');
    assert.equal(normalizeOddsTriplet({ home: '2.10', draw: '3.40', away: '3.20' }).join(','), '2.1,3.4,3.2');
    assert.equal(normalizeOddsTriplet(['1.00', '3.40', '3.20']), null);
    assert.equal(
        extractOddsArray([{ value: ['bad'] }, { value: { h: 2.1, d: 3.4, a: 3.2 } }]).join(','),
        '2.1,3.4,3.2'
    );
    assert.equal(extractOddsArray([]), null);
    assert.equal(extractOddsArrays({ market: { odds: ['2.10', '3.40', '3.20'] } }).rawArrays[0].path, 'market.odds');

    const purityWarnOnly = validatePurity(['bad', '3.40', '3.20'], { strictMode: false });
    assert.equal(purityWarnOnly.valid, false);
    assert.equal(purityWarnOnly.purity_score, 67);
    assert.equal(validatePurity('bad').errors[0], '赔率数据必须是数组');
    assert.equal(validatePurity([2.1, 3.4]).errors[0], '赔率数组长度必须为3，当前为2');
    const volatility = calculateVolatilityMetrics([{ o: [2.0, 3.0, 4.0] }, { o: [2.2, 3.1, 3.8] }]);
    assert.equal(volatility.total_movement_count, 2);
    assert.equal(calculateVolatilityMetrics(null).total_movement_count, 0);

    const foundValues = findValuesByKey({ nested: { oddsHistory: [1, 2, 3] } }, 'history');
    assert.equal(foundValues[0].path.join('.'), 'nested.oddsHistory');
    assert.equal(findBookieById({ providers: [{ id: 18, opening: [2.1, 3.4, 3.2] }] }, 'pinnacle').id, 18);
    assert.equal(findBookieById({ providers: [{ name: 'Bet365 Sportsbook' }] }, 'bet365').name, 'Bet365 Sportsbook');

    const historyPoints = recursiveHistoryScanner({
        bookie: {
            history: [
                { o: [2.1, 3.4, 3.2], t: 1767323045 },
                { odds: [2.2, 3.3, 3.1], timestamp: 1767326645 },
                { o: [2.2, 3.3, 3.1], ts: 1767326645 },
            ],
            current: { home: 2.2, draw: 3.3, away: 3.1, ts: 1767326645 },
        },
    });
    const timeline = processOddsTimeline(historyPoints);
    assert.equal(timeline.opening[0], 2.1);
    assert.equal(timeline.closing[0], 2.2);
    assert.equal(timeline._point_count, 2);
    assert.deepEqual(processOddsTimeline([{ o: [2.1, 3.4, 3.2] }, { o: [2.2, 3.3, 3.1] }]).history, [
        { o: [2.1, 3.4, 3.2] },
        { o: [2.2, 3.3, 3.1] },
    ]);
    assert.equal(processOddsTimeline([]), null);

    const warningCalls = [];
    const originalWarn = console.warn;
    console.warn = (...args) => warningCalls.push(args);
    try {
        assert.equal(extractOpeningOdds(null, 'pinnacle'), null);
        assert.equal(extractClosingOdds({ closing: ['bad', 3.4, 3.2] }, 'pinnacle'), null);
    } finally {
        console.warn = originalWarn;
    }
    assert.equal(warningCalls.length, 0);
    assert.deepEqual(
        extractOpeningOdds({ initial: [2.1, 3.4, 3.2], initial_at: '2026-01-02T03:04:05Z' }, 'pinnacle').o,
        [2.1, 3.4, 3.2]
    );
    assert.deepEqual(
        extractClosingOdds({ odds: { current: { h: 2.2, d: 3.3, a: 3.1, ts: 1767326645 } } }, 'bet365').o,
        [2.2, 3.3, 3.1]
    );

    const parsed = deepParseOddsData({
        providers: [
            {
                id: 18,
                opening: [2.1, 3.4, 3.2],
                current: [2.2, 3.3, 3.1],
            },
            {
                name: 'Bet365',
                history: [{ o: [2.3, 3.2, 3.0], t: 1767323045 }],
            },
        ],
    });
    assert.equal(parsed.pinnacle.bookmaker_id, 18);
    assert.equal(parsed.bet365.bookmaker_id, 16);
    assert.equal(deepParseOddsData(null).pinnacle, null);
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

test('recon mapping store shared helpers cover pure conflict and error classification branches', () => {
    class RepositoryError extends Error {
        constructor(message, code, cause = null, details = null) {
            super(message);
            this.code = code;
            this.cause = cause;
            this.details = details;
        }
    }

    assert.throws(() => assertFunctionDependency('query', null), /缺少必需依赖/);
    assert.throws(() => assertObjectDependency('pool', null), /缺少必需依赖/);
    assert.doesNotThrow(() => assertFunctionDependency('query', () => {}));
    assert.doesNotThrow(() => assertObjectDependency('pool', {}));
    assert.equal(getPreserveLinkedStatusFlag({ preserve_linked_status: true }), true);
    assert.equal(
        shouldForceOverwriteEvidenceOnlyConflict({ is_evidence_only: true }, { is_evidence_only: false }),
        true
    );
    assert.match(buildEvidenceOnlyHash('m-1'), /^~[a-f0-9]{7}$/);
    assert.deepEqual(buildForceOverwriteAssignments({ match_confidence: true, candidate_name: true }).slice(-2), [
        'match_confidence = $7',
        'candidate_name = NULL',
    ]);

    assert.throws(
        () => assertRequiredFields(RepositoryError, { match_id: 'm-1' }),
        error => error.code === 'MISSING_REQUIRED_FIELDS'
    );
    assert.throws(
        () => assertMismatchEvidenceFields(RepositoryError, { match_id: 'm-1' }),
        error => error.code === 'MISMATCH_EVIDENCE_REQUIRED_FIELDS'
    );
    assert.doesNotThrow(() =>
        assertRequiredFields(RepositoryError, {
            match_id: 'm-1',
            oddsportal_hash: 'h',
            full_url: 'https://example.test/a',
            season: '2024/2025',
            league_name: 'Ligue 1',
            home_team: 'Home',
            away_team: 'Away',
        })
    );
    assert.throws(
        () => assertSuccessfulRebind(RepositoryError, 0, { match_id: 'm-1' }),
        error => error.code === 'HASH_CONFLICT_REBIND_FAILED' && error.details.match_id === 'm-1'
    );
    assert.doesNotThrow(() => assertSuccessfulRebind(RepositoryError, 1));

    assert.equal(isSeasonHashUniqueViolation(null), false);
    assert.equal(isSeasonHashUniqueViolation({ code: '23505', constraint: 'idx_mapping_season_hash_unique' }), true);
    assert.equal(
        isSeasonHashUniqueViolation(
            { code: '23505', detail: 'Key (season, oddsportal_hash)=(2024/2025,h) already exists.' },
            { season: '2024/2025', oddsportal_hash: 'h' }
        ),
        true
    );
    assert.equal(
        classifyWriteError(new RepositoryError('kept', 'KEPT'), {
            RepositoryError,
            mappingData: {},
            defaultCode: 'DEFAULT',
            defaultMessage: 'default',
        }).code,
        'KEPT'
    );
    assert.equal(
        classifyWriteError(
            { code: '23503', message: 'fk failed' },
            { RepositoryError, mappingData: {}, defaultCode: 'DEFAULT', defaultMessage: 'default' }
        ).code,
        'FOREIGN_KEY_VIOLATION'
    );
    assert.equal(
        classifyWriteError(
            { code: '23505', message: 'unique failed' },
            { RepositoryError, mappingData: null, defaultCode: 'DEFAULT', defaultMessage: 'default' }
        ).code,
        'UNIQUE_VIOLATION'
    );
    assert.equal(
        classifyWriteError(
            { code: '23502', message: 'not null failed' },
            { RepositoryError, mappingData: {}, defaultCode: 'DEFAULT', defaultMessage: 'default' }
        ).code,
        'NOT_NULL_VIOLATION'
    );
    assert.equal(
        classifyWriteError(
            { code: 'XX000', message: 'unknown failed' },
            { RepositoryError, mappingData: {}, defaultCode: 'DEFAULT', defaultMessage: 'default' }
        ).code,
        'DEFAULT'
    );

    const arbiter = {
        sameFixtureThreshold: 1.5,
        sameFixtureWindowMs: 60_000,
        teamSimilarity(left, right) {
            return String(left).split(' ')[0].toLowerCase() === String(right).split(' ')[0].toLowerCase() ? 1 : 0;
        },
    };
    const existingMatch = { home_team: 'Alpha FC', away_team: 'Beta FC', match_date: '2026-01-01T12:00:00Z' };
    const incomingMatch = { home_team: 'Alpha United', away_team: 'Beta City', match_date: '2026-01-03T12:00:00Z' };
    assert.equal(scoreFixturePair(arbiter, existingMatch, incomingMatch).bestScore, 2);
    assert.equal(
        scoreUrlAgainstMatch(arbiter, 'https://example.test/football/h2h/alpha-fc/beta-fc/', existingMatch),
        2
    );
    assert.equal(scoreUrlAgainstMatch(arbiter, 'not-a-url', existingMatch), 0);
    assert.equal(
        shouldPreferIncomingSequentialHashOverwrite({
            arbiter,
            existingMatch,
            incomingMatch,
            existingMapping: { full_url: 'https://example.test/match/alpha-beta-11111111', match_confidence: 0.75 },
            incomingMapping: { full_url: 'https://example.test/match/alpha-beta-22222222', match_confidence: 0.8 },
            decision: { sameFixture: false, dateDistanceMs: 172_800_000 },
        }),
        true
    );
    assert.equal(
        shouldPreferIncomingProtocolOverwrite({
            arbiter,
            existingMatch,
            incomingMatch,
            existingMapping: { full_url: 'https://example.test/football/h2h/gamma/delta/' },
            incomingMapping: {
                full_url: 'https://example.test/football/france/alpha-united-beta-city-abcdef12/',
                mapping_method: 'protocol_extract',
            },
            decision: { incomingScore: 2, existingScore: 0 },
        }),
        true
    );
});
