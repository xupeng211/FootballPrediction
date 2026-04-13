'use strict';

function cleanText(value) {
  return String(value || '').replace(/\s+/g, ' ').trim();
}

function getFirstText(scope, selectors = []) {
  for (const selector of selectors) {
    const node = scope.querySelector(selector);
    const text = cleanText(node?.textContent || node?.getAttribute?.('title') || '');
    if (text) {
      return text;
    }
  }

  return '';
}

function extractTeamsFromScope(scope, options = {}) {
  const homeTeam = getFirstText(scope, options.homeSelectors || []);
  const awayTeam = getFirstText(scope, options.awaySelectors || []);
  if (homeTeam && awayTeam) {
    return { homeTeam, awayTeam };
  }

  const participantTitles = Array.from(scope.querySelectorAll('[title]'))
    .map((node) => cleanText(node.getAttribute('title') || ''))
    .filter(Boolean);
  const participantAlts = Array.from(scope.querySelectorAll('img[alt]'))
    .map((node) => cleanText(node.getAttribute('alt') || ''))
    .filter(Boolean);
  const participantTexts = Array.from(scope.querySelectorAll((options.participantSelectors || []).join(', ')))
    .map((node) => cleanText(node.textContent || ''))
    .filter(Boolean);
  const combinedNames = [...new Set([...participantTitles, ...participantAlts, ...participantTexts])];

  return {
    homeTeam: homeTeam || combinedNames[0] || '',
    awayTeam: awayTeam || combinedNames[1] || ''
  };
}

