'use strict';

const PARSER_VERSION = 'PHASE4.62C_FOOTBALL_DATA_LOCAL_CSV_PARSER';
const DEFAULT_SOURCE_NAME = 'football_data_local_csv';
const DEFAULT_DATA_VERSION = 'PHASE4.62C_LOCAL_PARSER';
const DEFAULT_SEASON = 'UNKNOWN_SEASON';
const DEFAULT_TIMEZONE = 'UTC';
const NON_EXECUTION_CONFIRMATIONS = [
    'no_external_network',
    'no_db_reads',
    'no_db_writes',
    'no_file_writes',
    'no_legacy_runtime',
    'no_training',
    'no_prediction_execution',
];
const DIVISION_NAME_MAP = {
    E0: 'Premier League',
    E1: 'Championship',
    SP1: 'La Liga',
    SP2: 'Segunda Division',
    D1: 'Bundesliga',
    D2: '2. Bundesliga',
    I1: 'Serie A',
    I2: 'Serie B',
    F1: 'Ligue 1',
    F2: 'Ligue 2',
    N1: 'Eredivisie',
    P1: 'Liga Portugal',
};
const SUPPORTED_ODDS_BOOKMAKERS = [
    {
        bookmaker: 'Bet365',
        columns: {
            home: 'B365H',
            draw: 'B365D',
            away: 'B365A',
        },
    },
    {
        bookmaker: 'Pinnacle',
        columns: {
            home: 'PSH',
            draw: 'PSD',
            away: 'PSA',
        },
    },
];

function normalizeText(value) {
    return String(value || '').trim();
}

function normalizeTeamName(value) {
    return normalizeText(value).replace(/\s+/g, ' ');
}

function toIntegerOrNull(value) {
    const text = normalizeText(value);
    if (!text) {
        return null;
    }
    if (!/^-?\d+$/.test(text)) {
        return null;
    }
    return Number.parseInt(text, 10);
}

function toFloatOrNull(value) {
    const text = normalizeText(value);
    if (!text) {
        return null;
    }
    const parsed = Number.parseFloat(text);
    return Number.isFinite(parsed) ? parsed : null;
}

function mapDivisionToLeagueName(divisionCode) {
    const normalizedCode = normalizeText(divisionCode).toUpperCase();
    return DIVISION_NAME_MAP[normalizedCode] || normalizedCode || 'UNKNOWN_LEAGUE';
}

function deriveSeasonFromIsoDate(matchDate) {
    const date = new Date(matchDate);
    if (Number.isNaN(date.getTime())) {
        return DEFAULT_SEASON;
    }
    const month = date.getUTCMonth() + 1;
    const startYear = month >= 7 ? date.getUTCFullYear() : date.getUTCFullYear() - 1;
    const endYear = startYear + 1;
    return `${startYear}/${endYear}`;
}

function mapFtrToActualResult(ftr) {
    const normalized = normalizeText(ftr).toUpperCase();
    if (normalized === 'H') {
        return 'home_win';
    }
    if (normalized === 'D') {
        return 'draw';
    }
    if (normalized === 'A') {
        return 'away_win';
    }
    return null;
}

function deriveActualResultFromScores(homeScore, awayScore) {
    if (!Number.isInteger(homeScore) || !Number.isInteger(awayScore)) {
        return null;
    }
    if (homeScore > awayScore) {
        return 'home_win';
    }
    if (homeScore < awayScore) {
        return 'away_win';
    }
    return 'draw';
}

function splitCsvLine(line) {
    const values = [];
    let current = '';
    let insideQuotes = false;

    for (let index = 0; index < line.length; index++) {
        const character = line[index];
        const nextCharacter = line[index + 1];

        if (character === '"') {
            if (insideQuotes && nextCharacter === '"') {
                current += '"';
                index += 1;
                continue;
            }
            insideQuotes = !insideQuotes;
            continue;
        }

        if (character === ',' && !insideQuotes) {
            values.push(current);
            current = '';
            continue;
        }

        current += character;
    }

    values.push(current);
    return values;
}

