'use strict';

const fs = require('node:fs');
const path = require('node:path');

const { Normalizer } = require('../../../src/utils/Normalizer');

const DEFAULT_ACTIVE_REGISTRY_PATH = path.resolve(__dirname, '../../../config/active_registry.json');

function normalizeSeasonTag(value) {
  return Normalizer.normalizeSeason(String(value || '').trim()).replace('/', '');
}

function safeGet(obj, pathSegments = []) {
  return pathSegments.reduce((current, segment) => {
    if (!current || typeof current !== 'object') {
      return undefined;
    }
    return current[segment];
  }, obj);
}

function loadActiveRegistry(registryPath = process.env.ACTIVE_REGISTRY_PATH || DEFAULT_ACTIVE_REGISTRY_PATH) {
  const resolvedPath = path.resolve(registryPath);
  const payload = fs.readFileSync(resolvedPath, 'utf8');
  return {
    path: resolvedPath,
    data: JSON.parse(payload)
  };
}

function resolveSeasonContext(options = {}) {
  const {
    seasonEnvVar = 'ACTIVE_SEASON',
    seasonTagEnvVar = 'ACTIVE_SEASON_TAG',
    registryPath = process.env.ACTIVE_REGISTRY_PATH || DEFAULT_ACTIVE_REGISTRY_PATH
  } = options;

  const rawEnvSeason = String(process.env[seasonEnvVar] || process.env.ACTIVE_SEASON || '').trim();
  const rawEnvSeasonTag = String(process.env[seasonTagEnvVar] || process.env.ACTIVE_SEASON_TAG || '').trim();

  let rawSeason = rawEnvSeason;
  let rawSeasonTag = rawEnvSeasonTag;
  let source = rawEnvSeason ? `env:${seasonEnvVar}` : '';
  let resolvedRegistryPath = '';

  if (!rawSeason) {
    const registry = loadActiveRegistry(registryPath);
    rawSeason = String(safeGet(registry.data, ['active_context', 'current_season']) || '').trim();
    rawSeasonTag = rawSeasonTag
      || String(safeGet(registry.data, ['active_context', 'current_season_tag']) || '').trim();
    source = `registry:${registry.path}`;
    resolvedRegistryPath = registry.path;
  }

  if (!rawSeason) {
    throw new Error(
      `缺少赛季配置：请设置 ${seasonEnvVar} 或在 ${path.resolve(registryPath)}.active_context.current_season 中声明当前赛季`
    );
  }

  const season = Normalizer.normalizeSeason(rawSeason);
  const derivedSeasonTag = season.replace('/', '');

  if (rawSeasonTag) {
    const normalizedTag = normalizeSeasonTag(rawSeasonTag);
    if (normalizedTag !== derivedSeasonTag) {
      throw new Error(
        `赛季配置不一致：season=${season} 但 ${seasonTagEnvVar || 'current_season_tag'}=${rawSeasonTag}`
      );
    }
  }

  return {
    season,
    seasonTag: derivedSeasonTag,
    source,
    registryPath: resolvedRegistryPath
  };
}

module.exports = {
  DEFAULT_ACTIVE_REGISTRY_PATH,
  loadActiveRegistry,
  normalizeSeasonTag,
  resolveSeasonContext
};