function extractNamesFromSlug(pathname) {
  const cleanPath = String(pathname || '').replace(/\/+$/, '');
  const lastSegment = cleanPath.split('/').filter(Boolean).pop() || '';
  const slugWithHash = lastSegment
    .replace(/-[A-Za-z0-9]{8}$/i, '')
    .replace(/^[A-Za-z0-9-]+$/, (value) => (/\/match\//i.test(cleanPath) ? '' : value));
  const parts = slugWithHash.split('-');
  if (parts.length < 2) {
    return { homeTeam: '', awayTeam: '' };
  }

  const midpoint = Math.ceil(parts.length / 2);
  const toTitle = (value) => value
    .split('-')
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(' ');

  return {
    homeTeam: toTitle(parts.slice(0, midpoint).join('-')),
    awayTeam: toTitle(parts.slice(midpoint).join('-'))
  };
}

function extractTeamsFromH2hPath(pathname) {
  const match = String(pathname || '').match(/\/football\/h2h\/([^/]+)\/([^/]+)\/?$/iu);
  if (!match) {
    return { homeTeam: '', awayTeam: '' };
  }

  const decodeTeam = (segment) => String(segment || '')
    .replace(/-[A-Za-z0-9]{8}$/u, '')
    .replace(/-/g, ' ')
    .trim()
    .replace(/\s+/g, ' ');

  return {
    homeTeam: decodeTeam(match[1]),
    awayTeam: decodeTeam(match[2])
  };
}

function extractTeamsFromText(value) {
  const cleanValue = cleanText(value);
  if (!cleanValue) {
    return { homeTeam: '', awayTeam: '' };
  }

  for (const separator of [/\s+vs\.?\s+/i, /\s+-\s+/]) {
    const parts = cleanValue.split(separator).map((item) => cleanText(item)).filter(Boolean);
    if (parts.length === 2) {
      return {
        homeTeam: parts[0],
        awayTeam: parts[1]
      };
    }
  }

  return { homeTeam: '', awayTeam: '' };
}

function collectStandingsTeamAnchors(document) {
  if (!document) {
    return [];
  }

  const selectors = [
    'table a[href]',
    '[role="row"] a[href]',
    '[class*="standings"] a[href]',
    '[data-testid*="standings"] a[href]',
    'a[href*="/team/"]',
    'a[href*="/teams/"]'
  ];

  return [...new Set(
    selectors.flatMap((selector) => Array.from(document.querySelectorAll(selector)))
  )];
}

function looksLikeStandaloneTeamLabel(value) {
  const label = cleanText(value);
  if (!label) {
    return false;
  }
  if (!/[a-z\u00c0-\u024f]/i.test(label)) {
    return false;
  }
  if (/\bvs\.?\b/i.test(label) || /\d+\s*[-:]\s*\d+/.test(label)) {
    return false;
  }

  return !/\b(standings?|results?|table|outrights?)\b/i.test(label);
}

function decodeTeamSlugToName(teamSlug) {
  const parts = String(teamSlug || '')
    .split('-')
    .map((part) => cleanText(part))
    .filter(Boolean);
  if (parts.length === 0) {
    return '';
  }

  return parts
    .map((part) => (/^[a-z]{1,3}$/i.test(part) ? part.toUpperCase() : part.charAt(0).toUpperCase() + part.slice(1)))
    .join(' ');
}

function extractTeamReference(url, getPathname) {
  const pathname = getPathname(url);
  if (!pathname) {
    return null;
  }
  if (/\/football\/h2h\/|\/match\//i.test(pathname)) {
    return null;
  }
  if (/\/(results|standings|outrights)(?:\/page\/\d+)?\/?$/i.test(pathname)) {
    return null;
  }

  const segments = pathname.split('/').filter(Boolean);
  if (segments.length === 0) {
    return null;
  }

  const hasExplicitTeamPrefix = segments.some((segment) => /^(team|teams)$/i.test(segment));
  if (
    !hasExplicitTeamPrefix
    && /^football$/i.test(segments[0] || '')
    && segments.length >= 4
    && /-\d{4}(?:-\d{4})?$/i.test(segments[2] || '')
  ) {
    return null;
  }

  const lastSegment = segments[segments.length - 1] || '';
  const match = lastSegment.match(/^(.*)-([A-Za-z0-9]{6,12})$/);
  if (!match) {
    return null;
  }

  const teamName = decodeTeamSlugToName(match[1]);
  if (!teamName) {
    return null;
  }

  return {
    teamName,
    teamHash: match[2],
    teamUrl: url
  };
}

function collectEventAnchors(document, eventContainerSelectors = []) {
  if (!document) {
    return [];
  }

  const containers = Array.from(document.querySelectorAll(eventContainerSelectors.join(', '))).filter(Boolean);
  const anchors = [];
  for (const container of containers) {
    anchors.push(...Array.from(container.querySelectorAll('a[href]')));
  }

  for (const anchor of Array.from(document.links || [])) {
    const href = anchor.getAttribute('href') || anchor.href || '';
    if (
      /\/match\/[^/]+\/?$/i.test(href)
      || /-([A-Za-z0-9]{8})\/?$/i.test(href)
      || /\/football\/h2h\/[^/]+\/[^/]+\/?#?[A-Za-z0-9]*$/iu.test(href)
    ) {
      anchors.push(anchor);
    }
  }

  return anchors;
}

function probeAnchorPatterns(document) {
  if (!document) {
    return [];
  }

  const anchors = [];
  for (const anchor of Array.from(document.querySelectorAll('a[href]'))) {
    const text = cleanText(anchor.textContent);
    const href = anchor.getAttribute('href') || anchor.href || '';
    if (/\/match\/[^/]+\/?$/i.test(href) || /\/football\/h2h\/[^/]+\/[^/]+\/?#?[A-Za-z0-9]*$/iu.test(href)) {
      anchors.push(anchor);
      continue;
    }
    if (text && /\bvs\.?\b|-/i.test(text)) {
      anchors.push(anchor);
    }
  }

  return anchors;
}

function matchesScopedLeaguePath(pathname, leaguePathPrefix, canonicalLeaguePathPrefix, matcher) {
  return [leaguePathPrefix, canonicalLeaguePathPrefix]
    .filter(Boolean)
    .some((prefix) => matcher(pathname, prefix));
}

function isCandidateInScope(pathname, leaguePathPrefix, canonicalLeaguePathPrefix, matcher) {
  const normalizedPath = String(pathname || '');
  if (!leaguePathPrefix && !canonicalLeaguePathPrefix) {
    return true;
  }
  if (/\/match\/[^/]+\/?$/i.test(normalizedPath) || /\/football\/h2h\/[^/]+\/[^/]+\/?$/iu.test(normalizedPath)) {
    return true;
  }

  return matchesScopedLeaguePath(normalizedPath, leaguePathPrefix, canonicalLeaguePathPrefix, matcher);
}

module.exports = {
  cleanText,
  getFirstText,
  extractTeamsFromScope,
  extractNamesFromSlug,
  extractTeamsFromH2hPath,
  extractTeamsFromText,
  collectStandingsTeamAnchors,
  looksLikeStandaloneTeamLabel,
  extractTeamReference,
  decodeTeamSlugToName,
  collectEventAnchors,
  probeAnchorPatterns,
  isCandidateInScope
};
