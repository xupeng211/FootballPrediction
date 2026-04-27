'use strict';

const fuzzball = require('fuzzball');
const { Normalizer } = require('../../../src/utils/Normalizer');

const ALIGNMENT_NAME_WEIGHT = 0.7;
const ALIGNMENT_TIME_WEIGHT = 0.3;
const MAX_ALIGNMENT_TIME_WINDOW_MS = 6 * 60 * 60 * 1000;
const MIN_CONFIDENCE_SCORE = 0.85;
const MIN_ALIGNMENT_SCORE_GAP = 0.03;
const MIN_ORIENTATION_MARGIN = 0.05;
const LEAGUE_TIMEZONE_MAP = {
    'premier league': 'Europe/London',
    epl: 'Europe/London',
    championship: 'Europe/London',
    'scottish premiership': 'Europe/London',
    'la liga': 'Europe/London',
    laliga: 'Europe/London',
    'serie a': 'Europe/London',
    bundesliga: 'Europe/Berlin',
    'ligue 1': 'Europe/Berlin'
};
const DATE_TIME_FORMATTER_CACHE = new Map();

function normalizeText(value) {
    if (!value || typeof value !== 'string') return '';
    return Normalizer.normalizeTeamName(value);
}

function normalizeLookupKey(value) {
    return String(value || '')
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .toLowerCase()
        .replace(/[^\p{L}\p{N}]+/gu, ' ')
        .trim();
}

function resolveCsvField(row, candidates = []) {
    for (const key of candidates) {
        if (row[key] !== null && row[key] !== undefined && row[key] !== '') return row[key];
    }
    return null;
}

function getDateTimeFormatter(timeZone) {
    if (!DATE_TIME_FORMATTER_CACHE.has(timeZone)) {
        DATE_TIME_FORMATTER_CACHE.set(
            timeZone,
            new Intl.DateTimeFormat('en-CA', {
                timeZone,
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hour12: false
            })
        );
    }

    return DATE_TIME_FORMATTER_CACHE.get(timeZone);
}

function extractZonedParts(date, timeZone) {
    const values = {};
    for (const part of getDateTimeFormatter(timeZone).formatToParts(date)) {
        if (part.type !== 'literal') {
            values[part.type] = Number.parseInt(part.value, 10);
        }
    }
    return values;
}

function getTimeZoneOffsetMs(timestamp, timeZone) {
    const zoned = extractZonedParts(new Date(timestamp), timeZone);
    const asUtc = Date.UTC(
        zoned.year,
        (zoned.month || 1) - 1,
        zoned.day || 1,
        zoned.hour || 0,
        zoned.minute || 0,
        zoned.second || 0
    );
    return asUtc - timestamp;
}

function buildUtcDateFromZonedParts(parts, timeZone) {
    let timestamp = Date.UTC(
        parts.year,
        parts.month - 1,
        parts.day,
        parts.hour,
        parts.minute,
        0,
        0
    );

    for (let attempt = 0; attempt < 4; attempt++) {
        const nextTimestamp = Date.UTC(
            parts.year,
            parts.month - 1,
            parts.day,
            parts.hour,
            parts.minute,
            0,
            0
        ) - getTimeZoneOffsetMs(timestamp, timeZone);
        if (nextTimestamp === timestamp) {
            break;
        }
        timestamp = nextTimestamp;
    }

    const validation = extractZonedParts(new Date(timestamp), timeZone);
    if (
        validation.year !== parts.year
        || validation.month !== parts.month
        || validation.day !== parts.day
        || validation.hour !== parts.hour
        || validation.minute !== parts.minute
    ) {
        return null;
    }

    return new Date(timestamp);
}

function resolveLeagueTimezone(leagueName = '') {
    const lookupKey = normalizeLookupKey(leagueName);
    return LEAGUE_TIMEZONE_MAP[lookupKey] || 'UTC';
}

function toCsvCell(value) {
    if (value === null || value === undefined || value === '') return '';
    const str = String(value);
    return str.includes(',') || str.includes('"') || str.includes('\n') ? `"${str.replace(/"/g, '""')}"` : str;
}

function formatCsvLine(row, headers = null) {
    const values = Array.isArray(headers) && headers.length > 0
        ? headers.map((header) => row?.[header])
        : Object.values(row);
    return values.map(toCsvCell).join(',');
}

function parseFootballDataDateTime(dateValue, timeValue, options = {}) {
    if (!dateValue) return null;
    const parts = dateValue.split('/');
    if (parts.length !== 3) return null;
    const [day, month, year] = parts;
    const fullYear = year.length === 2 ? `20${year}` : year;
    const [hours, minutes] = timeValue && /^\d{2}:\d{2}$/.test(timeValue)
        ? timeValue.split(':').map((value) => Number.parseInt(value, 10))
        : [15, 0];
    const parsed = buildUtcDateFromZonedParts({
        year: Number.parseInt(fullYear, 10),
        month: Number.parseInt(month, 10),
        day: Number.parseInt(day, 10),
        hour: hours,
        minute: minutes
    }, options.timeZone || resolveLeagueTimezone(options.leagueName || options.leagueCode || ''));
    return parsed ? parsed.toISOString() : null;
}

