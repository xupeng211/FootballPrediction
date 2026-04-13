'use strict';

const VALUE_SETTERS = new Map([
  ['--league-id', (result, value) => {
    result.leagueId = Number(value);
  }],
  ['--season', (result, value) => {
    result.season = value;
  }],
  ['--threshold', (result, value) => {
    result.threshold = Number(value);
  }],
  ['--remote-source', (result, value) => {
    result.remoteSource = String(value || 'auto').trim().toLowerCase();
  }],
  ['--standings-url', (result, value) => {
    result.standingsUrl = String(value || '').trim() || null;
  }],
  ['--output', (result, value) => {
    result.output = String(value || '').trim() || null;
  }]
]);

const FLAG_SETTERS = new Map([
  ['--dry-run', (result) => {
    result.dryRun = true;
  }]
]);

function parseArgs(argv = process.argv.slice(2)) {
  const result = {
    leagueId: null,
    season: null,
    threshold: 0.1,
    remoteSource: 'auto',
    standingsUrl: null,
    dryRun: false,
    output: null
  };

  for (let index = 0; index < argv.length; index++) {
    const token = argv[index];
    const valueSetter = VALUE_SETTERS.get(token);
    if (valueSetter) {
      valueSetter(result, argv[++index]);
      continue;
    }

    const flagSetter = FLAG_SETTERS.get(token);
    if (flagSetter) {
      flagSetter(result);
    }
  }

  if (!Number.isInteger(result.leagueId) || result.leagueId <= 0) {
    throw new Error('必须传入 --league-id，例如 --league-id 140');
  }
  if (!['auto', 'standings', 'mapping_candidates'].includes(result.remoteSource)) {
    throw new Error(`不支持的 --remote-source: ${result.remoteSource}`);
  }

  return result;
}

module.exports = {
  parseArgs
};
