'use strict';

// lifecycle: permanent；只接受本地原始文本中明确字段的严格离线 adapter。

const { parseFootballDataDate } = require('../../../scripts/lib/football_data_local_csv_parser');

const ADAPTER_VERSIONS = Object.freeze({
    'football-data-csv': '1.0.0',
    'oddsportal-explicit-envelope-html': '1.0.0',
});

const EXPLICIT_HTML_SCHEMA_VERSION = 'oddsportal-explicit-envelope-html/v1';

const FOOTBALL_DATA_COLUMN_GROUPS = Object.freeze([
    {
        id: 'bet365-unknown',
        bookmaker: 'Bet365',
        bookmaker_source_id: 'B365',
        snapshot_type: 'unknown',
        columns: { home: 'B365H', draw: 'B365D', away: 'B365A' },
    },
    {
        id: 'pinnacle-unknown',
        bookmaker: 'Pinnacle',
        bookmaker_source_id: 'PS',
        snapshot_type: 'unknown',
        columns: { home: 'PSH', draw: 'PSD', away: 'PSA' },
    },
    {
        id: 'bet365-opening-explicit',
        bookmaker: 'Bet365',
        bookmaker_source_id: 'B365',
        snapshot_type: 'opening',
        columns: { home: 'B365_OPEN_HOME', draw: 'B365_OPEN_DRAW', away: 'B365_OPEN_AWAY' },
    },
    {
        id: 'bet365-current-explicit',
        bookmaker: 'Bet365',
        bookmaker_source_id: 'B365',
        snapshot_type: 'current',
        columns: { home: 'B365_CURRENT_HOME', draw: 'B365_CURRENT_DRAW', away: 'B365_CURRENT_AWAY' },
    },
    {
        id: 'bet365-closing-explicit',
        bookmaker: 'Bet365',
        bookmaker_source_id: 'B365',
        snapshot_type: 'closing',
        columns: { home: 'B365_CLOSE_HOME', draw: 'B365_CLOSE_DRAW', away: 'B365_CLOSE_AWAY' },
    },
    {
        id: 'pinnacle-opening-explicit',
        bookmaker: 'Pinnacle',
        bookmaker_source_id: 'PS',
        snapshot_type: 'opening',
        columns: { home: 'PS_OPEN_HOME', draw: 'PS_OPEN_DRAW', away: 'PS_OPEN_AWAY' },
    },
    {
        id: 'pinnacle-current-explicit',
        bookmaker: 'Pinnacle',
        bookmaker_source_id: 'PS',
        snapshot_type: 'current',
        columns: { home: 'PS_CURRENT_HOME', draw: 'PS_CURRENT_DRAW', away: 'PS_CURRENT_AWAY' },
    },
    {
        id: 'pinnacle-closing-explicit',
        bookmaker: 'Pinnacle',
        bookmaker_source_id: 'PS',
        snapshot_type: 'closing',
        columns: { home: 'PS_CLOSE_HOME', draw: 'PS_CLOSE_DRAW', away: 'PS_CLOSE_AWAY' },
    },
]);

function normalizeText(value) {
    return String(value ?? '').trim();
}

function parseDecimal(value) {
    const text = normalizeText(value);
    if (!text) {
        return null;
    }
    const parsed = Number(text);
    return Number.isFinite(parsed) ? parsed : value;
}

