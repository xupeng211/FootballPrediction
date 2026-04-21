#!/usr/bin/env node
'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');
const { Pool } = require('pg');
const { JSDOM } = require('jsdom');
const {
  REPO_ROOT,
  MIGRATIONS_DIR,
  buildDbConnectionConfig,
  readExecutableSql
} = require('./helpers/dbBlueprint');
const { EntityMapper } = require('../../src/infrastructure/etl/EntityMapper');

const DEFAULT_INPUT_DIR = path.join(REPO_ROOT, 'data', 'manual_html');
const BOOKMAKER_ODDS_HISTORY_MIGRATION = path.join(
  MIGRATIONS_DIR,
  'V12.5__create_bookmaker_odds_history.sql'
);
const CLIPBOARD_COMMANDS = [
  { command: 'powershell.exe', args: ['-NoProfile', '-Command', 'Get-Clipboard -Raw'] },
  { command: 'pbpaste', args: [] },
  { command: 'xclip', args: ['-selection', 'clipboard', '-o'] },
  { command: 'xsel', args: ['--clipboard', '--output'] },
  { command: 'wl-paste', args: ['-n'] }
];

function printUsage() {
  console.log('用法: node scripts/ops/local_dom_ingestor.js [--dir <path> | --file <path> | --clipboard] [--commit]');
  console.log('说明: 默认仅预览结构化 JSON；带 --commit 时才写入 bookmaker_odds_history。');
  console.log('说明: 仅处理本地 HTML / 剪贴板，不发起任何网络请求。');
}

function parseArgs(argv = process.argv.slice(2)) {
  const args = [...argv];
  const options = {
    mode: 'directory',
    inputPath: DEFAULT_INPUT_DIR,
    commit: false
  };

  for (let index = 0; index < args.length; index++) {
    const token = String(args[index] || '').trim();
    if (!token) {
      continue;
    }

    if (token === '--help' || token === '-h') {
      options.help = true;
      continue;
    }

    if (token === '--dir') {
      const value = args[++index];
      if (!value || String(value).startsWith('--')) {
        throw new Error('参数 --dir 缺少目录路径');
      }
      options.mode = 'directory';
      options.inputPath = path.resolve(REPO_ROOT, value);
      continue;
    }

    if (token === '--file') {
      const value = args[++index];
      if (!value || String(value).startsWith('--')) {
        throw new Error('参数 --file 缺少文件路径');
      }
      options.mode = 'file';
      options.inputPath = path.resolve(REPO_ROOT, value);
      continue;
    }

    if (token === '--clipboard') {
      options.mode = 'clipboard';
      options.inputPath = null;
      continue;
    }

    if (token === '--commit') {
      options.commit = true;
      continue;
    }

    throw new Error(`未知参数: ${token}`);
  }

  return options;
}

function normalizeText(value) {
  return String(value || '').replace(/\s+/g, ' ').trim();
}

function safeJsonParse(rawValue, fallbackValue) {
  if (!rawValue || typeof rawValue !== 'string') {
    return fallbackValue;
  }

  try {
    return JSON.parse(rawValue);
  } catch (error) {
    return fallbackValue;
  }
}

function parseDecimal(rawValue) {
  const normalized = normalizeText(rawValue).replace(/,/g, '.');
  if (!normalized) {
    return null;
  }

  const value = Number.parseFloat(normalized);
  return Number.isFinite(value) ? value : null;
}

function sha256(content) {
  return crypto.createHash('sha256').update(content).digest('hex');
}

function buildFileSource(filePath) {
  const html = fs.readFileSync(filePath, 'utf8');
  return {
    kind: 'file',
    label: path.relative(REPO_ROOT, filePath),
    html,
    digest: sha256(html),
    collectedAt: new Date().toISOString()
  };
}

function loadHtmlSources(options) {
  if (options.mode === 'clipboard') {
    return [readClipboardSource()];
  }

  if (options.mode === 'file') {
    if (!fs.existsSync(options.inputPath)) {
      throw new Error(`HTML 文件不存在: ${options.inputPath}`);
    }
    return [buildFileSource(options.inputPath)];
  }

  if (!fs.existsSync(options.inputPath)) {
    throw new Error(`HTML 目录不存在: ${options.inputPath}`);
  }

  const filePaths = fs.readdirSync(options.inputPath)
    .filter((fileName) => /\.html?$/i.test(fileName))
    .map((fileName) => path.join(options.inputPath, fileName))
    .sort((left, right) => left.localeCompare(right));

  if (filePaths.length === 0) {
    throw new Error(`目录下未找到 HTML 文件: ${options.inputPath}`);
  }

  return filePaths.map((filePath) => buildFileSource(filePath));
}

