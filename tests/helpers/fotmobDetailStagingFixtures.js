'use strict';

// lifecycle: permanent
// Synthetic fixture builders for the FotMob detail staging converter /
// validator tests. Every fixture payload is RE-SIGNED with the real pipeline
// hashing helpers (computeStableCapturePayloadSha256,
// computeCaptureManifestSelfHash) so the fixtures are legal capture
// documents — never mocked hash stubs (ERRATA_4).

const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const zlib = require('node:zlib');

const {
    computeStableCapturePayloadSha256,
    computeCaptureManifestSelfHash,
    canonicalJsonHash,
} = require('../../src/infrastructure/fotmob/FotMobDetailCaptureContract');

const COMPETITION = 'Premier League';
const LEAGUE_ID = '47';
const SEASON = '2022/2023';
const KICKOFF = '2022-10-08T14:00:00Z';
const PARSER_VERSION = 'V174.0.0';
const PARSED_CONTRACT = 'fotmob-match-detail-parsed/v1';
const COLLECTOR_REVISION = 'a3df6d0a81cdaa8414ef30d257f5698cd002d12c';

function sha256Text(text) {
    return crypto.createHash('sha256').update(String(text), 'utf8').digest('hex');
}

/**
 * Build a legal capture payload. `overrides.normalized` replaces the whole
 * normalized object; `overrides.observed` / `overrides.expected` replace
 * those identity objects. The stable payload hash is always recomputed by
 * the real pipeline function.
 */
function buildPayload(overrides = {}) {
    const sourceMatchId = String(overrides.source_match_id ?? '3901023');
    const candidateId = String(overrides.candidate_id ?? `47_20222023_${sourceMatchId}`);
    const expected = {
        home_team: 'AFC Bournemouth',
        away_team: 'Leicester City',
        kickoff_at: KICKOFF,
        ...(overrides.expected || {}),
    };
    const observed = {
        home_team: 'AFC Bournemouth',
        away_team: 'Leicester City',
        observed_match_id: sourceMatchId,
        observed_match_id_source: 'general.matchId',
        observed_match_id_conflict: false,
        observed_match_id_is_response_derived: true,
        observed_home_team_id: 10204,
        observed_home_team_id_source: 'general.homeTeam.id',
        observed_away_team_id: 10261,
        observed_away_team_id_source: 'general.awayTeam.id',
        ...(overrides.observed || {}),
    };
    const payload = {
        schema_version: 'fotmob-match-detail-capture-payload/v1',
        source_provider: 'FotMob',
        source_match_id: sourceMatchId,
        candidate_id: candidateId,
        competition: COMPETITION,
        league_id: LEAGUE_ID,
        season: SEASON,
        expected_identity: expected,
        observed_identity: observed,
        normalized: overrides.normalized !== undefined ? overrides.normalized : buildNormalized(sourceMatchId),
        parser_component: 'NextDataParser+FotMobRawParser',
        parser_version: PARSER_VERSION,
        parser_output_contract_version: PARSED_CONTRACT,
    };
    payload.stable_payload_sha256 = computeStableCapturePayloadSha256(payload);
    return payload;
}