function splitCsvLine(line) {
    const values = [];
    let current = '';
    let insideQuotes = false;

    for (let index = 0; index < line.length; index += 1) {
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

    if (insideQuotes) {
        throw new Error('unterminated quoted CSV field');
    }
    values.push(current);
    return values;
}

function canonicalizeCsvHeader(value) {
    return String(value ?? '')
        .normalize('NFKC')
        .trim()
        .toLowerCase();
}

function inspectCsvHeaders(declaredHeaders) {
    const emptyHeaderPositions = [];
    const byCanonicalName = new Map();
    declaredHeaders.forEach((declaredName, index) => {
        const position = index + 1;
        const declaredText = String(declaredName ?? '');
        const canonicalName = canonicalizeCsvHeader(declaredText);
        if (!canonicalName) {
            emptyHeaderPositions.push(position);
            return;
        }
        if (!byCanonicalName.has(canonicalName)) {
            byCanonicalName.set(canonicalName, []);
        }
        byCanonicalName.get(canonicalName).push({ declared_name: declaredText, position });
    });
    const duplicateHeaders = [...byCanonicalName.entries()]
        .filter(([, entries]) => entries.length > 1)
        .map(([canonicalName, entries]) => ({
            canonical_name: canonicalName,
            positions: entries.map(entry => entry.position),
            declared_names: entries.map(entry => entry.declared_name),
        }));
    const reasons = [];
    if (emptyHeaderPositions.length > 0) {
        reasons.push('csv_empty_header');
    }
    if (duplicateHeaders.length > 0) {
        reasons.push('csv_duplicate_header');
    }
    return {
        valid: reasons.length === 0,
        reasons,
        evidence: {
            header_count: declaredHeaders.length,
            empty_header_positions: emptyHeaderPositions,
            duplicate_headers: duplicateHeaders,
        },
    };
}

function parseCsvRows(rawText) {
    const lines = String(rawText || '')
        .replace(/^\uFEFF/, '')
        .replace(/\r\n/g, '\n')
        .replace(/\r/g, '\n')
        .split('\n')
        .filter(line => line.trim() !== '');
    if (lines.length < 2) {
        return { headers: [], rows: [] };
    }

    const declaredHeaders = splitCsvLine(lines[0]);
    const headerValidation = inspectCsvHeaders(declaredHeaders);
    const headers = declaredHeaders.map(normalizeText);
    if (!headerValidation.valid) {
        return { headers, rows: [], header_validation: headerValidation };
    }
    return {
        headers,
        header_validation: headerValidation,
        rows: lines.slice(1).map((line, index) => {
            const values = splitCsvLine(line);
            const row = headers.reduce((result, header, columnIndex) => {
                result[header] = values[columnIndex] ?? '';
                return result;
            }, {});
            return { row, row_number: index + 2 };
        }),
    };
}

function pickFirst(row, fields) {
    for (const field of fields) {
        if (Object.prototype.hasOwnProperty.call(row, field) && normalizeText(row[field])) {
            return normalizeText(row[field]);
        }
    }
    return null;
}

function csvKickoffAt(row, manifest) {
    const explicitKickoff = pickFirst(row, ['KickoffAt', 'kickoff_at']);
    if (explicitKickoff) {
        return { kickoff_at: explicitKickoff, reason: null };
    }

    const date = pickFirst(row, ['Date', 'date']);
    const time = pickFirst(row, ['Time', 'time']);
    if (!date) {
        return { kickoff_at: null, reason: 'kickoff_missing' };
    }
    if (String(manifest.source_timezone || '').toUpperCase() !== 'UTC') {
        return { kickoff_at: null, reason: 'kickoff_timezone_unresolved' };
    }

    const kickoffAt = parseFootballDataDate(date, time || '', { timezone: 'UTC' });
    return kickoffAt ? { kickoff_at: kickoffAt, reason: null } : { kickoff_at: null, reason: 'kickoff_invalid' };
}

function buildCsvIdentity(row, manifest) {
    const kickoff = csvKickoffAt(row, manifest);
    const rawSourceMatchId = pickFirst(row, ['SourceMatchId', 'source_match_id', 'SourceMatchID']);
    const manifestSourceMatchId = normalizeText(manifest.source_match_id) || null;
    const sourceMatchIdConflict =
        rawSourceMatchId && manifestSourceMatchId && rawSourceMatchId !== manifestSourceMatchId;
    return {
        source_match_id: rawSourceMatchId || manifestSourceMatchId,
        competition: pickFirst(row, ['Competition', 'League', 'Div']),
        season: pickFirst(row, ['Season', 'season']),
        kickoff_at: kickoff.kickoff_at,
        home_team: pickFirst(row, ['HomeTeam', 'home_team']),
        away_team: pickFirst(row, ['AwayTeam', 'away_team']),
        identity_reason: kickoff.reason,
        manifest_source_match_id: manifestSourceMatchId,
        raw_source_match_id: rawSourceMatchId,
        source_match_id_conflict: sourceMatchIdConflict,
    };
}

function buildAdapterQuarantine(locator, reasons, evidence = {}) {
    return {
        raw_record_locator: locator,
        reasons: [...new Set(reasons.filter(Boolean))].sort(),
        evidence,
    };
}

function buildCsvObservation(identity, group, selection, decimalOdds, rowNumber) {
    return {
        ...identity,
        bookmaker: group.bookmaker,
        bookmaker_source_id: group.bookmaker_source_id,
        market: '1X2',
        selection,
        line: null,
        decimal_odds: decimalOdds,
        snapshot_type: group.snapshot_type,
        source_observed_at: null,
        raw_record_locator: `csv:row=${rowNumber}:${group.id}:${selection}`,
        extraction_method: `explicit_csv_columns:${group.id}`,
        adapter_quarantine_reasons: identity.identity_reason ? [identity.identity_reason] : [],
    };
}

function adaptFootballDataCsv(rawText, context = {}) {
    const parsed = parseCsvRows(rawText);
    if (parsed.headers.length === 0) {
        return {
            observations: [],
            quarantine: [buildAdapterQuarantine('csv:document', ['csv_header_or_rows_missing'])],
        };
    }
    if (parsed.header_validation && !parsed.header_validation.valid) {
        return {
            observations: [],
            quarantine: [
                buildAdapterQuarantine(
                    'csv:document',
                    parsed.header_validation.reasons,
                    parsed.header_validation.evidence
                ),
            ],
        };
    }

    const observations = [];
    const quarantine = [];
    for (const entry of parsed.rows) {
        const identity = buildCsvIdentity(entry.row, context.manifest || {});
        if (identity.source_match_id_conflict) {
            quarantine.push(
                buildAdapterQuarantine('csv:row=' + String(entry.row_number), ['manifest_source_match_id_conflict'], {
                    manifest_source_match_id: identity.manifest_source_match_id,
                    raw_source_match_id: identity.raw_source_match_id,
                    row_number: entry.row_number,
                })
            );
            continue;
        }
        let hasExplicitBookmakerGroup = false;
        for (const group of FOOTBALL_DATA_COLUMN_GROUPS) {
            const presentSelections = Object.entries(group.columns)
                .filter(([, column]) => Object.prototype.hasOwnProperty.call(entry.row, column))
                .map(([selection]) => selection);
            if (presentSelections.length === 0) {
                continue;
            }

            hasExplicitBookmakerGroup = true;
            if (presentSelections.length !== 3) {
                quarantine.push(
                    buildAdapterQuarantine(
                        `csv:row=${entry.row_number}:${group.id}`,
                        ['incomplete_explicit_1x2_columns'],
                        {
                            present_selections: presentSelections,
                            required_columns: group.columns,
                        }
                    )
                );
                continue;
            }

            for (const selection of ['home', 'draw', 'away']) {
                observations.push(
                    buildCsvObservation(
                        identity,
                        group,
                        selection,
                        parseDecimal(entry.row[group.columns[selection]]),
                        entry.row_number
                    )
                );
            }
        }

        if (!hasExplicitBookmakerGroup) {
            quarantine.push(
                buildAdapterQuarantine(
                    `csv:row=${entry.row_number}`,
                    ['bookmaker_or_market_explicit_columns_missing'],
                    {
                        supported_column_groups: FOOTBALL_DATA_COLUMN_GROUPS.map(group => group.id),
                    }
                )
            );
        }
    }

    return { observations, quarantine };
}

function extractExplicitHtmlEnvelope(rawText) {
    const scripts = String(rawText || '').matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/gi);
    for (const script of scripts) {
        const attributes = script[1];
        if (/data-odds-staging\s*=\s*(["'])explicit\1/i.test(attributes)) {
            return script[2].trim();
        }
    }
    return null;
}

function parseExplicitHtmlPayload(payloadText) {
    try {
        return { payload: JSON.parse(payloadText), quarantine: null };
    } catch {
        return {
            payload: null,
            quarantine: buildAdapterQuarantine('html:explicit-envelope', [
                'explicit_html_evidence_payload_invalid_json',
            ]),
        };
    }
}

function validateExplicitHtmlPayload(payload) {
    if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
        return buildAdapterQuarantine('html:explicit-envelope', ['explicit_html_payload_not_object']);
    }
    if (payload.schema_version !== EXPLICIT_HTML_SCHEMA_VERSION) {
        return buildAdapterQuarantine('html:explicit-envelope', ['explicit_html_schema_version_unsupported'], {
            declared_schema_version: normalizeText(payload.schema_version) || null,
            supported_schema_version: EXPLICIT_HTML_SCHEMA_VERSION,
        });
    }

    if (!Array.isArray(payload.observations)) {
        const reason =
            Array.isArray(payload.triplet) || Array.isArray(payload.odds)
                ? 'generic_triplet_without_explicit_bookmaker'
                : 'explicit_html_observations_missing';
        return buildAdapterQuarantine('html:explicit-envelope', [reason]);
    }

    return null;
}

function resolveHtmlIdentityReasons(match, manifest) {
    const identityReasons = [];
    if (manifest.source_match_id && match.source_match_id && manifest.source_match_id !== match.source_match_id) {
        identityReasons.push('manifest_source_match_id_conflict');
    }
    if (manifest.source_url && match.source_url && manifest.source_url !== match.source_url) {
        identityReasons.push('manifest_source_url_conflict');
    }
    return identityReasons;
}

function mapExplicitHtmlObservations(payload, manifest) {
    const match = payload.match && typeof payload.match === 'object' ? payload.match : {};
    const identityReasons = resolveHtmlIdentityReasons(match, manifest);
    return payload.observations.map((entry, index) => ({
        source_match_id: normalizeText(match.source_match_id) || null,
        competition: normalizeText(match.competition) || null,
        season: normalizeText(match.season) || null,
        kickoff_at: normalizeText(match.kickoff_at) || null,
        home_team: normalizeText(match.home_team) || null,
        away_team: normalizeText(match.away_team) || null,
        bookmaker: normalizeText(entry?.bookmaker) || null,
        bookmaker_source_id: normalizeText(entry?.bookmaker_source_id) || null,
        market: normalizeText(entry?.market) || null,
        selection: normalizeText(entry?.selection) || null,
        line: entry?.line ?? null,
        decimal_odds: entry?.decimal_odds ?? null,
        snapshot_type: normalizeText(entry?.snapshot_type) || 'unknown',
        source_observed_at: normalizeText(entry?.source_observed_at) || null,
        raw_record_locator: `html:explicit-envelope:observations[${index}]`,
        extraction_method: 'explicit_html_data_odds_staging_envelope',
        adapter_quarantine_reasons: identityReasons,
    }));
}

function adaptOddsPortalExplicitEnvelopeHtml(rawText, context = {}) {
    const payloadText = extractExplicitHtmlEnvelope(rawText);
    if (!payloadText) {
        return {
            observations: [],
            quarantine: [buildAdapterQuarantine('html:document', ['explicit_html_evidence_payload_missing'])],
        };
    }

    const parsedPayload = parseExplicitHtmlPayload(payloadText);
    if (parsedPayload.quarantine) {
        return { observations: [], quarantine: [parsedPayload.quarantine] };
    }

    const payloadQuarantine = validateExplicitHtmlPayload(parsedPayload.payload);
    if (payloadQuarantine) {
        return { observations: [], quarantine: [payloadQuarantine] };
    }

    return {
        observations: mapExplicitHtmlObservations(parsedPayload.payload, context.manifest || {}),
        quarantine: [],
    };
}

function getAdapter(adapterName) {
    if (adapterName === 'football-data-csv') {
        return adaptFootballDataCsv;
    }
    if (adapterName === 'oddsportal-explicit-envelope-html') {
        return adaptOddsPortalExplicitEnvelopeHtml;
    }
    return null;
}

module.exports = {
    ADAPTER_VERSIONS,
    EXPLICIT_HTML_SCHEMA_VERSION,
    FOOTBALL_DATA_COLUMN_GROUPS,
    adaptFootballDataCsv,
    adaptOddsPortalExplicitEnvelopeHtml,
    getAdapter,
};