function readClipboardSource() {
  for (const entry of CLIPBOARD_COMMANDS) {
    const result = spawnSync(entry.command, entry.args, {
      cwd: REPO_ROOT,
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'pipe']
    });

    if (result.status !== 0) {
      continue;
    }

    const html = String(result.stdout || '').trim();
    if (!html || !html.includes('<')) {
      continue;
    }

    return {
      kind: 'clipboard',
      label: `clipboard:${entry.command}`,
      html,
      digest: sha256(html),
      collectedAt: new Date().toISOString()
    };
  }

  throw new Error('当前环境未发现可用剪贴板命令，请改用 --file 或 --dir');
}

function queryText(root, selectors = []) {
  for (const selector of selectors) {
    const node = root.querySelector(selector);
    const text = normalizeText(node?.textContent || '');
    if (text) {
      return text;
    }
  }

  return '';
}

function queryElement(root, selectors = []) {
  for (const selector of selectors) {
    const node = root.querySelector(selector);
    if (node) {
      return node;
    }
  }

  return null;
}

function queryAttribute(root, selectors = [], attributeName = '') {
  for (const selector of selectors) {
    const node = root.querySelector(selector);
    const value = normalizeText(node?.getAttribute(attributeName) || '');
    if (value) {
      return value;
    }
  }

  return '';
}

function queryJson(root, selectors = [], attributeName = 'data-json') {
  for (const selector of selectors) {
    const node = root.querySelector(selector);
    if (!node) {
      continue;
    }

    if (attributeName) {
      const attributeValue = node.getAttribute(attributeName);
      const parsedAttribute = safeJsonParse(attributeValue, null);
      if (parsedAttribute !== null) {
        return parsedAttribute;
      }
    }

    const parsedText = safeJsonParse(node.textContent, null);
    if (parsedText !== null) {
      return parsedText;
    }
  }

  return null;
}

function compactObject(value) {
  return Object.fromEntries(
    Object.entries(value || {}).filter(([, entryValue]) => (
      entryValue !== null
      && entryValue !== undefined
      && entryValue !== ''
    ))
  );
}

function parseMarketSnapshot(row, phase) {
  const directJson = safeJsonParse(
    row.getAttribute(`data-${phase}`) || row.getAttribute(`data-${phase}-odds`),
    null
  );
  if (directJson && typeof directJson === 'object' && !Array.isArray(directJson)) {
    return directJson;
  }

  const nestedJson = queryJson(row, [
    `[data-role="${phase}-odds"]`,
    `.${phase}-odds`,
    `script.${phase}-odds-json`,
    `script[data-role="${phase}-odds-json"]`
  ]);
  if (nestedJson && typeof nestedJson === 'object' && !Array.isArray(nestedJson)) {
    return nestedJson;
  }

  const snapshot = compactObject({
    line: queryAttribute(row, [
      `.${phase}-line`,
      `[data-role="${phase}-line"]`
    ], 'data-value') || queryText(row, [
      `.${phase}-line`,
      `[data-role="${phase}-line"]`
    ]) || null,
    home: parseDecimal(queryAttribute(row, [
      `.${phase}-home`,
      `[data-role="${phase}-home"]`
    ], 'data-value') || queryText(row, [
      `.${phase}-home`,
      `[data-role="${phase}-home"]`
    ])),
    draw: parseDecimal(queryAttribute(row, [
      `.${phase}-draw`,
      `[data-role="${phase}-draw"]`
    ], 'data-value') || queryText(row, [
      `.${phase}-draw`,
      `[data-role="${phase}-draw"]`
    ])),
    away: parseDecimal(queryAttribute(row, [
      `.${phase}-away`,
      `[data-role="${phase}-away"]`
    ], 'data-value') || queryText(row, [
      `.${phase}-away`,
      `[data-role="${phase}-away"]`
    ]))
  });

  return Object.keys(snapshot).length > 0 ? snapshot : {};
}

function parseTrajectory(row, openOdds, closeOdds) {
  const directJson = safeJsonParse(
    row.getAttribute('data-trajectory') || row.getAttribute('data-movement-trajectory'),
    null
  );
  if (Array.isArray(directJson)) {
    return directJson;
  }

  const nestedJson = queryJson(row, [
    'script.movement-trajectory',
    'script[data-role="movement-trajectory"]',
    '.movement-trajectory'
  ], '');
  if (Array.isArray(nestedJson)) {
    return nestedJson;
  }

  const fallbackTrajectory = [];
  if (Object.keys(openOdds).length > 0) {
    fallbackTrajectory.push({ stage: 'open', odds: openOdds });
  }
  if (Object.keys(closeOdds).length > 0) {
    fallbackTrajectory.push({ stage: 'close', odds: closeOdds });
  }
  return fallbackTrajectory;
}

