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
function londonUtcOffsetMinutes(year, month, day) {
    try {
        // Create a date at noon local time on the given date
        // Use Intl.DateTimeFormat to get the actual IANA timezone offset
        const formatter = new Intl.DateTimeFormat('en-US', {
            timeZone: 'Europe/London',
            timeZoneName: 'longOffset',
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            hour12: false,
        });

        // Build a UTC timestamp for noon on the target date
        // We use noon UTC as the reference point and let formatter tell us the offset
        const targetDate = new Date(Date.UTC(year, month - 1, day, 12, 0, 0));
        const parts = formatter.formatToParts(targetDate);

        // Find the timeZoneName part which contains the offset like "GMT+1" or "GMT"
        let offsetStr = null;
        for (const part of parts) {
            if (part.type === 'timeZoneName') {
                offsetStr = part.value;
                break;
            }
        }

        if (!offsetStr) return null;

        // Parse offset from strings like "GMT+1", "GMT+01:00", "GMT"
        const offsetMatch = /^GMT([+-]\d{1,2})(?::(\d{2}))?$/.exec(offsetStr);
        if (offsetMatch) {
            const hours = Number(offsetMatch[1]);
            const minutes = offsetMatch[2] ? Number(offsetMatch[2]) : 0;
            if (hours < 0) return hours * 60 - minutes;
            return hours * 60 + minutes;
        }

        // Just "GMT" without offset = UTC+0
        if (offsetStr === 'GMT') {
            return 0;
        }

        return null;
    } catch {
        return null;
    }
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
    if (!interpretation) {
        return { kickoff_at: null, error: 'kickoff_timezone_unresolved' };
    }

    if (interpretation.status !== 'derived') {
        return { kickoff_at: null, error: 'kickoff_interpretation_invalid' };
    }

    if (interpretation.timezone !== 'Europe/London') {
        return { kickoff_at: null, error: 'kickoff_interpretation_invalid' };
    }

    const parsed = parseAndValidateDate(dateStr);
    if (!parsed) {
        return { kickoff_at: null, error: 'kickoff_invalid' };
    }

    const { year, month, day } = parsed;

    const timeText = String(timeStr ?? '').trim();
    if (!timeText) {
        return { kickoff_at: null, error: 'kickoff_missing' };
    }

    const timeMatch = /^(\d{1,2}):(\d{2})$/.exec(timeText);
    if (!timeMatch) {
        return { kickoff_at: null, error: 'kickoff_invalid' };
    }

    const hour = Number(timeMatch[1]);
    const minute = Number(timeMatch[2]);

    if (hour > 23 || minute > 59) {
        return { kickoff_at: null, error: 'kickoff_invalid' };
    }

    // Get Europe/London UTC offset using IANA timezone
    const offsetMinutes = londonUtcOffsetMinutes(year, month, day);
    if (offsetMinutes === null) {
        return { kickoff_at: null, error: 'kickoff_timezone_unresolved' };
    }

    // Source time is in Europe/London local → subtract offset to get UTC
    // Create as UTC then subtract the offset
    const localMinutes = hour * 60 + minute;
    const utcMinutes = localMinutes - offsetMinutes;

    // Handle day rollover
    let utcYear = year;
    let utcMonth = month;
    let utcDay = day;
    let utcHour = Math.floor(utcMinutes / 60);
    let utcMinute = utcMinutes % 60;

    if (utcMinutes < 0) {
        // Go back to previous day
        utcHour += 24;
        utcDay -= 1;
        if (utcDay < 1) {
            utcMonth -= 1;
            if (utcMonth < 1) {
                utcMonth = 12;
                utcYear -= 1;
            }
            utcDay = new Date(Date.UTC(utcYear, utcMonth, 0)).getUTCDate();
        }
    } else if (utcHour >= 24) {
        utcHour -= 24;
        utcDay += 1;
        const dim = new Date(Date.UTC(utcYear, utcMonth, 0)).getUTCDate();
        if (utcDay > dim) {
            utcDay = 1;
            utcMonth += 1;
            if (utcMonth > 12) {
                utcMonth = 1;
                utcYear += 1;
            }
        }
    }

    const kickoffAt = `${String(utcYear).padStart(4, '0')}-${String(utcMonth).padStart(2, '0')}-${String(utcDay).padStart(2, '0')}T${String(utcHour).padStart(2, '0')}:${String(utcMinute).padStart(2, '0')}:00Z`;

    return { kickoff_at: kickoffAt, error: null };
}

/**
 * Validate the kickoff_time_interpretation manifest object.
 * Returns { valid: boolean, errors: string[] }
 */
function validateKickoffTimeInterpretation(interpretation) {
    if (!interpretation || typeof interpretation !== 'object') {
        return { valid: true, errors: [] }; // Optional field
    }

    const errors = [];

    if (interpretation.status !== 'derived') {
        errors.push('kickoff_time_interpretation.status must be "derived"');
    }
    if (interpretation.timezone !== 'Europe/London') {
        errors.push('kickoff_time_interpretation.timezone must be "Europe/London"');
    }
    if (interpretation.method !== 'source_local_calendar_time') {
        errors.push('kickoff_time_interpretation.method must be "source_local_calendar_time"');
    }
    if (interpretation.evidence_level !== 'empirical_cross_source') {
        errors.push('kickoff_time_interpretation.evidence_level must be "empirical_cross_source"');
    }
    if (interpretation.official_source_declaration !== false) {
        errors.push('kickoff_time_interpretation.official_source_declaration must be false');
    }
    if (!interpretation.evidence_reference || typeof interpretation.evidence_reference !== 'string' || !interpretation.evidence_reference.trim()) {
        errors.push('kickoff_time_interpretation.evidence_reference must be a non-empty string');
    }

    // Validate allowed_competitions
    if (!Array.isArray(interpretation.allowed_competitions) || interpretation.allowed_competitions.length === 0) {
        errors.push('kickoff_time_interpretation.allowed_competitions must be a non-empty array');
    } else {
        for (const comp of interpretation.allowed_competitions) {
            if (!ALLOWED_COMPETITIONS.includes(comp)) {
                errors.push(`kickoff_time_interpretation.allowed_competitions contains unauthorized competition: ${comp}`);
            }
        }
    }

    // Validate allowed_seasons
    if (!Array.isArray(interpretation.allowed_seasons) || interpretation.allowed_seasons.length === 0) {
        errors.push('kickoff_time_interpretation.allowed_seasons must be a non-empty array');
    } else {
        for (const season of interpretation.allowed_seasons) {
            if (!ALLOWED_SEASONS.includes(season)) {
                errors.push(`kickoff_time_interpretation.allowed_seasons contains unauthorized season: ${season}`);
            }
        }
    }

    // No unknown fields allowed — fail closed
    const knownFields = new Set([
        'status', 'timezone', 'method', 'evidence_level',
        'official_source_declaration', 'evidence_reference',
        'allowed_competitions', 'allowed_seasons',
    ]);
    for (const key of Object.keys(interpretation)) {
        if (!knownFields.has(key)) {
            errors.push(`kickoff_time_interpretation contains unknown field: ${key}`);
        }
    }

    return { valid: errors.length === 0, errors };
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
