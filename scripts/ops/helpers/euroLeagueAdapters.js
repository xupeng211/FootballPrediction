'use strict';

const { Normalizer } = require('../../../src/utils/Normalizer');

function normalizeText(value) {
    if (!value || typeof value !== 'string') return '';
    return Normalizer.normalizeTeamName(value);
}

function resolveCsvField(row, candidates = []) {
    for (const key of candidates) {
        if (row[key] !== null && row[key] !== undefined && row[key] !== '') return row[key];
    }
    return null;
}

function toCsvCell(value) {
    if (value === null || value === undefined || value === '') return '';
    const str = String(value);
    return str.includes(',') || str.includes('"') || str.includes('\n') ? `"${str.replace(/"/g, '""')}"` : str;
}

function formatCsvLine(row) {
    return Object.values(row).map(toCsvCell).join(',');
}

function parseFootballDataDateTime(dateValue, timeValue) {
    if (!dateValue) return null;
    const parts = dateValue.split('/');
    if (parts.length !== 3) return null;
    const [day, month, year] = parts;
    const fullYear = year.length === 2 ? `20${year}` : year;
    let isoDate = `${fullYear}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;
    if (timeValue && /^\d{2}:\d{2}$/.test(timeValue)) {
        isoDate += `T${timeValue}:00.000Z`;
    } else {
        isoDate += 'T15:00:00.000Z';
    }
    const parsed = new Date(isoDate);
    return Number.isNaN(parsed.getTime()) ? null : parsed.toISOString();
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

function resolveLineValue(row, config, phase) {
    const lineCol = config[`${phase}_line`];
    if (!lineCol) return '';
    const val = row[lineCol];
    if (val === null || val === undefined || val === '') return '';
    return String(val);
}

function mapOutcomeColumns(config, values) {
    return {
        home: values[config.home] !== undefined ? values[config.home] : null,
        draw: values[config.draw] !== undefined ? values[config.draw] : null,
        away: values[config.away] !== undefined ? values[config.away] : null,
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
            const openLine = resolveLineValue(row, config.open, 'open');
            const closeLine = resolveLineValue(row, config.close, 'close');
            const hasOpenTriplet = hasCompleteOddsTriplet(openOutcomes);
            const hasCloseTriplet = hasCompleteOddsTriplet(closeOutcomes);
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
    normalizeText,
    resolveCsvField,
    toCsvCell,
    formatCsvLine,
    parseFootballDataDateTime,
    extractOddsValues,
    hasAnyOddsValue,
    hasCompleteOddsTriplet,
    resolveLineValue,
    mapOutcomeColumns,
    buildExpandedOddsRows,
};
