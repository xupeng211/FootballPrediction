/**
 * FotMobRawParser — fotmob_live_v1 raw payload 纯函数解析器
 * ============================================================
 *
 * 将 FotMob raw API payload 解析为 contract 定义的稳定中间结构。
 * 纯函数：无网络、无 DB、无文件 I/O、无副作用。
 *
 * Contract: docs/data/FOTMOB_RAW_PARSER_CONTRACT.md
 * Data version: fotmob_live_v1
 *
 * lifecycle: permanent
 * @module parsers/fotmob/FotMobRawParser
 */

'use strict';

// ---------------------------------------------------------------------------
// 辅助函数
// ---------------------------------------------------------------------------

/**
 * 返回 values 中第一个非 null/undefined/空字符串的值。
 * 所有值都无效时返回 fallback（默认 null）。
 *
 * 复用现有 MatchParser 的 firstValue 语义。
 */
function firstValue(values, fallback = null) {
  return values.find(
    (value) => value !== undefined && value !== null && value !== ''
  ) ?? fallback;
}

/**
 * 安全取深层属性，任意中间步骤缺失返回 undefined。
 */
function safeGet(obj, ...path) {
  let current = obj;
  for (const key of path) {
    if (current === null || current === undefined || typeof current !== 'object') {
      return undefined;
    }
    current = current[key];
  }
  return current;
}

/**
 * 确保返回值是数组；null/undefined/非数组返回 []。
 */
function ensureArray(value) {
  return Array.isArray(value) ? value : [];
}

/**
 * 确保返回值是普通对象；null/undefined/非对象返回 {}。
 */
function ensureObject(value) {
  if (value === null || value === undefined || typeof value !== 'object' || Array.isArray(value)) {
    return {};
  }
  return value;
}

// ---------------------------------------------------------------------------
// 各段提取函数（纯函数，不抛异常）
// ---------------------------------------------------------------------------

/**
 * 提取并校验 match identity（§6 match 段）。
 */
function extractMatch(payload, externalId) {
  const general = ensureObject(payload.general);
  const header = ensureObject(payload.header);

  const matchIdRaw = firstValue([
    payload.matchId,
    general.matchId,
  ]);

  // contract §7: matchId 必须存在且可转为数字
  const matchIdNum = Number(matchIdRaw);
  if (matchIdRaw === null || matchIdRaw === undefined || !Number.isFinite(matchIdNum)) {
    return { ok: false, error: 'INVALID_MATCH_ID' };
  }

  return {
    ok: true,
    data: {
      matchId: String(matchIdNum),
      externalId: String(externalId ?? matchIdNum),
      leagueId: String(firstValue([general.leagueId], '')),
      leagueName: String(firstValue([general.leagueName], '')),
      matchRound: firstValue([general.matchRound, general.leagueRoundName], null),
      matchTimeUTC: firstValue([general.matchTimeUTC], null),
      started: Boolean(firstValue([general.started, safeGet(header, 'status', 'started')], false)),
      finished: Boolean(firstValue([general.finished, safeGet(header, 'status', 'finished')], false)),
      cancelled: Boolean(safeGet(header, 'status', 'cancelled') ?? false),
    },
  };
}

/**
 * 提取球队信息（§6 homeTeam / awayTeam 段）。
 */
function extractTeams(payload) {
  const general = ensureObject(payload.general);
  const header = ensureObject(payload.header);
  const lineup = ensureObject(safeGet(payload, 'content', 'lineup'));

  function buildTeam(side) {
    const teamKey = side === 'home' ? 'homeTeam' : 'awayTeam';
    const lineupKey = side === 'home' ? 'homeTeam' : 'awayTeam';
    const headerIdx = side === 'home' ? 0 : 1;

    const fromGeneral = ensureObject(general[teamKey]);
    const fromHeaderTeams = Array.isArray(safeGet(header, 'teams'))
      ? (header.teams[headerIdx] || {})
      : {};
    const fromLineup = ensureObject(lineup[lineupKey]);

    const id = firstValue([fromGeneral.id, fromHeaderTeams.id, fromLineup.id]);
    const name = firstValue([fromGeneral.name, fromHeaderTeams.name, fromLineup.name, fromGeneral.shortName]);
    const score = firstValue([fromHeaderTeams.score, fromGeneral.score], null);
    const formation = firstValue([fromLineup.formation], null);

    // score 可能是数字或字符串，统一为数字或 null
    let scoreNum = null;
    if (score !== null && score !== undefined) {
      const parsed = Number(score);
      scoreNum = Number.isFinite(parsed) ? parsed : null;
    }

    return {
      id: id !== null && id !== undefined ? Number(id) : null,
      name: name !== null && name !== undefined ? String(name) : null,
      score: scoreNum,
      formation: formation !== null && formation !== undefined ? String(formation) : null,
    };
  }

  return {
    homeTeam: buildTeam('home'),
    awayTeam: buildTeam('away'),
  };
}

