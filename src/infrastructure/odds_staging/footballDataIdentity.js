'use strict';

// lifecycle: permanent；Football-Data 历史 CSV 的确定性比赛身份：球队别名、赛季推导、Europe/London 时间解释。
// 不依赖模糊匹配、Double Metaphone、网络或数据库。

const ALLOWED_COMPETITIONS = Object.freeze(['Premier League']);
const ALLOWED_SEASONS = Object.freeze(['2022/2023', '2023/2024', '2024/2025']);

const COMPETITION_MAP = Object.freeze({
    E0: 'Premier League',
});

const FOOTBALL_DATA_TEAM_ALIASES = Object.freeze({
    luton: 'Luton Town',
    bournemouth: 'AFC Bournemouth',
    brighton: 'Brighton & Hove Albion',
    leeds: 'Leeds United',
    leicester: 'Leicester City',
    'man city': 'Manchester City',
    'man united': 'Manchester United',
    newcastle: 'Newcastle United',
    "nott'm forest": 'Nottingham Forest',
    tottenham: 'Tottenham Hotspur',
    'west ham': 'West Ham United',
    wolves: 'Wolverhampton Wanderers',
});

function normalizeIdentityText(value) {
    return String(value ?? '')
        .normalize('NFKC')
        .trim()
        .toLowerCase()
        .replace(/\s+/g, ' ')
        .trim();
}

function normalizeAliasTarget(value) {
    return String(value ?? '')
        .normalize('NFKC')
        .trim();
}

/**
 * Resolve a Football-Data source team name to its FotMob canonical name.
 * Only applies the 12 verified, source-scoped, exact aliases.
 * Unknown names are returned as-is (no fuzzy matching).
 * @param {string} rawName
 * @returns {string} resolved canonical name
 */
function resolveFootballDataTeamName(rawName) {
    const normalized = normalizeIdentityText(rawName);
    const alias = FOOTBALL_DATA_TEAM_ALIASES[normalized];
    return alias ? normalizeAliasTarget(alias) : normalizeAliasTarget(rawName);
}

/**
 * Map competition code to canonical competition name.
 * Only E0 → Premier League is authorized.
 * Non-E0 codes remain as-is; caller must validate.
 * @param {string} rawDiv
 * @returns {string}
 */
function resolveCompetition(rawDiv) {
    const code = String(rawDiv ?? '').trim();
    return COMPETITION_MAP[code] || code;
}

/**
 * Parse a strict DD/MM/YYYY or DD/MM/YY date and validate it is a real calendar date.
 * Returns { year, month, day } or null.
 */
function parseStrictDate(dateStr) {
    const text = String(dateStr ?? '').trim();
    if (!text) return null;

    // DD/MM/YYYY or DD/MM/YY
    const match = /^(\d{1,2})\/(\d{1,2})\/(\d{2,4})$/.exec(text);
    if (!match) return null;

    const day = Number(match[1]);
    const month = Number(match[2]);
    let year = Number(match[3]);

    // Two-digit year expansion: 00-49 → 2000-2049, 50-99 → 1950-1999
    if (year < 100) {
        year += year < 50 ? 2000 : 1900;
    }

    if (month < 1 || month > 12) return null;
    if (day < 1 || day > 31) return null;

    // Validate actual calendar date
    const daysInMonth = new Date(Date.UTC(year, month, 0)).getUTCDate();
    if (day > daysInMonth) return null;

    return { year, month, day };
}

/**
 * Parse a date and validate as a real calendar date.
 * Also supports YYYY-MM-DD format.
 */
function parseAndValidateDate(dateStr) {
    const text = String(dateStr ?? '').trim();
    if (!text) return null;

    // Try YYYY-MM-DD first
    const isoMatch = /^(\d{4})-(\d{2})-(\d{2})$/.exec(text);
    if (isoMatch) {
        const year = Number(isoMatch[1]);
        const month = Number(isoMatch[2]);
        const day = Number(isoMatch[3]);
        if (month < 1 || month > 12 || day < 1) return null;
        const dim = new Date(Date.UTC(year, month, 0)).getUTCDate();
        if (day > dim) return null;
        return { year, month, day };
    }

    return parseStrictDate(text);
}

