'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

const {
    calculateAlignmentScore,
    calculateStringSimilarity,
    extractOddsValues,
    formatCsvLine,
    hasAnyOddsValue,
    hasCompleteMarketOdds,
    hasCompleteOddsTriplet,
    mapOutcomeColumns,
    normalizeText,
    parseFootballDataDateTime,
    resolveCsvField,
    resolveLeagueTimezone,
    resolveLineValue,
    selectBestAlignmentCandidate,
    toCsvCell,
    buildExpandedOddsRows,
} = require('../../scripts/ops/helpers/euroLeagueAdapters');

test('euroLeagueAdapters 应规范化 CSV 字段、时间和文本相似度', () => {
    assert.equal(resolveLeagueTimezone('Bundesliga'), 'Europe/Berlin');
    assert.equal(resolveLeagueTimezone('Championship'), 'Europe/London');
    assert.equal(resolveLeagueTimezone('Unknown League'), 'UTC');
    assert.equal(resolveCsvField({ HomeTeam: '', home: 'Darmstadt' }, ['HomeTeam', 'home']), 'Darmstadt');
    assert.equal(resolveCsvField({ HomeTeam: '' }, ['HomeTeam', 'home']), null);
    assert.equal(toCsvCell('Borussia, Dortmund'), '"Borussia, Dortmund"');
    assert.equal(toCsvCell('He said "yes"'), '"He said ""yes"""');
    assert.equal(formatCsvLine({ home: 'A', away: 'B' }, ['away', 'home']), 'B,A');
    assert.equal(parseFootballDataDateTime('', '15:00'), null);
    assert.equal(parseFootballDataDateTime('01/08/22', '20:30', { timeZone: 'UTC' }), '2022-08-01T20:30:00.000Z');
    assert.equal(parseFootballDataDateTime('01/08/2022', '', { timeZone: 'UTC' }), '2022-08-01T15:00:00.000Z');
    assert.equal(normalizeText('Borussia Dortmund'), 'Borussia Dortmund');
    assert.equal(calculateStringSimilarity('', 'Dortmund'), 0);
    assert.equal(calculateStringSimilarity('Borussia Dortmund', 'Borussia Dortmund'), 1);
    assert.ok(calculateStringSimilarity('FC Koln', 'Koln') > 0.8);
});

test('euroLeagueAdapters 应给候选比赛生成可解释的对齐结果', () => {
    const target = {
        homeTeam: 'Hamburger SV',
        awayTeam: 'St Pauli',
        matchDate: '2022-08-01T18:30:00.000Z',
    };
    const candidates = [
        {
            match_id: 'later',
            home_team: 'Hamburger SV',
            away_team: 'St Pauli',
            match_date: '2022-08-01T19:00:00.000Z',
        },
        {
            match_id: 'best',
            home_team: 'Hamburger SV',
            away_team: 'St Pauli',
            match_date: '2022-08-01T18:30:00.000Z',
        },
    ];

    const score = calculateAlignmentScore({
        requestedHomeTeam: target.homeTeam,
        requestedAwayTeam: target.awayTeam,
        requestedMatchDate: target.matchDate,
        candidateHomeTeam: candidates[0].home_team,
        candidateAwayTeam: candidates[0].away_team,
        candidateMatchDate: candidates[0].match_date,
    });
    assert.equal(score.homeSimilarity, 1);
    assert.equal(score.awaySimilarity, 1);
    assert.ok(score.timeScore < 1);

    const matched = selectBestAlignmentCandidate([candidates[1]], target);
    assert.equal(matched.status, 'matched');
    assert.equal(matched.candidate.match_id, 'best');
    assert.equal(matched.alignmentMeta.name_similarity, 1);

    assert.equal(selectBestAlignmentCandidate([], target).status, 'not_found');
    assert.equal(
        selectBestAlignmentCandidate(
            [
                {
                    match_id: 'reversed',
                    home_team: 'St Pauli',
                    away_team: 'Hamburger SV',
                    match_date: target.matchDate,
                },
            ],
            target
        ).status,
        'orientation_conflict'
    );
    assert.equal(
        selectBestAlignmentCandidate(
            [
                {
                    match_id: 'weak',
                    home_team: 'Unrelated Home',
                    away_team: 'Unrelated Away',
                    match_date: target.matchDate,
                },
            ],
            target,
            { minConfidenceScore: 0.95, minOrientationMargin: -1 }
        ).status,
        'low_confidence'
    );
    assert.equal(selectBestAlignmentCandidate(candidates, target, { minScoreGap: 0.99 }).status, 'ambiguous');
});

test('euroLeagueAdapters 应展开多市场赔率行并标记低质量来源', () => {
    const row = {
        openHome: '1.80',
        openDraw: '3.50',
        openAway: '4.20',
        closeHome: '1.75',
        closeDraw: '3.60',
        closeAway: '4.40',
        over: '1.91',
        line: '2.5',
    };
    const oddsConfig = {
        Pinnacle: {
            '1x2': {
                open: { home: 'openHome', draw: 'openDraw', away: 'openAway' },
                close: { home: 'closeHome', draw: 'closeDraw', away: 'closeAway' },
                open_line_value: '',
                close_line: 'line',
            },
            goals: {
                open: { over: 'missingOver', under: 'missingUnder' },
                close: { over: 'over', under: 'missingUnder' },
                open_line: 'missingLine',
                close_line_value: '2.5',
            },
        },
    };

    const values = extractOddsValues(row, oddsConfig.Pinnacle['1x2'].open);
    assert.deepEqual(values, { home: '1.80', draw: '3.50', away: '4.20' });
    assert.equal(hasAnyOddsValue(values), true);
    assert.equal(hasAnyOddsValue({ home: '', away: null }), false);
    assert.equal(hasCompleteOddsTriplet(values), true);
    assert.equal(hasCompleteMarketOdds('1x2', values), true);
    assert.equal(hasCompleteMarketOdds('goals', { home: '1.91', away: '1.91' }), true);
    assert.equal(resolveLineValue(row, oddsConfig.Pinnacle['1x2'], 'close'), '2.5');
    assert.equal(resolveLineValue(row, oddsConfig.Pinnacle.goals, 'open'), '');
    assert.deepEqual(mapOutcomeColumns({}, { over: '1.91', under: '1.95' }), {
        home: '1.91',
        draw: null,
        away: '1.95',
    });

    const expanded = buildExpandedOddsRows(
        row,
        {
            oddsConfig,
            WARNING_LOW_QUALITY_SOURCE: 'LOW_QUALITY_SOURCE',
        },
        {
            match_id: 'D2_20222023_1',
            season: '2022/2023',
        }
    );

    assert.equal(expanded.length, 2);
    assert.equal(expanded[0].bookmaker_name, 'Pinnacle');
    assert.equal(expanded[0].market_type, '1x2');
    assert.equal(expanded[0].close_away, '4.40');
    assert.equal(expanded[0].quality_flags, '');
    assert.equal(expanded[1].market_type, 'goals');
    assert.equal(expanded[1].close_line, '2.5');
    assert.equal(expanded[1].quality_flags, 'LOW_QUALITY_SOURCE');
});