function normalizeSimilarityInput(value) {
    return normalizeLookupKey(normalizeText(value));
}

function roundScore(value) {
    return Math.round(Number(value || 0) * 10000) / 10000;
}

function calculateStringSimilarity(left, right) {
    const normalizedLeft = normalizeSimilarityInput(left);
    const normalizedRight = normalizeSimilarityInput(right);
    if (!normalizedLeft || !normalizedRight) {
        return 0;
    }
    if (normalizedLeft === normalizedRight) {
        return 1;
    }

    const weightedRatio = Number(fuzzball.WRatio(normalizedLeft, normalizedRight) || 0) / 100;
    const tokenRatio = Number(fuzzball.token_sort_ratio(normalizedLeft, normalizedRight) || 0) / 100;
    return roundScore(Math.max(weightedRatio, tokenRatio));
}

function calculateAlignmentScore(options = {}) {
    const requestedDate = new Date(options.requestedMatchDate);
    const candidateDate = new Date(options.candidateMatchDate);
    const timeDiffMs = Math.abs(requestedDate.getTime() - candidateDate.getTime());
    const maxTimeWindowMs = options.maxTimeWindowMs || MAX_ALIGNMENT_TIME_WINDOW_MS;
    const timeScore = Number.isFinite(timeDiffMs) && timeDiffMs <= maxTimeWindowMs
        ? Math.max(0, 1 - (timeDiffMs / maxTimeWindowMs))
        : 0;

    const homeSimilarity = calculateStringSimilarity(options.requestedHomeTeam, options.candidateHomeTeam);
    const awaySimilarity = calculateStringSimilarity(options.requestedAwayTeam, options.candidateAwayTeam);
    const reversedHomeSimilarity = calculateStringSimilarity(options.requestedHomeTeam, options.candidateAwayTeam);
    const reversedAwaySimilarity = calculateStringSimilarity(options.requestedAwayTeam, options.candidateHomeTeam);
    const nameSimilarity = roundScore((homeSimilarity + awaySimilarity) / 2);
    const reversedSimilarity = roundScore((reversedHomeSimilarity + reversedAwaySimilarity) / 2);
    const orientationMargin = roundScore(nameSimilarity - reversedSimilarity);
    const matchScore = roundScore((nameSimilarity * ALIGNMENT_NAME_WEIGHT) + (timeScore * ALIGNMENT_TIME_WEIGHT));

    return {
        matchScore,
        nameSimilarity,
        timeScore: roundScore(timeScore),
        timeDiffMs,
        timeDiffSeconds: Math.round(timeDiffMs / 1000),
        homeSimilarity,
        awaySimilarity,
        reversedSimilarity,
        orientationMargin
    };
}

function selectBestAlignmentCandidate(candidates = [], target = {}, options = {}) {
    const maxTimeWindowMs = options.maxTimeWindowMs || MAX_ALIGNMENT_TIME_WINDOW_MS;
    const minConfidenceScore = options.minConfidenceScore || MIN_CONFIDENCE_SCORE;
    const minScoreGap = options.minScoreGap || MIN_ALIGNMENT_SCORE_GAP;
    const minOrientationMargin = options.minOrientationMargin || MIN_ORIENTATION_MARGIN;

    const ranked = candidates
        .map((candidate) => ({
            candidate,
            score: calculateAlignmentScore({
                requestedHomeTeam: target.homeTeam,
                requestedAwayTeam: target.awayTeam,
                requestedMatchDate: target.matchDate,
                candidateHomeTeam: candidate.home_team,
                candidateAwayTeam: candidate.away_team,
                candidateMatchDate: candidate.match_date,
                maxTimeWindowMs
            })
        }))
        .filter((entry) => Number.isFinite(entry.score.timeDiffMs) && entry.score.timeDiffMs <= maxTimeWindowMs)
        .sort((left, right) => (
            right.score.matchScore - left.score.matchScore
            || left.score.timeDiffMs - right.score.timeDiffMs
            || String(left.candidate.match_id || '').localeCompare(String(right.candidate.match_id || ''))
        ));

    if (ranked.length === 0) {
        return {
            status: 'not_found',
            ranked
        };
    }

    const best = ranked[0];
    if (best.score.orientationMargin < minOrientationMargin) {
        return {
            status: 'orientation_conflict',
            ranked
        };
    }
    if (best.score.matchScore < minConfidenceScore) {
        return {
            status: 'low_confidence',
            ranked
        };
    }

    const second = ranked[1];
    if (second && (best.score.matchScore - second.score.matchScore) < minScoreGap) {
        return {
            status: 'ambiguous',
            ranked
        };
    }

    return {
        status: 'matched',
        candidate: best.candidate,
        ranked,
        alignmentMeta: {
            match_score: best.score.matchScore,
            name_similarity: best.score.nameSimilarity,
            time_diff_seconds: best.score.timeDiffSeconds
        }
    };
}