/**
 * Derive football season from a valid parsed date.
 * Season = YYYY/YYYY+1 for Aug-Dec, (YYYY-1)/YYYY for Jan-(June? No: July).
 * Month >= 7 (July) → season starts in this year.
 * Month < 7 (Jan-Jun) → season started in previous year.
 * Month == 7 is actually July which starts the new season. Wait:
 * Football season: August (8) to May (5) of next year.
 * So month >= 8 → YYYY/YYYY+1; month <= 5 → (YYYY-1)/YYYY; months 6,7 → edge.
 *
 * Strict rule from M3-D3A-R calibration: month >= 7 → year/year+1; month < 7 → year-1/year.
 * (This handles the July edge case and aligns with M3-D3 diagnostic behavior.)
 */
function deriveSeason(year, month) {
    if (month >= 7) {
        return `${year}/${year + 1}`;
    }
    return `${year - 1}/${year}`;
}

/**
 * Validate that a derived season is within the authorized set.
 */
function isAllowedSeason(season) {
    return ALLOWED_SEASONS.includes(season);
}

/**
 * Determine the Europe/London UTC offset in minutes for a given date.
 * Uses IANA-style DST rules via Intl.DateTimeFormat.
 * BST (UTC+1, offset=60): last Sunday of March 01:00 UTC → last Sunday of October 01:00 UTC
 * GMT (UTC+0, offset=0): otherwise
 *
 * Returns offset in minutes, or null on error.
 */
const LONDON_PARTS_FORMATTER = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Europe/London',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
});

function parseStrictLocalTime(dateStr, timeStr) {
    const date = parseAndValidateDate(dateStr);
    const match = /^(\d{1,2}):(\d{2})$/.exec(String(timeStr ?? '').trim());
    if (!date || !match || Number(match[1]) > 23 || Number(match[2]) > 59) return null;
    return { ...date, hour: Number(match[1]), minute: Number(match[2]) };
}

function localPartsAt(instant) {
    return LONDON_PARTS_FORMATTER.formatToParts(new Date(instant)).reduce((result, part) => {
        if (['year', 'month', 'day', 'hour', 'minute'].includes(part.type)) result[part.type] = Number(part.value);
        return result;
    }, {});
}

function localPartsEqual(left, right) {
    return ['year', 'month', 'day', 'hour', 'minute'].every(field => left[field] === right[field]);
}

function resolveLondonLocalInstant(local) {
    const naiveUtcMs = Date.UTC(local.year, local.month - 1, local.day, local.hour, local.minute);
    const offsets = new Set();
    for (let hours = -48; hours <= 48; hours += 1) {
        const instant = naiveUtcMs + hours * 60 * 60 * 1000;
        const actual = localPartsAt(instant);
        offsets.add(Date.UTC(actual.year, actual.month - 1, actual.day, actual.hour, actual.minute) - instant);
    }
    return [...offsets]
        .map(offset => naiveUtcMs - offset)
        .filter(instant => localPartsEqual(localPartsAt(instant), local))
        .filter((instant, index, values) => values.indexOf(instant) === index)
        .sort((left, right) => left - right);
}

/**
 * Convert a source local Date+Time to an absolute UTC ISO-8601 timestamp,
 * using the explicit Europe/London interpretation.
 *
 * @param {string} dateStr - DD/MM/YYYY or YYYY-MM-DD
 * @param {string} timeStr - HH:MM
 * @param {object} interpretation - the validated kickoff_time_interpretation from manifest
 * @returns {{ kickoff_at: string|null, error: string|null }}
 */
function deriveKickoffAt(dateStr, timeStr, interpretation) {
    if (!interpretation) return { kickoff_at: null, error: 'kickoff_timezone_unresolved' };
    if (interpretation.status !== 'derived' || interpretation.timezone !== 'Europe/London') {
        return { kickoff_at: null, error: 'kickoff_interpretation_invalid' };
    }
    if (!String(timeStr ?? '').trim()) return { kickoff_at: null, error: 'kickoff_missing' };
    const local = parseStrictLocalTime(dateStr, timeStr);
    if (!local) return { kickoff_at: null, error: 'kickoff_invalid' };
    const candidates = resolveLondonLocalInstant(local);
    if (candidates.length === 0) return { kickoff_at: null, error: 'kickoff_local_time_nonexistent' };
    if (candidates.length > 1) return { kickoff_at: null, error: 'kickoff_local_time_ambiguous' };
    return { kickoff_at: new Date(candidates[0]).toISOString().replace('.000', ''), error: null };
}