function buildNormalized(sourceMatchId = '3901023') {
    return {
        match_external_id: String(sourceMatchId),
        home_team: {
            id: 10204,
            name: 'AFC Bournemouth',
            shortName: 'BOU',
            score: 2,
            formation: '4-2-3-1',
        },
        away_team: {
            id: 10261,
            name: 'Leicester City',
            shortName: 'LEI',
            score: 1,
            formation: '4-1-4-1',
        },
        events: [
            {
                id: 9434327,
                minute: 10,
                homeScore: 0,
                awayScore: 0,
                event_kind: 'real_event',
                assistPlayerId: null,
                card: null,
                outcome: null,
                playerName: 'Player A',
                synthetic_event_key: 'synthetic:1',
                source_has_native_id: true,
            },
            {
                id: 9434979,
                minute: 40,
                homeScore: 0,
                awayScore: 1,
                event_kind: 'real_event',
                assistPlayerId: null,
                card: 'Yellow',
                outcome: null,
                playerName: 'Player B',
                synthetic_event_key: 'synthetic:2',
                source_has_native_id: true,
            },
        ],
        lineup: {
            home: {
                coach: {
                    id: 24393,
                    firstName: 'Gary',
                    lastName: "O'Neil",
                    name: "Gary O'Neil",
                    countryCode: 'ENG',
                    countryName: 'England',
                    age: 39,
                    isCoach: true,
                    primaryTeamName: 'AFC Bournemouth',
                },
                starters: [
                    {
                        id: 176186,
                        name: 'Neto',
                        shirtNumber: '13',
                        position: null,
                        rating: null,
                    },
                    {
                        id: 254472,
                        name: 'Danny Ward',
                        shirtNumber: '1',
                        position: null,
                        rating: null,
                    },
                ],
                subs: [
                    {
                        id: 436036,
                        name: 'Daniel Amartey',
                        shirtNumber: '18',
                        position: null,
                        rating: null,
                    },
                ],
            },
            away: {
                coach: {
                    id: 160770,
                    firstName: 'Brendan',
                    lastName: 'Rodgers',
                    name: 'Brendan Rodgers',
                    countryCode: 'NIR',
                    countryName: 'Northern Ireland',
                    age: 49,
                    isCoach: true,
                    primaryTeamName: 'Leicester City',
                },
                starters: [
                    {
                        id: 139671,
                        name: 'Marc Albrighton',
                        shirtNumber: '11',
                        position: null,
                        rating: null,
                    },
                ],
                subs: [],
            },
        },
        player_stats: {
            1171140: {
                id: 1171140,
                name: 'Jaidon Anthony',
                shirtNumber: '32',
                isGoalkeeper: false,
                teamId: 10204,
                teamName: 'AFC Bournemouth',
                optaId: '444180',
                positionId: 38,
                usualPosition: 'Forward',
                shotmap: [],
                funFacts: ['first goal'],
            },
            176186: {
                id: 176186,
                name: 'Neto',
                shirtNumber: '13',
                isGoalkeeper: true,
                teamId: 10204,
                teamName: 'AFC Bournemouth',
                optaId: '69752',
                positionId: 11,
                usualPosition: 'Goalkeeper',
                shotmap: [],
                funFacts: null,
            },
        },
        shotmap: {
            shots: [
                {
                    id: 1,
                    playerId: 1171140,
                    teamId: 10204,
                    min: 10,
                    minAdded: 0,
                    period: 'FirstHalf',
                    x: 80.5,
                    y: 40.2,
                    blockedX: null,
                    blockedY: null,
                    goalCrossedY: 0,
                    goalCrossedZ: 0,
                    onGoalShot: null,
                    expectedGoals: 0.09059995412826538,
                    expectedGoalsOnTarget: null,
                    isBlocked: false,
                    isOnTarget: true,
                    isOwnGoal: false,
                    isSavedOffLine: false,
                    shotType: 'RightFoot',
                    eventType: 'AttemptSaved',
                    situation: 'RegularPlay',
                    firstName: 'Harvey',
                    lastName: 'Jones',
                    fullName: 'Harvey Jones',
                    playerName: 'Harvey Jones',
                    teamColor: 'RED',
                },
            ],
        },
        stats: [
            { key: 'top_stats', homeValue: null, awayValue: null, period: 'All' },
            { key: 'shots', homeValue: 15, awayValue: 9, period: 'All' },
            { key: 'shots', homeValue: 10, awayValue: 5, period: 'FirstHalf' },
            { key: 'shots', homeValue: 5, awayValue: 4, period: 'SecondHalf' },
            { key: 'possession', homeValue: 52.3, awayValue: 47.7, period: 'All' },
            {
                key: 'possession',
                homeValue: 55.0,
                awayValue: 45.0,
                period: 'FirstHalf',
            },
            {
                key: 'possession',
                homeValue: 49.0,
                awayValue: 51.0,
                period: 'SecondHalf',
            },
        ],
    };
}

/**
 * Build a legal capture manifest bound to a payload document. All hashes are
 * recomputed by the real pipeline helpers.
 */