function extractMatchMetadata(document, mapper) {
  const root = queryElement(document, [
    '[data-match-id]',
    '.op-match-page',
    '.match-page',
    'main',
    'body'
  ]);
  const rawLeagueName = queryText(document, [
    '[data-role="league-name"]',
    '.league-name',
    '.event-header .league',
    '.match-header__league'
  ]) || normalizeText(root?.getAttribute('data-league-name') || '');
  const rawHomeTeam = queryText(document, [
    '[data-role="home-team"]',
    '.participant--home .participant__name',
    '.home-team',
    '.team-home'
  ]);
  const rawAwayTeam = queryText(document, [
    '[data-role="away-team"]',
    '.participant--away .participant__name',
    '.away-team',
    '.team-away'
  ]);
  const kickoffUtc = queryAttribute(document, ['time[datetime]', '[data-role="kickoff"]'], 'datetime')
    || queryText(document, ['[data-role="kickoff"]', '.kickoff', '.match-time', 'time']);

  return {
    match_id: normalizeText(root?.getAttribute('data-match-id') || ''),
    league_name: mapper.normalizeLeagueName(rawLeagueName),
    home_team: mapper.normalizeTeamName(rawHomeTeam),
    away_team: mapper.normalizeTeamName(rawAwayTeam),
    kickoff_utc: kickoffUtc || null
  };
}

function parseOddsRows(document, metadata, source) {
  const rows = Array.from(document.querySelectorAll([
    '[data-role="odds-row"]',
    'tr.bookmaker-row',
    'tr.odds-row',
    '.odds-table__row'
  ].join(', ')));

  return rows.map((row) => {
    const openOdds = parseMarketSnapshot(row, 'open');
    const closeOdds = parseMarketSnapshot(row, 'close');

    return {
      match_id: metadata.match_id || null,
      bookmaker_name: queryText(row, [
        '[data-role="bookmaker-name"]',
        '.bookmaker-name',
        '.bookmaker'
      ]),
      market_type: normalizeText(
        row.getAttribute('data-market-type')
        || queryText(row, [
          '[data-role="market-type"]',
          '.market-type'
        ])
      ),
      open_odds: openOdds,
      close_odds: closeOdds,
      movement_trajectory: parseTrajectory(row, openOdds, closeOdds),
      source_html_path: source.kind === 'file' ? source.label : null,
      source_digest: source.digest,
      collected_at: source.collectedAt
    };
  }).filter((row) => row.bookmaker_name && row.market_type);
}

function parseHtmlSource(source, mapper = new EntityMapper()) {
  const dom = new JSDOM(source.html);
  const document = dom.window.document;
  const metadata = extractMatchMetadata(document, mapper);
  const insertPreview = parseOddsRows(document, metadata, source);

  return {
    source: {
      kind: source.kind,
      label: source.label,
      digest: source.digest
    },
    metadata,
    insertPreview
  };
}

function flattenInsertPreview(parsedResults = []) {
  return parsedResults.flatMap((result) => (
    Array.isArray(result?.insertPreview) ? result.insertPreview : []
  ));
}

async function ensureOddsHistoryTable(client) {
  const result = await client.query(`
    SELECT to_regclass('public.bookmaker_odds_history') AS table_name
  `);
  if (result.rows[0]?.table_name) {
    return false;
  }

  const migrationSql = readExecutableSql(BOOKMAKER_ODDS_HISTORY_MIGRATION);
  await client.query(migrationSql);
  return true;
}

async function assertReferencedMatchesExist(client, rows = []) {
  const distinctMatchIds = [...new Set(
    rows
      .map((row) => String(row?.match_id || '').trim())
      .filter(Boolean)
  )];

  if (distinctMatchIds.length === 0) {
    throw new Error('commit 模式至少需要 1 条带 match_id 的赔率记录');
  }

  const result = await client.query(`
    SELECT match_id
    FROM matches
    WHERE match_id = ANY($1::text[])
  `, [distinctMatchIds]);

  const existingIds = new Set(result.rows.map((row) => String(row.match_id)));
  const missingIds = distinctMatchIds.filter((matchId) => !existingIds.has(matchId));
  if (missingIds.length > 0) {
    throw new Error(`以下 match_id 在 matches 表中不存在: ${missingIds.join(', ')}`);
  }
}