/**
 * Validate the kickoff_time_interpretation manifest object.
 * Returns { valid: boolean, errors: string[] }
 */
function validateKickoffTimeInterpretation(interpretation) {
    if (interpretation === undefined || interpretation === null) return { valid: true, errors: [] };
    if (!interpretation || typeof interpretation !== 'object' || Array.isArray(interpretation)) {
        return { valid: false, errors: ['kickoff_time_interpretation must be a plain object'] };
    }
    const required = {
        status: 'derived',
        timezone: 'Europe/London',
        method: 'source_local_calendar_time',
        evidence_level: 'empirical_cross_source',
        official_source_declaration: false,
    };
    const errors = Object.entries(required)
        .filter(([field, value]) => interpretation[field] !== value)
        .map(([field, value]) => `kickoff_time_interpretation.${field} must be ${JSON.stringify(value)}`);
    if (typeof interpretation.evidence_reference !== 'string' || !interpretation.evidence_reference.trim()) {
        errors.push('kickoff_time_interpretation.evidence_reference must be a non-empty string');
    }
    appendAllowedValuesErrors(
        errors,
        interpretation.allowed_competitions,
        'allowed_competitions',
        ALLOWED_COMPETITIONS,
        true
    );
    appendAllowedValuesErrors(errors, interpretation.allowed_seasons, 'allowed_seasons', ALLOWED_SEASONS, false);
    const known = new Set([...Object.keys(required), 'evidence_reference', 'allowed_competitions', 'allowed_seasons']);
    Object.keys(interpretation)
        .filter(field => !known.has(field))
        .forEach(field => errors.push(`kickoff_time_interpretation contains unknown field: ${field}`));
    return { valid: errors.length === 0, errors };
}

function appendAllowedValuesErrors(errors, values, field, allowed, requirePremierLeagueOnly) {
    if (!Array.isArray(values) || values.length === 0) {
        errors.push(`kickoff_time_interpretation.${field} must be a non-empty array`);
        return;
    }
    if (new Set(values).size !== values.length) {
        errors.push(`kickoff_time_interpretation.${field} must not contain duplicates`);
    }
    if (values.some(value => !allowed.includes(value))) {
        errors.push(
            `kickoff_time_interpretation.${field} contains unauthorized ${field === 'allowed_competitions' ? 'competition' : 'season'}`
        );
    }
    if (requirePremierLeagueOnly && (values.length !== 1 || values[0] !== 'Premier League')) {
        errors.push('kickoff_time_interpretation.allowed_competitions must contain only Premier League');
    }
}

/**
 * Check if a kickoff_time_interpretation is applicable for the given context.
 * Only for historical_git_recovery + football-data-csv with source_timezone=unknown.
 */
function isInterpretationApplicable(manifest) {
    if (!manifest) return false;
    if (!manifest.kickoff_time_interpretation) return false;
    if (manifest.acquisition_mode !== 'historical_git_recovery') return false;
    if (manifest.adapter !== 'football-data-csv') return false;
    if (manifest.adapter_version !== '1.2.0') return false;
    if (String(manifest.source_timezone || '').toUpperCase() !== 'UNKNOWN') return false;
    return true;
}

/**
 * Build the kickoff_time_interpretation evidence object for an observation.
 */
function buildKickoffInterpretationEvidence(interpretation, sourceDate, sourceTime) {
    if (!interpretation) return null;
    return {
        status: 'derived',
        timezone: 'Europe/London',
        method: 'source_local_calendar_time',
        evidence_level: 'empirical_cross_source',
        official_source_declaration: false,
        source_local_date: String(sourceDate ?? '').trim(),
        source_local_time: String(sourceTime ?? '').trim(),
        evidence_reference: String(interpretation.evidence_reference || '').trim(),
    };
}

module.exports = {
    ALLOWED_COMPETITIONS,
    ALLOWED_SEASONS,
    COMPETITION_MAP,
    FOOTBALL_DATA_TEAM_ALIASES,
    buildKickoffInterpretationEvidence,
    deriveKickoffAt,
    deriveSeason,
    isAllowedSeason,
    isInterpretationApplicable,
    normalizeIdentityText,
    parseAndValidateDate,
    parseStrictDate,
    resolveCompetition,
    resolveFootballDataTeamName,
    validateKickoffTimeInterpretation,
};