/* eslint-disable-next-line complexity */
function buildManifest(payload, overrides = {}) {
    const expected = payload.expected_identity || {};
    const observed = payload.observed_identity || {};
    const candidateIdentity = {
        source_match_id: String(payload.source_match_id),
        competition: String(payload.competition),
        season: String(payload.season),
        home_team: String(expected.home_team ?? ''),
        away_team: String(expected.away_team ?? ''),
        kickoff_at: String(expected.kickoff_at ?? ''),
    };
    const normalized = payload.normalized || {};
    const hasLineup = normalized.lineup !== undefined && normalized.lineup !== null;
    const hasShotmap = normalized.shotmap !== undefined && normalized.shotmap !== null;
    const hasStats = normalized.stats !== undefined && normalized.stats !== null;
    const manifest = {
        schema_version: 'fotmob-match-detail-capture-manifest/v1',
        source_provider: 'FotMob',
        source_kind: 'match_detail_page',
        candidate_id: String(payload.candidate_id),
        source_match_id: String(payload.source_match_id),
        competition: String(payload.competition),
        league_id: String(payload.league_id),
        season: String(payload.season),
        home_team: String(expected.home_team ?? ''),
        away_team: String(expected.away_team ?? ''),
        kickoff_at: String(expected.kickoff_at ?? ''),
        candidate_identity_sha256: canonicalJsonHash(candidateIdentity),
        source_plan_sha256: 'bd01003b75fd3f9aebf60554235948976f8beca07dd28639d04c37d01c69af3f',
        source_artifact_sha256: 'f99d36d227cbcc4d2baa0750e5ea2c63afe05d998bdee0b5af237b278de0c6a7',
        capture_run_id: 'fotmob-ten-match-risk-accepted-b6f9f385-b75c9b9df4fb-20260804T053204Z',
        authorization_id: 'OWNER_RISK_ACCEPTED_TEN_MATCH_b75c9b9df4fb_20260804T053204Z',
        request_ordinal: 1,
        request_budget: 10,
        delay_ms: 60000,
        request_method: 'GET',
        request_url: `https://www.fotmob.com/match/${payload.source_match_id}`,
        request_attempted_at: '2026-08-04T05:34:59.650Z',
        response_received_at: '2026-08-04T05:35:01.537Z',
        http_status: 200,
        content_type: 'text/html; charset=utf-8',
        response_body_byte_size: 1823042,
        response_body_sha256: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        observed_match_id: String(observed.observed_match_id ?? ''),
        observed_match_id_source: String(observed.observed_match_id_source ?? 'general.matchId'),
        observed_match_id_match: true,
        observed_match_id_conflict: observed.observed_match_id_conflict === true,
        observed_match_id_is_response_derived: observed.observed_match_id_is_response_derived === true,
        hydration_parse_ok: true,
        transformed_api_format: true,
        looks_like_valid_match_detail: true,
        has_stats: hasStats,
        has_lineup: hasLineup,
        has_shotmap: hasShotmap,
        stable_raw_payload_sha256: 'c4a1f5d8c3b9a2f7d6e5b4a3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3',
        stable_payload_sha256: String(payload.stable_payload_sha256),
        payload_file_sha256: overrides.payload_file_sha256 || sha256Text(JSON.stringify(payload, null, 2) + '\n'),
        payload_file_relative_path: `pairs/1-${payload.source_match_id}.payload.json`,
        parser_component: 'NextDataParser+FotMobRawParser',
        parser_version: String(payload.parser_version),
        collector_component: 'FotMobDetailCapturePipeline',
        collector_code_revision: COLLECTOR_REVISION,
        network_authorization_mode: 'explicit_network_authorization',
        ...(overrides.manifest || {}),
    };
    manifest.capture_manifest_sha256 = computeCaptureManifestSelfHash(manifest);
    return manifest;
}

/**
 * Build a full legal pair with physical bytes.
 * @returns {{ payload, manifest, payloadBytes }}
 */
function buildPair(overrides = {}) {
    const payload = buildPayload(overrides);
    const payloadBytes = Buffer.from(JSON.stringify(payload, null, 2) + '\n', 'utf8');
    const manifest = buildManifest(payload, overrides);
    return { payload, manifest, payloadBytes };
}

/**
 * Build a legal source index document. Each binding is
 * { package: { sha256, path, receipt } } — the PR1817-remediated schema
 * requires the archive path, the declared SHA-256 AND the verified package
 * receipt path for every binding.
 */
function buildSourceIndex(entries, archiveBindings = {}) {
    return {
        schema_version: 'fotmob-detail-source-index/v1',
        source_provider: 'FotMob',
        archive_bindings: archiveBindings,
        entries,
    };
}

/**
 * Build a full legal source index from one fixture archive + its receipt.
 *
 * @param {Array<{sourceMatchId: string, pair: object}>} pairs
 * @param {object} archiveInfo - from writeFixtureArchive
 * @param {object} options - { packageId, receiptPath, extraEntry }
 * @returns {object} source index document
 */