/**
 * 从 sub-stats 数组中提取 homeValue / awayValue。
 * contract §3.2.4: stats 数组含 { key: "homeValue", value: N } 和 { key: "awayValue", value: N }
 */
function extractHomeAwayValues(subStats) {
  let homeValue = null;
  let awayValue = null;

  for (const sub of subStats) {
    if (!sub || typeof sub !== 'object') continue;
    const v = Number(sub.value);
    if (sub.key === 'homeValue' && Number.isFinite(v)) {
      homeValue = v;
    } else if (sub.key === 'awayValue' && Number.isFinite(v)) {
      awayValue = v;
    }
  }

  return { homeValue, awayValue };
}

/**
 * 提取 stats — Periods-aware 遍历 (§3, §6 stats 段)。
 *
 * 遍历 content.stats.Periods.{All,FirstHalf,SecondHalf}.stats[]
 * 将每条 stat 拍平为 { period, key, homeValue, awayValue }。
 */
function extractStats(payload) {
  const statsContainer = safeGet(payload, 'content', 'stats');
  if (!statsContainer || typeof statsContainer !== 'object') {
    return [];
  }

  const periods = statsContainer.Periods;
  if (!periods || typeof periods !== 'object') {
    return [];
  }

  const result = [];
  const PERIOD_KEYS = ['All', 'FirstHalf', 'SecondHalf'];

  for (const periodKey of PERIOD_KEYS) {
    const period = periods[periodKey];
    if (!period || typeof period !== 'object') {
      continue;
    }

    const statsArray = ensureArray(period.stats);
    for (const statEntry of statsArray) {
      if (!statEntry || typeof statEntry !== 'object') {
        continue;
      }

      const key = statEntry.key || statEntry.title || statEntry.name || null;
      if (key === null) {
        continue;
      }

      const { homeValue, awayValue } = extractHomeAwayValues(ensureArray(statEntry.stats));

      result.push({
        period: periodKey,
        key: String(key),
        homeValue,
        awayValue,
      });
    }
  }

  return result;
}

/**
 * 提取 lineup（§4, §6 lineup 段）。
 */
function extractLineup(payload) {
  const lineupContainer = safeGet(payload, 'content', 'lineup');
  if (!lineupContainer || typeof lineupContainer !== 'object') {
    return {
      home: { starters: [], subs: [], coach: {} },
      away: { starters: [], subs: [], coach: {} },
    };
  }

  function buildSquad(teamData) {
    const obj = ensureObject(teamData);

    const normalizePlayer = (p) => {
      if (!p || typeof p !== 'object') return null;
      const nameObj = ensureObject(p.name);
      return {
        id: firstValue([p.id, p.playerId], null),
        name: firstValue([
          nameObj.fullName,
          nameObj.firstName,
          p.name,
          p.fullName,
          p.playerName,
        ], null),
        position: firstValue([p.position, p.role], null),
        shirtNumber: firstValue([p.shirtNumber, p.number], null),
        rating: Number.isFinite(Number(p.rating)) ? Number(p.rating) : null,
      };
    };

    return {
      starters: ensureArray(obj.starters).map(normalizePlayer).filter(Boolean),
      subs: ensureArray(obj.subs).map(normalizePlayer).filter(Boolean),
      coach: ensureObject(obj.coach),
    };
  }

  return {
    home: buildSquad(lineupContainer.homeTeam),
    away: buildSquad(lineupContainer.awayTeam),
  };
}

/**
 * 提取 events timeline（§5, §6 events 段）。
 *
 * 从 content.matchFacts.events.events[] 读取。
 * 与 header.events（score summary）明确区分。
 */
