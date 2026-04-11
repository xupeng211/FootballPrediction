'use strict';

const { Normalizer } = require('../../../utils/Normalizer');

const DISCOVERY_DATE_RESOLVERS = [
  (match) => match?.status?.utcTime,
  (match) => match?.matchTime,
  (match) => match?.time?.utc,
  (match) => match?.date,
  (match) => match?.kickoff?.datetime
];

function getDiscoveryExternalId(match) {
  return match?.id ?? match?.matchId ?? match?.match_id ?? null;
}

function getDiscoveryTeamSeed(match, side) {
  return match?.[side]
    ?? match?.[`${side}Team`]
    ?? match?.[`${side}_team`]
    ?? match?.[`${side}_name`]
    ?? null;
}

function hasDiscoveryTeams(match) {
  return Boolean(getDiscoveryTeamSeed(match, 'home') && getDiscoveryTeamSeed(match, 'away'));
}

function extractDiscoveryDate(match) {
  const dateValue = DISCOVERY_DATE_RESOLVERS
    .map((resolver) => resolver(match))
    .find((value) => value !== null && value !== undefined && value !== '');

  if (!dateValue) {
    return null;
  }

  const date = new Date(dateValue);
  return Number.isNaN(date.getTime()) ? null : date;
}

function safeJsonPreview(value, maxLength = 500) {
  try {
    const serialized = JSON.stringify(value);
    return typeof serialized === 'string'
      ? serialized.substring(0, maxLength)
      : '';
  } catch {
    return '[unserializable response]';
  }
}

function buildDiscoveryMatchId(leagueId, season, externalId) {
  const rawSeason = String(season || '').trim();
  const rawExternalId = String(externalId || '').trim();

  if (/^\d{4}$/.test(rawSeason)) {
    return `${leagueId}_${rawSeason}_${rawExternalId}`;
  }

  try {
    return Normalizer.buildMatchId(leagueId, rawSeason, rawExternalId);
  } catch {
    return `${leagueId}_${rawSeason.replace(/[/_-]/g, '')}_${rawExternalId}`;
  }
}

function toIsoTimestamp(value = new Date()) {
  const date = value instanceof Date ? value : new Date(value);
  return Number.isNaN(date.getTime()) ? null : date.toISOString();
}

module.exports = {
  buildDiscoveryMatchId,
  extractDiscoveryDate,
  getDiscoveryExternalId,
  getDiscoveryTeamSeed,
  hasDiscoveryTeams,
  safeJsonPreview,
  toIsoTimestamp
};