function buildSourceIndexFromArchive(pairs, archiveInfo, options = {}) {
    const packageId = options.packageId || archiveInfo.packageId || 'ten-match';
    const entries = pairs.map(({ sourceMatchId }) =>
        sourceIndexEntry(
            sourceMatchId,
            archiveInfo.payloadFiles[sourceMatchId],
            archiveInfo.manifestFiles[sourceMatchId],
            {
                package: packageId,
                // R4-P1-1: a multi-pair archive (one package, many pairs)
                // needs each entry to select ITS archive members — the
                // receipt declares only the first pair's members globally.
                ...(archiveInfo.payloadMembers && archiveInfo.payloadMembers[sourceMatchId]
                    ? { payload_member: archiveInfo.payloadMembers[sourceMatchId] }
                    : {}),
                ...(archiveInfo.manifestMembers && archiveInfo.manifestMembers[sourceMatchId]
                    ? { manifest_member: archiveInfo.manifestMembers[sourceMatchId] }
                    : {}),
                ...(options.extraEntry || {}),
            }
        )
    );
    return buildSourceIndex(entries, {
        [packageId]: {
            sha256: archiveInfo.archiveSha256,
            path: archiveInfo.archivePath,
            receipt: options.receiptPath,
        },
    });
}

function sourceIndexEntry(sourceMatchId, payloadFile, manifestFile, extra = {}) {
    const entry = {
        source_match_id: String(sourceMatchId),
        payload_file: payloadFile,
        manifest_file: manifestFile,
        package: extra.package || 'ten-match',
        ...extra,
    };
    // P2-2 (Codex review 4863122944): payload_file_sha256 and
    // manifest_file_sha256 are REQUIRED by the source index contract and are
    // verified live at build time; fixtures compute them from the real files
    // (unless a test overrides them via extra).
    if (entry.payload_file_sha256 === undefined && payloadFile && fs.existsSync(payloadFile)) {
        entry.payload_file_sha256 = sha256Text(fs.readFileSync(payloadFile, 'utf8'));
    }
    if (entry.manifest_file_sha256 === undefined && manifestFile && fs.existsSync(manifestFile)) {
        entry.manifest_file_sha256 = sha256Text(fs.readFileSync(manifestFile, 'utf8'));
    }
    return entry;
}

// ─────────────────────────────────────────────────────────────
// Minimal tar writer + fixture archives (PR1817 remediation,
// FINDING_3): unit tests build REAL gzipped tar archives so the
// VERIFIED_PACKAGE_RECEIPT path is exercised against real bytes —
// no mocked archive hashes anywhere.
// ─────────────────────────────────────────────────────────────

function tarHeader(name, size) {
    const buf = Buffer.alloc(512);
    buf.write(String(name), 0, 'utf8');
    buf.write('0000644\0', 100, 'utf8'); // mode
    buf.write('0000000\0', 108, 'utf8'); // uid
    buf.write('0000000\0', 116, 'utf8'); // gid
    // NOTE: toString(8) must be called on the NUMBER — String.prototype
    // toString ignores a radix argument and would write decimal digits.
    buf.write(Number(size).toString(8).padStart(11, '0') + '\0', 124, 'utf8'); // size
    buf.write('00000000000\0', 136, 'utf8'); // mtime
    buf.write('0', 156, 'utf8'); // typeflag: regular file
    buf.write('ustar\0', 257, 'utf8'); // magic
    buf.write('00', 263, 'utf8'); // version
    let sum = 0;
    for (let i = 0; i < 512; i += 1) {
        sum += i >= 148 && i < 156 ? 32 : buf[i];
    }
    buf.write(sum.toString(8).padStart(6, '0') + '\0 ', 148, 'utf8');
    return buf;
}

/**
 * Build a gzipped tar archive from {name, content} members (test-only;
 * minimal ustar writer — no PAX/GNU headers needed for fixtures).
 *
 * @param {Array<{name: string, content: string|Buffer}>} members
 * @returns {Buffer} gzipped tar bytes
 */
function createTarGz(members) {
    const blocks = [];
    for (const member of members) {
        const content = Buffer.isBuffer(member.content) ? member.content : Buffer.from(member.content, 'utf8');
        blocks.push(tarHeader(member.name, content.length));
        blocks.push(content);
        const remainder = content.length % 512;
        if (remainder > 0) blocks.push(Buffer.alloc(512 - remainder));
    }
    blocks.push(Buffer.alloc(1024)); // end-of-archive: two zero blocks
    return zlib.gzipSync(Buffer.concat(blocks));
}