function extractOddsValues(row, columns = {}) {
    const values = {};
    for (const [key, col] of Object.entries(columns)) {
        values[key] = row[col] ?? null;
    }
    return values;
}

function hasAnyOddsValue(oddsValues) {
    return Object.values(oddsValues).some((v) => v !== null && v !== undefined && v !== '');
}

function hasCompleteOddsTriplet(oddsValues) {
    return oddsValues.home !== null && oddsValues.home !== undefined &&
           oddsValues.draw !== null && oddsValues.draw !== undefined &&
           oddsValues.away !== null && oddsValues.away !== undefined;
}

function hasCompleteTwoWayOdds(oddsValues) {
    return oddsValues.home !== null && oddsValues.home !== undefined &&
           oddsValues.away !== null && oddsValues.away !== undefined;
}

function hasCompleteMarketOdds(marketType, oddsValues) {
    return normalizeText(marketType) === '1x2'
        ? hasCompleteOddsTriplet(oddsValues)
        : hasCompleteTwoWayOdds(oddsValues);
}

function resolveLineValue(row, config, phase) {
    const lineValue = config[`${phase}_line_value`];
    if (lineValue !== null && lineValue !== undefined && lineValue !== '') {
        return String(lineValue);
    }

    const lineCol = config[`${phase}_line`];
    if (!lineCol) return '';
    const val = row[lineCol];
    if (val === null || val === undefined || val === '') return '';
    return String(val);
}

function mapOutcomeColumns(config, values) {
    return {
        home: values.home !== undefined ? values.home : (values.over !== undefined ? values.over : null),
        draw: values.draw !== undefined ? values.draw : null,
        away: values.away !== undefined ? values.away : (values.under !== undefined ? values.under : null),
    };
}

function buildExpandedOddsRows(row, context, matchCore) {
    const rows = [];
    for (const [bookmakerName, markets] of Object.entries(context.oddsConfig)) {
        for (const [marketType, config] of Object.entries(markets)) {
            const openValues = extractOddsValues(row, config.open);
            const closeValues = extractOddsValues(row, config.close);
            if (!hasAnyOddsValue(openValues) && !hasAnyOddsValue(closeValues)) continue;
            const openOutcomes = mapOutcomeColumns(config.open, openValues);
            const closeOutcomes = mapOutcomeColumns(config.close, closeValues);
            const openLine = resolveLineValue(row, config, 'open');
            const closeLine = resolveLineValue(row, config, 'close');
            const hasOpenTriplet = hasCompleteMarketOdds(marketType, openOutcomes);
            const hasCloseTriplet = hasCompleteMarketOdds(marketType, closeOutcomes);
            const qualityFlags = [];
            if (!hasOpenTriplet && !hasCloseTriplet) {
                qualityFlags.push(context.WARNING_LOW_QUALITY_SOURCE);
            }
            rows.push({
                ...matchCore,
                bookmaker_name: bookmakerName,
                market_type: marketType,
                open_line: openLine,
                open_home: openOutcomes.home ?? '',
                open_draw: openOutcomes.draw ?? '',
                open_away: openOutcomes.away ?? '',
                close_line: closeLine,
                close_home: closeOutcomes.home ?? '',
                close_draw: closeOutcomes.draw ?? '',
                close_away: closeOutcomes.away ?? '',
                quality_flags: qualityFlags.join(','),
            });
        }
    }
    return rows;
}

module.exports = {
    ALIGNMENT_NAME_WEIGHT,
    ALIGNMENT_TIME_WEIGHT,
    MAX_ALIGNMENT_TIME_WINDOW_MS,
    MIN_CONFIDENCE_SCORE,
    MIN_ALIGNMENT_SCORE_GAP,
    MIN_ORIENTATION_MARGIN,
    resolveLeagueTimezone,
    normalizeText,
    resolveCsvField,
    toCsvCell,
    formatCsvLine,
    parseFootballDataDateTime,
    calculateStringSimilarity,
    calculateAlignmentScore,
    selectBestAlignmentCandidate,
    extractOddsValues,
    hasAnyOddsValue,
    hasCompleteOddsTriplet,
    hasCompleteMarketOdds,
    resolveLineValue,
    mapOutcomeColumns,
    buildExpandedOddsRows,
};
