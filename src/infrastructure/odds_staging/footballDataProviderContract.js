'use strict';

// lifecycle: permanent；M3-R2 Football-Data.co.uk official provider semantic contract。
//
// 来源：provider 官方公开文档（Level A primary provider documentation），
// retrieved 2026-08-09（HTTPS GET，官方域，无登录/无 POST）。完整取证记录在 repo 外
// evidence 目录（provider-evidence.md / provider-evidence-hashes.json / effective-scope.md）。
// 本模块只承载机器可读的已证明语义 + provenance metadata；
// runtime 绝不联网 —— official_source_urls 只是 provenance 记录。

const FOOTBALL_DATA_PROVIDER_CONTRACT = Object.freeze({
    contract_id: 'football-data-provider-contract/v1',
    provider_id: 'football-data.co.uk',
    evidence_type: 'primary_provider_documentation',
    evidence_checked_at: '2026-08-09',
    official_source_urls: Object.freeze([
        'https://www.football-data.co.uk/downloadm.php',
        'https://www.football-data.co.uk/data.php',
        'https://www.football-data.co.uk/matches.php',
        'https://www.football-data.co.uk/notes.txt',
    ]),
    // "Since 2019/20 I have collected two sets of odds."（downloadm.php）
    effective_from_season: '2019/20',
    // "The first set is collected after market opening at times specified on my
    // fixtures page." —— provider 从未把第一组称为 opening odds；不得等价为精确开盘价。
    first_collection_semantics: 'first_collection_after_market_open',
    first_set_is_exact_opening_price: false,
    // "The second set are the closing odds ('C' included the data column headings)."
    // notes.txt: "as below but with an additional 'C' character following the bookmaker
    // abbreviation/Max/Avg (e.g. B365CH = closing Bet365 home win odds)。"
    closing_series_marker: 'C',
    closing_series_semantics: 'closing',
    closing_series_is_exact_closing_tick: false,
    // 没有任何 per-row 观察/采集时间戳字段；下列规则只可作 provider_collection_schedule，
    // 不可写成 observation timestamp（source_observed_at / captured_at 保持 null）。
    exact_observation_timestamp_available: false,
    exact_capture_timestamp_available: false,
    provider_collection_schedule: Object.freeze({
        weekend_fixtures: {
            day: 'Friday',
            qualifier: 'generally not later than',
            latest_uk_time: '17:00',
            timezone: 'British Standard Time',
        },
        midweek_fixtures: {
            day: 'Tuesday',
            qualifier: 'not later than',
            latest_uk_time: '13:00',
            timezone: 'British Standard Time',
        },
        note: 'collection schedule rule only; never a per-row observation timestamp',
    }),
    // "Since 23/07/2025 Pinnacle's public API ... has become unreliable ..."
    // Canonical seasons（2022/23–2024/25，最后比赛 2025-05-25）全部早于该日期。
    pinnacle_warning: Object.freeze({
        effective_from: '2025-07-23',
        applicable_to_canonical_seasons: false,
    }),
    // C series 允许的 snapshot_type（现有 schema ALLOWED_SNAPSHOT_TYPES 已含 'closing'）。
    closing_snapshot_type: 'closing',
    // 允许的 provider_collection_phase 值。
    collection_phase_values: Object.freeze(['first_collection_after_market_open', 'closing']),
});

const FIRST_COLLECTION_PHASE = 'first_collection_after_market_open';
const CLOSING_PHASE = 'closing';

/**
 * 判定 season 是否落在 provider contract 生效范围内。
 * 支持 '2022/2023'（identity 派生格式，adapter normalizeSeasonFormat 之后）与
 * '22/23'（短格式）。raw Season 列的紧凑 '2223' 格式在 adapter 中保持原样、不会到达
 * 这里（Codex R2 F-03）：无法解析 → fail closed，不应用 overlay —— 宁可不打 closing
 * 标签，也不把未证实语义写进观测。
 * effective_from '2019/20' → 起始年份 2019。
 */
function parseSeasonStartYear(season) {
    const text = String(season || '').trim();
    // 支持 '2019/20'（contract 自身格式）、'2022/2023'、'22/23'。
    const match = /^(\d{2,4})\/(\d{2,4})$/.exec(text);
    if (!match) {
        return null;
    }
    if (match[1].length === 4) {
        return Number(match[1]);
    }
    return Number(`20${match[1]}`);
}

function isSeasonWithinProviderContract(season) {
    const seasonYear = parseSeasonStartYear(season);
    const effectiveYear = parseSeasonStartYear(FOOTBALL_DATA_PROVIDER_CONTRACT.effective_from_season);
    if (seasonYear === null || effectiveYear === null) {
        return false;
    }
    return seasonYear >= effectiveYear;
}

/**
 * 按 provider contract 对 rebuild column group 应用语义 overlay。
 * 只接受来自 FOOTBALL_DATA_COLUMN_GROUPS 的 group 形态；generic/未知源
 * （applicable=false）一律返回 null → 保持 snapshot_type=unknown 且无 phase。
 * 返回 { snapshot_type, provider_collection_phase } 或 null。
 */
function applyProviderContractToGroup(group, options = {}) {
    const applicable = options.applicable === true;
    const seasonWithinScope = isSeasonWithinProviderContract(options.season);
    if (!applicable || !seasonWithinScope) {
        return null;
    }
    if (!group || typeof group !== 'object' || typeof group.id !== 'string') {
        return null;
    }
    if (group.id.endsWith('-c-series-unknown')) {
        return {
            snapshot_type: FOOTBALL_DATA_PROVIDER_CONTRACT.closing_snapshot_type,
            provider_collection_phase: CLOSING_PHASE,
        };
    }
    if (group.id.endsWith('-unknown') || group.id.endsWith('-snake-unknown')) {
        // 第一组：provider 定义为 market opening 之后按 fixtures 页时间采集的第一组；
        // 不是 opening price。snapshot_type 保持 unknown（现有 schema 无法准确表达
        // first-collection 语义，mandate §22），provider_collection_phase 精确表达。
        return {
            snapshot_type: 'unknown',
            provider_collection_phase: FIRST_COLLECTION_PHASE,
        };
    }
    return null;
}

module.exports = {
    CLOSING_PHASE,
    FIRST_COLLECTION_PHASE,
    FOOTBALL_DATA_PROVIDER_CONTRACT,
    applyProviderContractToGroup,
    isSeasonWithinProviderContract,
    parseSeasonStartYear,
};