function extractEvents(payload) {
  const eventsContainer = safeGet(payload, 'content', 'matchFacts', 'events');
  if (!eventsContainer || typeof eventsContainer !== 'object') {
    return [];
  }

  const eventsArray = ensureArray(eventsContainer.events);

  return eventsArray
    .filter((e) => e && typeof e === 'object')
    .map((e) => {
      const player = ensureObject(e.player);
      const teamSide = typeof e.isHome === 'boolean'
        ? (e.isHome ? 'home' : 'away')
        : null;

      return {
        id: firstValue([e.eventId, e.id], null),
        type: firstValue([e.type], null),
        minute: firstValue([e.time, e.timeStr, e.minute], null),
        teamSide,
        teamId: firstValue([e.teamId, e.team_id], null),
        playerId: firstValue([e.playerId, e.player_id, player.id], null),
        playerName: firstValue([e.nameStr, e.fullName, e.shortName, player.name], null),
        card: firstValue([e.card], null),
        homeScore: firstValue([e.homeScore], null),
        awayScore: firstValue([e.awayScore], null),
        assistPlayerId: firstValue([e.assistPlayerId, e.assist_player_id], null),
        outcome: firstValue([e.outcome], null),
      };
    });
}

/**
 * 提取 shotmap（§6 shotmap 段）。
 */
function extractShotmap(payload) {
  const shotmap = safeGet(payload, 'content', 'shotmap');
  if (!shotmap || typeof shotmap !== 'object') {
    return { shots: [] };
  }

  return {
    shots: ensureArray(shotmap.shots),
  };
}

/**
 * 提取 playerStats（§6 playerStats 段）。
 */
function extractPlayerStats(payload) {
  const playerStats = safeGet(payload, 'content', 'playerStats');
  if (!playerStats || typeof playerStats !== 'object') {
    return {};
  }
  return playerStats;
}

// ---------------------------------------------------------------------------
// 主入口
// ---------------------------------------------------------------------------

/**
 * 解析 fotmob_live_v1 raw payload。
 *
 * @param {object} payload - 原始 raw payload（须含 _meta, general, header, content 顶层键）
 * @param {string} [externalId] - 外部 ID（如未提供则从 payload.matchId 推导）
 * @returns {{ ok: boolean, data?: object, error?: string }}
 *   - ok: true  → data 包含解析结果（符合 contract §6 结构）
 *   - ok: false → error 包含形如 "ERROR_CODE:description" 的错误信息
 */
function parseFotMobRaw(payload, externalId) {
  // ---- 输入防御 ----
  if (!payload || typeof payload !== 'object') {
    return { ok: false, error: 'INVALID_INPUT:payload 不是有效对象' };
  }

  // ---- 必选段校验 (contract §7) ----
  const requiredSections = ['general', 'header', 'content'];
  for (const section of requiredSections) {
    if (!payload[section] || typeof payload[section] !== 'object') {
      return { ok: false, error: `MISSING_REQUIRED_SECTION:${section}` };
    }
  }

  // ---- 球队身份校验 (contract §7) ----
  const general = ensureObject(payload.general);
  if (!general.homeTeam || !general.awayTeam) {
    return { ok: false, error: 'MISSING_TEAM_IDENTITY' };
  }

  // ---- matchId 校验 (contract §7) ----
  const matchIdRaw = firstValue([payload.matchId, general.matchId]);
  const matchIdNum = Number(matchIdRaw);
  if (matchIdRaw === null || matchIdRaw === undefined || !Number.isFinite(matchIdNum)) {
    return { ok: false, error: 'INVALID_MATCH_ID' };
  }

  // ---- 各段提取 ----
  // matchId 提取和 match 结构构建
  const matchResult = extractMatch(payload, externalId);
  if (!matchResult.ok) {
    return matchResult; // 传播 INVALID_MATCH_ID
  }

  const { homeTeam, awayTeam } = extractTeams(payload);
  const stats = extractStats(payload);
  const lineup = extractLineup(payload);
  const events = extractEvents(payload);
  const shotmap = extractShotmap(payload);
  const playerStats = extractPlayerStats(payload);

  // ---- 组装输出 (contract §6) ----
  return {
    ok: true,
    data: {
      match: matchResult.data,
      homeTeam,
      awayTeam,
      stats,
      lineup,
      events,
      shotmap,
      playerStats,
      meta: {
        dataVersion: 'fotmob_live_v1',
        hashStrategy: 'stable_raw_payload_v1',
        parserVersion: '1.0.0',
        parsedAt: null, // 纯函数不产生时间戳；调用方可在上游注入
      },
    },
  };
}

module.exports = {
  parseFotMobRaw,
  // 导出内部函数便于单元测试
  _internals: {
    firstValue,
    safeGet,
    ensureArray,
    ensureObject,
    extractHomeAwayValues,
    extractMatch,
    extractTeams,
    extractStats,
    extractLineup,
    extractEvents,
    extractShotmap,
    extractPlayerStats,
  },
};