function sha256Hex(buffer) {
    return crypto.createHash('sha256').update(buffer).digest('hex');
}

/**
 * Write a real fixture archive (gzipped tar) containing one pair as
 * `pairs/1-<id>.payload.json` + `pairs/1-<id>.manifest.json`, plus the
 * extracted payload/manifest files next to it. Returns everything a source
 * index binding and a package receipt need.
 *
 * @param {string} dir - repository-external temp dir
 * @param {Array<{sourceMatchId: string, pair: object}>} pairs
 * @param {object} options - { packageId }
 * @returns {object} { archivePath, archiveSha256, payloadMember,
 *                     manifestMember, payloadFile, manifestFile,
 *                     payloadFiles: {}, manifestFiles: {} }
 */
function writeFixtureArchive(dir, pairs, options = {}) {
    const packageId = options.packageId || 'ten-match';
    const payloadFiles = {};
    const manifestFiles = {};
    const payloadMembers = {};
    const manifestMembers = {};
    const members = [];
    for (const { sourceMatchId, pair } of pairs) {
        const payloadFile = path.join(dir, `${sourceMatchId}.payload.json`);
        const manifestFile = path.join(dir, `${sourceMatchId}.manifest.json`);
        fs.writeFileSync(payloadFile, pair.payloadBytes);
        fs.writeFileSync(manifestFile, JSON.stringify(pair.manifest, null, 2) + '\n');
        payloadFiles[sourceMatchId] = payloadFile;
        manifestFiles[sourceMatchId] = manifestFile;
        const payloadMember = `pairs/1-${sourceMatchId}.payload.json`;
        const manifestMember = `pairs/1-${sourceMatchId}.manifest.json`;
        // R4-P1-1: per-match member names — a multi-pair archive needs each
        // source-index entry to select ITS members, not the receipt's global
        // (first-pair) selectors.
        payloadMembers[sourceMatchId] = payloadMember;
        manifestMembers[sourceMatchId] = manifestMember;
        members.push({ name: payloadMember, content: pair.payloadBytes });
        members.push({
            name: manifestMember,
            content: JSON.stringify(pair.manifest, null, 2) + '\n',
        });
    }
    const archivePath = path.join(dir, `fixture-${packageId}.tar.gz`);
    const archiveBytes = createTarGz(members);
    fs.writeFileSync(archivePath, archiveBytes);
    const first = pairs[0];
    return {
        archivePath,
        archiveSha256: sha256Hex(archiveBytes),
        payloadMember: `pairs/1-${first.sourceMatchId}.payload.json`,
        manifestMember: `pairs/1-${first.sourceMatchId}.manifest.json`,
        payloadFile: payloadFiles[first.sourceMatchId],
        manifestFile: manifestFiles[first.sourceMatchId],
        payloadFiles,
        manifestFiles,
        payloadMembers,
        manifestMembers,
    };
}

/**
 * Build a package receipt for a fixture archive via the real
 * source-verification module and write it to disk.
 *
 * @param {object} args - { archivePath, archiveSha256, packageId,
 *                          payloadMember, manifestMember, receiptPath }
 * @returns {object} receipt document
 */
function writeFixtureReceipt(args) {
    const {
        verifyArchive,
        inspectArchive,
        buildPackageReceipt,
    } = require('../../src/infrastructure/fotmob/FotMobDetailStagingSourceVerification');
    verifyArchive(args.archivePath, args.archiveSha256);
    const inspected = inspectArchive(args.archivePath);
    const receipt = buildPackageReceipt({
        packageId: args.packageId,
        archivePath: args.archivePath,
        archiveSha256: args.archiveSha256,
        members: inspected.members,
        payloadMember: args.payloadMember,
        manifestMember: args.manifestMember,
    });
    fs.writeFileSync(args.receiptPath, JSON.stringify(receipt, null, 2) + '\n');
    return receipt;
}

module.exports = {
    COMPETITION,
    LEAGUE_ID,
    SEASON,
    KICKOFF,
    PARSER_VERSION,
    PARSED_CONTRACT,
    COLLECTOR_REVISION,
    sha256Text,
    buildPayload,
    buildNormalized,
    buildManifest,
    buildPair,
    buildSourceIndex,
    buildSourceIndexFromArchive,
    sourceIndexEntry,
    tarHeader,
    createTarGz,
    sha256Hex,
    writeFixtureArchive,
    writeFixtureReceipt,
};