function parseCsvText(csvText) {
    const normalizedText = String(csvText || '')
        .replace(/^\uFEFF/, '')
        .replace(/\r\n/g, '\n')
        .replace(/\r/g, '\n');
    const lines = normalizedText
        .split('\n')
        .map(line => line.trimEnd())
        .filter(line => line.trim() !== '');

    if (lines.length === 0) {
        return [];
    }

    const headers = splitCsvLine(lines[0]).map(header => normalizeText(header));
    return lines.slice(1).map(line => {
        const cells = splitCsvLine(line);
        return headers.reduce((row, header, index) => {
            row[header] = cells[index] !== undefined ? cells[index] : '';
            return row;
        }, {});
    });
}

function normalizeRowsInput(csvTextOrRows) {
    if (Array.isArray(csvTextOrRows)) {
        return csvTextOrRows.map(row => ({ ...row }));
    }
    return parseCsvText(csvTextOrRows);
}

function parseDateParts(dateText) {
    const normalized = normalizeText(dateText);
    const match = normalized.match(/^(\d{1,2})\/(\d{1,2})\/(\d{2}|\d{4})$/);
    if (!match) {
        return null;
    }

    const day = Number.parseInt(match[1], 10);
    const month = Number.parseInt(match[2], 10);
    const yearText = match[3];
    const year = yearText.length === 2 ? 2000 + Number.parseInt(yearText, 10) : Number.parseInt(yearText, 10);

    return { day, month, year };
}

function parseTimeParts(timeText) {
    const normalized = normalizeText(timeText);
    if (!normalized) {
        return { hour: 0, minute: 0 };
    }
    const match = normalized.match(/^(\d{1,2}):(\d{2})$/);
    if (!match) {
        return null;
    }
    return {
        hour: Number.parseInt(match[1], 10),
        minute: Number.parseInt(match[2], 10),
    };
}

function parseFootballDataDate(dateText, timeText, options = {}) {
    const dateParts = parseDateParts(dateText);
    const timeParts = parseTimeParts(timeText);

    if (!dateParts || !timeParts) {
        return null;
    }

    const { day, month, year } = dateParts;
    const { hour, minute } = timeParts;
    const utcDate = new Date(Date.UTC(year, month - 1, day, hour, minute, 0, 0));

    if (
        utcDate.getUTCFullYear() !== year
        || utcDate.getUTCMonth() + 1 !== month
        || utcDate.getUTCDate() !== day
        || utcDate.getUTCHours() !== hour
        || utcDate.getUTCMinutes() !== minute
    ) {
        return null;
    }

    if (normalizeText(options.timezone || DEFAULT_TIMEZONE).toUpperCase() !== 'UTC') {
        return utcDate.toISOString();
    }

    return utcDate.toISOString();
}

function buildOddsBookmakerPreview(row, config) {
    const homePresent = Object.prototype.hasOwnProperty.call(row, config.columns.home);
    const drawPresent = Object.prototype.hasOwnProperty.call(row, config.columns.draw);
    const awayPresent = Object.prototype.hasOwnProperty.call(row, config.columns.away);
    const recognizedColumns = [config.columns.home, config.columns.draw, config.columns.away].filter(column =>
        Object.prototype.hasOwnProperty.call(row, column)
    );

    if (!homePresent && !drawPresent && !awayPresent) {
        return null;
    }

    const values = {
        home: toFloatOrNull(row[config.columns.home]),
        draw: toFloatOrNull(row[config.columns.draw]),
        away: toFloatOrNull(row[config.columns.away]),
    };
    const hasAnyValue = Object.values(values).some(value => value !== null);
    const completeTriplet = Object.values(values).every(value => value !== null);

    return {
        bookmaker: config.bookmaker,
        recognized_columns: recognizedColumns,
        supported_columns_present: homePresent && drawPresent && awayPresent,
        has_any_value: hasAnyValue,
        complete_triplet: completeTriplet,
        values,
    };
}

function detectOddsColumns(row) {
    const bookmakers = SUPPORTED_ODDS_BOOKMAKERS.map(config => buildOddsBookmakerPreview(row, config)).filter(Boolean);
    return {
        available: bookmakers.length > 0,
        odds_preview_only: true,
        bookmakers,
    };
}

function buildWarning(rowNumber, code, message) {
    return {
        row_number: rowNumber,
        code,
        message,
    };
}

