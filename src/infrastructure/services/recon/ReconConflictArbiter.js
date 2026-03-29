'use strict';

const { Normalizer } = require('../../../utils/Normalizer');

class ReconConflictArbiter {
  constructor(options = {}) {
    this.sameFixtureThreshold = Number(options.sameFixtureThreshold ?? 1.5);
    this.sameFixtureWindowMs = Number(options.sameFixtureWindowMs ?? 48 * 60 * 60 * 1000);
  }

  normalizeTeamName(teamName) {
    return String(Normalizer.normalizeTeamName(teamName || '') || '')
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase()
      .replace(/[^\p{L}\p{N}\s]/gu, ' ')
      .replace(/\b(fc|afc|cf|sc|ac)\b/gu, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  }

  teamSimilarity(left, right) {
    const normalizedLeft = this.normalizeTeamName(left);
    const normalizedRight = this.normalizeTeamName(right);

    if (!normalizedLeft || !normalizedRight) {
      return 0;
    }
    if (normalizedLeft === normalizedRight) {
      return 1;
    }
    if (normalizedLeft.includes(normalizedRight) || normalizedRight.includes(normalizedLeft)) {
      return 0.95;
    }

    const leftTokens = new Set(normalizedLeft.split(' ').filter(Boolean));
    const rightTokens = new Set(normalizedRight.split(' ').filter(Boolean));
    let shared = 0;
    for (const token of leftTokens) {
      if (rightTokens.has(token)) {
        shared += 1;
      }
    }

    return shared > 0 ? shared / Math.max(leftTokens.size, rightTokens.size) : 0;
  }

  fixtureOrientationScore(matchRow, mappingData) {
    if (!matchRow || !mappingData) {
      return 0;
    }

    return this.teamSimilarity(matchRow.home_team, mappingData.home_team)
      + this.teamSimilarity(matchRow.away_team, mappingData.away_team);
  }

  fixtureDateDistanceMs(leftDate, rightDate) {
    const left = new Date(leftDate || '').getTime();
    const right = new Date(rightDate || '').getTime();
    if (!Number.isFinite(left) || !Number.isFinite(right)) {
      return Number.POSITIVE_INFINITY;
    }
    return Math.abs(left - right);
  }

  selectPreferredConflictWinner(existingMatch, incomingMatch, existingMappingRow = null) {
    if (!existingMatch || !incomingMatch) {
      return 'existing';
    }

    const ordered = [String(existingMatch.match_id), String(incomingMatch.match_id)]
      .sort((left, right) => left.localeCompare(right));

    if (ordered[0] === String(existingMatch.match_id)) {
      return 'existing';
    }
    if (ordered[0] === String(incomingMatch.match_id)) {
      return 'incoming';
    }

    const existingUpdatedAt = new Date(existingMappingRow?.updated_at || 0).getTime();
    return Number.isFinite(existingUpdatedAt) ? 'existing' : 'incoming';
  }

  analyzeConflict({ existingMatch, incomingMatch, existingMapping, incomingMapping }) {
    const existingScore = this.fixtureOrientationScore(existingMatch, incomingMapping);
    const incomingScore = this.fixtureOrientationScore(incomingMatch, incomingMapping);
    const sameFixture = existingScore >= this.sameFixtureThreshold
      && incomingScore >= this.sameFixtureThreshold
      && this.fixtureDateDistanceMs(existingMatch?.match_date, incomingMatch?.match_date) <= this.sameFixtureWindowMs;

    return {
      existingScore,
      incomingScore,
      sameFixture,
      preferredWinner: sameFixture
        ? this.selectPreferredConflictWinner(existingMatch, incomingMatch, existingMapping)
        : incomingScore > existingScore
          ? 'incoming'
          : 'existing'
    };
  }
}

module.exports = { ReconConflictArbiter };