async function commitInsertPreview(rows = []) {
  if (!Array.isArray(rows) || rows.length === 0) {
    return {
      total: 0,
      inserted: 0,
      updated: 0,
      migrationApplied: false
    };
  }

  const invalidRows = rows.filter((row) => !String(row?.match_id || '').trim());
  if (invalidRows.length > 0) {
    throw new Error(`发现 ${invalidRows.length} 条记录缺少 match_id，拒绝 commit`);
  }

  const pool = new Pool(buildDbConnectionConfig());
  const client = await pool.connect();

  try {
    await client.query('BEGIN');
    const migrationApplied = await ensureOddsHistoryTable(client);
    await assertReferencedMatchesExist(client, rows);

    let inserted = 0;
    let updated = 0;
    for (const row of rows) {
      const result = await client.query(`
        INSERT INTO bookmaker_odds_history (
          match_id,
          bookmaker_name,
          market_type,
          open_odds,
          close_odds,
          movement_trajectory,
          source_html_path,
          source_digest,
          collected_at
        )
        VALUES ($1, $2, $3, $4::jsonb, $5::jsonb, $6::jsonb, $7, $8, $9)
        ON CONFLICT (match_id, bookmaker_name, market_type) DO UPDATE SET
          open_odds = EXCLUDED.open_odds,
          close_odds = EXCLUDED.close_odds,
          movement_trajectory = EXCLUDED.movement_trajectory,
          source_html_path = EXCLUDED.source_html_path,
          source_digest = EXCLUDED.source_digest,
          collected_at = EXCLUDED.collected_at,
          updated_at = NOW()
        RETURNING (xmax = 0) AS inserted
      `, [
        row.match_id,
        row.bookmaker_name,
        row.market_type,
        JSON.stringify(row.open_odds || {}),
        JSON.stringify(row.close_odds || {}),
        JSON.stringify(Array.isArray(row.movement_trajectory) ? row.movement_trajectory : []),
        row.source_html_path || null,
        row.source_digest || null,
        row.collected_at || null
      ]);

      if (result.rows[0]?.inserted) {
        inserted += 1;
      } else {
        updated += 1;
      }
    }

    await client.query('COMMIT');
    return {
      total: rows.length,
      inserted,
      updated,
      migrationApplied
    };
  } catch (error) {
    await client.query('ROLLBACK').catch(() => {});
    throw error;
  } finally {
    client.release();
    await pool.end();
  }
}

async function main() {
  const options = parseArgs();
  if (options.help) {
    printUsage();
    return;
  }

  const mapper = new EntityMapper();
  const sources = loadHtmlSources(options);
  const parsedResults = [];

  for (const source of sources) {
    const parsed = parseHtmlSource(source, mapper);
    parsedResults.push(parsed);
    console.log(`[LOCAL-DOM] 源已载入 kind=${source.kind} label=${source.label} digest=${source.digest.slice(0, 12)}`);
    console.log(
      `[LOCAL-DOM] 比赛识别 match_id=${parsed.metadata.match_id || 'N/A'} `
      + `league=${parsed.metadata.league_name || 'N/A'} `
      + `home=${parsed.metadata.home_team || 'N/A'} `
      + `away=${parsed.metadata.away_team || 'N/A'} `
      + `kickoff=${parsed.metadata.kickoff_utc || 'N/A'} `
      + `rows=${parsed.insertPreview.length}`
    );
    console.log('[LOCAL-DOM] bookmaker_odds_history 入库预览:');
    console.log(JSON.stringify(parsed.insertPreview, null, 2));
  }

  if (!options.commit) {
    console.log('[LOCAL-DOM] 当前为 dry-run 模式；未执行数据库写入。');
    return;
  }

  const commitResult = await commitInsertPreview(flattenInsertPreview(parsedResults));
  console.log(
    `[LOCAL-DOM] commit 完成 total=${commitResult.total} `
    + `inserted=${commitResult.inserted} updated=${commitResult.updated} `
    + `migrationApplied=${commitResult.migrationApplied}`
  );
}

if (require.main === module) {
  main().catch((error) => {
    console.error(`[LOCAL-DOM] 失败: ${error.message}`);
    process.exit(1);
  });
}

module.exports = {
  commitInsertPreview,
  flattenInsertPreview,
  parseArgs,
  parseHtmlSource,
  readClipboardSource,
  loadHtmlSources
};