function buildBaseMeta(context = {}) {
    return {
        sourceName: normalizeText(context.sourceName) || DEFAULT_SOURCE_NAME,
        dataVersion: normalizeText(context.dataVersion) || DEFAULT_DATA_VERSION,
        defaultSeason: normalizeText(context.defaultSeason) || DEFAULT_SEASON,
        timezone: normalizeText(context.timezone) || DEFAULT_TIMEZONE,
    };
}

function resolveResult(homeScore, awayScore, ftrValue) {
    const hasFtrValue = normalizeText(ftrValue) !== '';
    const resultFromFtr = mapFtrToActualResult(ftrValue);
    const resultFromScore = deriveActualResultFromScores(homeScore, awayScore);

    if (hasFtrValue && !resultFromFtr) {
        return {
            actualResult: null,
            resultSource: null,
            invalidResult: true,
            mismatch: false,
        };
    }

    if (resultFromFtr && resultFromScore && resultFromFtr !== resultFromScore) {
        return {
            actualResult: null,
            resultSource: null,
            invalidResult: true,
            mismatch: true,
        };
    }

    if (resultFromFtr) {
        return {
            actualResult: resultFromFtr,
            resultSource: 'FTR',
            invalidResult: false,
            mismatch: false,
        };
    }

    if (resultFromScore) {
        return {
            actualResult: resultFromScore,
            resultSource: 'score_derived',
            invalidResult: false,
            mismatch: false,
        };
    }

    return {
        actualResult: null,
        resultSource: null,
        invalidResult: true,
        mismatch: false,
    };
}

function buildRowCore(row, meta) {
    const homeTeam = normalizeTeamName(row.HomeTeam);
    const awayTeam = normalizeTeamName(row.AwayTeam);
    const homeScore = toIntegerOrNull(row.FTHG);
    const awayScore = toIntegerOrNull(row.FTAG);
    const oddsPreview = detectOddsColumns(row);
    const matchDate = parseFootballDataDate(row.Date, row.Time, { timezone: meta.timezone });
    const resolvedResult = resolveResult(homeScore, awayScore, row.FTR);

    return {
        homeTeam,
        awayTeam,
        homeScore,
        awayScore,
        oddsPreview,
        matchDate,
        resolvedResult,
    };
}

function buildRowDiagnostics(row, rowNumber, rowCore) {
    const warnings = [];
    const flags = {
        invalid_date: false,
        missing_team: false,
        missing_score: false,
        invalid_result: false,
        odds_preview_available: rowCore.oddsPreview.available,
    };

    if (!rowCore.homeTeam || !rowCore.awayTeam) {
        flags.missing_team = true;
        warnings.push(buildWarning(rowNumber, 'missing_team', 'HomeTeam or AwayTeam is missing; row skipped.'));
    }

    if (!rowCore.matchDate) {
        flags.invalid_date = true;
        warnings.push(buildWarning(rowNumber, 'invalid_date', `Unable to parse Date/Time: Date=${row.Date || ''} Time=${row.Time || ''}`));
    }

    if (!Number.isInteger(rowCore.homeScore) || !Number.isInteger(rowCore.awayScore)) {
        flags.missing_score = true;
        warnings.push(buildWarning(rowNumber, 'missing_score', 'FTHG / FTAG is missing or invalid; row is not a finished label candidate.'));
    }

    if (rowCore.resolvedResult.invalidResult) {
        flags.invalid_result = true;
        warnings.push(
            buildWarning(
                rowNumber,
                rowCore.resolvedResult.mismatch ? 'result_score_mismatch' : 'invalid_result',
                rowCore.resolvedResult.mismatch
                    ? 'FTR conflicts with the score-derived result; row skipped.'
                    : 'Unable to derive actual_result from FTR or score; row skipped.'
            )
        );
    }

    return {
        warnings,
        flags,
    };
}

