'use strict';

const { Normalizer } = require('../../../utils/Normalizer');

function normalizeTeamName(teamName) {
  const raw = String(teamName || '')
    .replace(/[\\/]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  return String(Normalizer.normalizeTeamName(raw) || raw || '')
    .toLowerCase()
    .trim();
}

function normalizeDictionaryComparableName(teamName) {
  const raw = String(teamName || '')
    .replace(/\([^)]*\)/g, ' ')
    .replace(/\[[^\]]*\]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  return normalizeTeamName(raw);
}

function normalizeLeaguePlaceComparableName(teamName) {
  const raw = String(teamName || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/\([^)]*\)/g, ' ')
    .replace(/\[[^\]]*\]/g, ' ')
    .replace(/\bst[.\s-]+/giu, 'saint ')
    .replace(/[\\/]+/g, ' ')
    .replace(/[^\p{L}\p{N}\s-]/gu, ' ')
    .replace(/\b(as|us|usr|es|sc|rc|fc|ac|cs|ca|olympique|etoile|club)\b/giu, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  return normalizeTeamName(raw);
}

function splitCompositeTeamName(teamName) {
  return String(teamName || '')
    .split(/[\\/]+/)
    .map((segment) => String(segment || '').trim())
    .filter(Boolean);
}

function hasTextualTeamName(teamName) {
  return typeof teamName === 'string' && /[a-z\u00c0-\u024f]/i.test(teamName);
}

function extractCandidatePathname(url) {
  const raw = String(url || '').trim();
  if (!raw) {
    return '';
  }

  try {
    const parsed = new URL(raw);
    return parsed.pathname || '';
  } catch {
    return raw.split('#')[0].split('?')[0];
  }
}

function decodeCandidateTeamSegment(segment) {
  const slug = String(segment || '')
    .replace(/-[A-Za-z0-9]{8}$/i, '')
    .replace(/-/g, ' ')
    .trim();

  return slug ? (Normalizer.normalizeTeamName(slug) || slug) : '';
}

function extractTeamsFromH2hPath(pathname) {
  const match = String(pathname || '').match(/\/football\/h2h\/([^/]+)\/([^/]+)\/?$/i);
  if (!match) {
    return null;
  }

  const left = decodeCandidateTeamSegment(match[1]);
  const right = decodeCandidateTeamSegment(match[2]);
  return left && right
    ? { homeTeam: left, awayTeam: right }
    : null;
}

function tokenizeIdentityName(teamName) {
  return String(teamName || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim()
    .split(/\s+/)
    .filter(Boolean);
}

function isPlaceholderToken(token) {
  return /^\d+[a-z]+$/i.test(String(token || '').trim());
}

function isPlaceholderTeamName(teamName) {
  const normalized = String(teamName || '')
    .trim()
    .toLowerCase()
    .replace(/\s+/g, ' ');

  if (!normalized) {
    return false;
  }

  if (/\bplay[\s-]?off\b/i.test(normalized)) {
    return true;
  }

  if (/^(winner|loser)\b/i.test(normalized)) {
    return true;
  }

  const tokens = normalized.split(' ').filter(Boolean);
  return tokens.length > 0 && tokens.every(isPlaceholderToken);
}

module.exports = {
  decodeCandidateTeamSegment,
  extractCandidatePathname,
  extractTeamsFromH2hPath,
  hasTextualTeamName,
  isPlaceholderTeamName,
  isPlaceholderToken,
  normalizeDictionaryComparableName,
  normalizeLeaguePlaceComparableName,
  normalizeTeamName,
  splitCompositeTeamName,
  tokenizeIdentityName
};