function normalizeFootballDataRow(row, context = {}) {
    const meta = buildBaseMeta(context);
    const rowNumber = Number.isInteger(context.rowNumber) ? context.rowNumber : 0;
    const rowCore = buildRowCore(row, meta);
    const diagnostics = buildRowDiagnostics(row, rowNumber, rowCore);
    const errors = [];
    const { warnings, flags } = diagnostics;
    const shouldSkip = flags.invalid_date || flags.missing_team || flags.missing_score || flags.invalid_result;
    if (shouldSkip) {
        return {
            row_number: rowNumber,
            status: 'skipped',
            skip_reason: resolveSkipReason(flags),
            normalized_row: null,
            warnings,
            errors,
            flags,
            odds_preview: rowCore.oddsPreview,
        };
    }

    const normalizedRow = {
        row_number: rowNumber,
        league_code: normalizeText(row.Div).toUpperCase(),
        league_name: mapDivisionToLeagueName(row.Div),
        season: meta.defaultSeason !== DEFAULT_SEASON ? meta.defaultSeason : deriveSeasonFromIsoDate(rowCore.matchDate),
        match_date: rowCore.matchDate,
        home_team: rowCore.homeTeam,
        away_team: rowCore.awayTeam,
        home_score: rowCore.homeScore,
        away_score: rowCore.awayScore,
        actual_result: rowCore.resolvedResult.actualResult,
        result_source: rowCore.resolvedResult.resultSource,
        data_source: meta.sourceName,
        data_version: meta.dataVersion,
        odds_preview: rowCore.oddsPreview,
        would_insert_matches: false,
        would_insert_odds: false,
        odds_preview_only: true,
        label_only_fields: ['FTHG', 'FTAG', 'FTR'],
    };

    return {
        row_number: rowNumber,
        status: 'candidate',
        skip_reason: null,
        normalized_row: normalizedRow,
        warnings,
        errors,
        flags,
        odds_preview: rowCore.oddsPreview,
    };
}

function resolveSkipReason(flags) {
    if (flags.invalid_date) {
        return 'invalid_date';
    }
    if (flags.missing_team) {
        return 'missing_team';
    }
    if (flags.missing_score) {
        return 'missing_score';
    }
    if (flags.invalid_result) {
        return 'invalid_result';
    }
    return 'skipped';
}

function classifyFootballDataRows(normalizedEntries = []) {
    return normalizedEntries.reduce(
        (summary, entry) => {
            if (entry.normalized_row) {
                summary.finished_rows += 1;
                summary.trainable_label_rows += 1;
                if (entry.flags.odds_preview_available) {
                    summary.odds_preview_rows += 1;
                }
            } else {
                summary.skipped_rows += 1;
            }

            if (entry.flags.invalid_date) {
                summary.invalid_date_rows += 1;
            }
            if (entry.flags.missing_team) {
                summary.missing_team_rows += 1;
            }
            if (entry.flags.missing_score) {
                summary.missing_score_rows += 1;
            }
            if (entry.flags.invalid_result) {
                summary.invalid_result_rows += 1;
            }

            return summary;
        },
        {
            finished_rows: 0,
            trainable_label_rows: 0,
            skipped_rows: 0,
            invalid_date_rows: 0,
            missing_team_rows: 0,
            missing_score_rows: 0,
            invalid_result_rows: 0,
            odds_preview_rows: 0,
        }
    );
}

function parseFootballDataCsv(csvTextOrRows, options = {}) {
    const meta = buildBaseMeta(options);
    const rows = normalizeRowsInput(csvTextOrRows);
    const normalizedEntries = rows.map((row, index) =>
        normalizeFootballDataRow(row, {
            ...meta,
            rowNumber: index + 1,
        })
    );
    const candidateRows = normalizedEntries.map(entry => entry.normalized_row).filter(Boolean);
    const warnings = normalizedEntries.flatMap(entry => entry.warnings);
    const errors = normalizedEntries.flatMap(entry => entry.errors);

    return {
        parser_version: PARSER_VERSION,
        source_name: meta.sourceName,
        total_rows: rows.length,
        parsed_rows: rows.length,
        candidate_rows: candidateRows,
        row_classification: classifyFootballDataRows(normalizedEntries),
        warnings,
        errors,
        non_execution_confirmations: [...NON_EXECUTION_CONFIRMATIONS],
    };
}

module.exports = {
    parseFootballDataCsv,
    normalizeFootballDataRow,
    mapFtrToActualResult,
    parseFootballDataDate,
    detectOddsColumns,
    classifyFootballDataRows,
};
