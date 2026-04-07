'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');

const {
  reconMatchExtractor,
  isTrustedOddsPortalUrl
} = require('../../src/infrastructure/recon/services/ReconMatchExtractor');

describe('ReconMatchExtractor', () => {
  const annualLeagueIds = new Set([121, 223, 268]);

  it('应优先使用 home-name/away-name 而不是数字 participant id', () => {
    const extractor = {
      baseUrl: 'https://www.oddsportal.com',
      annualLeagueIds,
      extractMaxDepth: 5,
      ...reconMatchExtractor
    };

    const match = extractor.normalizeMatchObject({
      home: 26648917,
      away: 26648919,
      'home-name': 'Inter Miami',
      'away-name': 'Vancouver Whitecaps',
      encodeEventId: 'YkvQVd5d',
      slug: 'inter-miami-vancouver-whitecaps',
      countrySlug: 'usa',
      leagueSlug: 'mls',
      url: '/football/h2h/inter-miami-0AheRyBg/vancouver-whitecaps-K2dlua5N/#YkvQVd5d',
      'date-start-timestamp': 1765049400
    }, 'pure_protocol_archive:xbsqV0go');

    assert.ok(match);
    assert.strictEqual(match.homeTeam, 'Inter Miami');
    assert.strictEqual(match.awayTeam, 'Vancouver Whitecaps');
    assert.strictEqual(match.hash, 'YkvQVd5d');
  });

  it('pure protocol payload 同时提供 slug 与 h2h URL 时应优先生成事件级 canonical URL', () => {
    const extractor = {
      baseUrl: 'https://www.oddsportal.com',
      annualLeagueIds,
      extractMaxDepth: 5,
      ...reconMatchExtractor
    };

    const match = extractor.normalizeMatchObject({
      'home-name': 'Flamengo',
      'away-name': 'Palmeiras',
      encodeEventId: 'force123',
      slug: 'flamengo-palmeiras',
      countrySlug: 'brazil',
      leagueSlug: 'serie-a-betano',
      url: '/football/h2h/flamengo-rj-WjxY29qB/palmeiras-hMn9FTbH/#force123'
    }, 'pure_protocol_archive:pv7V3RRE');

    assert.ok(match);
    assert.strictEqual(
      match.url,
      'https://www.oddsportal.com/football/brazil/serie-a/flamengo-palmeiras-force123/'
    );
  });

  it('巴甲 sponsor slug 与 h2h URL 冲突时应强制收敛到标准 serie-a 事件 URL', () => {
    const extractor = {
      baseUrl: 'https://www.oddsportal.com',
      annualLeagueIds,
      extractMaxDepth: 5,
      ...reconMatchExtractor
    };

    const match = extractor.normalizeMatchObject({
      'home-name': 'Flamengo',
      'away-name': 'Palmeiras',
      encodeEventId: 'force123',
      slug: 'flamengo-palmeiras',
      country: 'brazil',
      competitionSlug: 'serie-a-betano',
      url: '/football/h2h/flamengo-rj-WjxY29qB/palmeiras-hMn9FTbH/#force123'
    }, 'pure_protocol_archive:pv7V3RRE');

    assert.ok(match);
    assert.strictEqual(
      match.url,
      'https://www.oddsportal.com/football/brazil/serie-a/flamengo-palmeiras-force123/'
    );
  });

  it('巴甲缺少 payload slug 时也应基于队名与 encodeEventId 生成标准事件 URL', () => {
    const extractor = {
      baseUrl: 'https://www.oddsportal.com',
      annualLeagueIds,
      extractMaxDepth: 5,
      ...reconMatchExtractor
    };

    const match = extractor.normalizeMatchObject({
      match_id: '268_20252026_000001',
      'home-name': 'Atletico Mineiro',
      'away-name': 'Botafogo',
      encodeEventId: 'Ab12Cd34',
      countrySlug: 'brazil',
      leagueSlug: 'serie-a-betano',
      url: '/football/h2h/atletico-mineiro-XX11/botafogo-YY22/#Ab12Cd34'
    }, 'pure_protocol_archive:pv7V3RRE');

    assert.ok(match);
    assert.strictEqual(
      match.url,
      'https://www.oddsportal.com/football/brazil/serie-a/atletico-mineiro-botafogo-Ab12Cd34/'
    );
  });

  it('pure protocol 若仅能从当前结果页拿到巴甲上下文，也应拒绝 h2h 原始 URL', () => {
    const extractor = {
      baseUrl: 'https://www.oddsportal.com',
      sourceUrl: 'https://www.oddsportal.com/football/brazil/serie-a/results/',
      annualLeagueIds,
      extractMaxDepth: 5,
      ...reconMatchExtractor
    };

    const match = extractor.normalizeMatchObject({
      'home-name': 'Cruzeiro',
      'away-name': 'Vitoria',
      encodeEventId: 'bwFhcK06',
      slug: 'cruzeiro-vitoria',
      url: '/football/h2h/cruzeiro-0SwtclaU/vitoria-8bSbHipn/#bwFhcK06'
    }, 'pure_protocol_archive:91691');

    assert.ok(match);
    assert.strictEqual(
      match.url,
      'https://www.oddsportal.com/football/brazil/serie-a/cruzeiro-vitoria-bwFhcK06/'
    );
  });

  it('年度制非巴甲联赛在具备 match_id、match_date 与 eventId 时也应优先生成 canonical URL', () => {
    const extractor = {
      baseUrl: 'https://www.oddsportal.com',
      sourceUrl: 'https://www.oddsportal.com/football/japan/j1-league/results/',
      annualLeagueIds,
      extractMaxDepth: 5,
      ...reconMatchExtractor
    };

    const match = extractor.normalizeMatchObject({
      match_id: '223_20252026_4691098',
      match_date: '2026-04-05T05:00:00.000Z',
      eventId: 'QwErTy12',
      'home-name': 'Kashiwa Reysol',
      'away-name': 'Yokohama F.Marinos',
      url: '/football/h2h/kashiwa-reysol-AbCd1234/yokohama-f-marinos-EfGh5678/#QwErTy12'
    }, 'current_results_dom');

    assert.ok(match);
    assert.strictEqual(
      match.url,
      'https://www.oddsportal.com/football/japan/j1-league/kashiwa-reysol-yokohama-f-marinos-QwErTy12/'
    );
  });

  it('非年度制联赛缺少 payload slug 时应直接拒收 h2h 原始 URL', () => {
    const extractor = {
      baseUrl: 'https://www.oddsportal.com',
      sourceUrl: 'https://www.oddsportal.com/football/england/premier-league/results/',
      annualLeagueIds,
      extractMaxDepth: 5,
      ...reconMatchExtractor
    };

    const match = extractor.normalizeMatchObject({
      match_id: '47_20252026_123456',
      match_date: '2026-04-05T05:00:00.000Z',
      eventId: 'QwErTy12',
      'home-name': 'Arsenal',
      'away-name': 'Chelsea',
      url: '/football/h2h/arsenal-AbCd1234/chelsea-EfGh5678/#QwErTy12'
    }, 'current_results_dom');

    assert.strictEqual(match, null);
  });

  it('非年度制联赛若 payload 已提供 slug，仍应安全洗白 h2h URL', () => {
    const extractor = {
      baseUrl: 'https://www.oddsportal.com',
      annualLeagueIds,
      extractMaxDepth: 5,
      ...reconMatchExtractor
    };

    const match = extractor.normalizeMatchObject({
      match_id: '47_20252026_654321',
      eventId: 'Ab12Cd34',
      slug: 'arsenal-chelsea',
      countrySlug: 'england',
      leagueSlug: 'premier-league',
      'home-name': 'Arsenal',
      'away-name': 'Chelsea',
      url: '/football/h2h/arsenal-X1/chelsea-X2/#Ab12Cd34'
    }, 'pure_protocol_archive:test');

    assert.ok(match);
    assert.strictEqual(
      match.url,
      'https://www.oddsportal.com/football/england/premier-league/arsenal-chelsea-Ab12Cd34/'
    );
  });

  it('遇到畸形 URL 时必须返回 null', () => {
    const extractor = {
      baseUrl: 'https://www.oddsportal.com',
      sourceUrl: 'https://www.oddsportal.com/football/japan/j1-league/results/',
      annualLeagueIds,
      extractMaxDepth: 5,
      ...reconMatchExtractor
    };

    const match = extractor.normalizeMatchObject({
      match_id: '223_20252026_4691098',
      eventId: 'QwErTy12',
      'home-name': 'Kashiwa Reysol',
      'away-name': 'Yokohama F.Marinos',
      url: '::::bad-url::::'
    }, 'zero_trust_probe');

    assert.strictEqual(match, null);
  });

  it('队名超过 100 字符时必须返回 null', () => {
    const extractor = {
      baseUrl: 'https://www.oddsportal.com',
      sourceUrl: 'https://www.oddsportal.com/football/japan/j1-league/results/',
      annualLeagueIds,
      extractMaxDepth: 5,
      ...reconMatchExtractor
    };
    const overlongTeamName = '超长队名'.repeat(2000);

    const match = extractor.normalizeMatchObject({
      match_id: '223_20252026_4691098',
      eventId: 'QwErTy12',
      'home-name': overlongTeamName,
      'away-name': 'Yokohama F.Marinos',
      url: '/football/h2h/kashiwa-reysol-AbCd1234/yokohama-f-marinos-EfGh5678/#QwErTy12'
    }, 'zero_trust_probe');

    assert.strictEqual(match, null);
  });

  it('非 canonical hash 必须直接返回 null', () => {
    const extractor = {
      baseUrl: 'https://www.oddsportal.com',
      sourceUrl: 'https://www.oddsportal.com/football/japan/j1-league/results/',
      annualLeagueIds,
      extractMaxDepth: 5,
      ...reconMatchExtractor
    };

    const match = extractor.normalizeMatchObject({
      match_id: '223_20252026_4691098',
      eventId: 'bad-hash',
      'home-name': 'Kashiwa Reysol',
      'away-name': 'Yokohama F.Marinos',
      url: '/football/japan/j1-league/kashiwa-reysol-yokohama-f-marinos-bad-hash/'
    }, 'zero_trust_probe');

    assert.strictEqual(match, null);
  });

  it('isTrustedOddsPortalUrl 应拒绝非 https 协议与非法 host 伪装', () => {
    const validUrl = 'https://www.oddsportal.com/football/england/premier-league/arsenal-chelsea-Ab12Cd34/';

    assert.strictEqual(isTrustedOddsPortalUrl(validUrl, 'Ab12Cd34'), true);
    assert.strictEqual(isTrustedOddsPortalUrl(validUrl, 'Zz99Yy88'), false);
    assert.strictEqual(isTrustedOddsPortalUrl(
      'ftp://www.oddsportal.com/football/england/premier-league/arsenal-chelsea-Ab12Cd34/'
    ), false);
    assert.strictEqual(isTrustedOddsPortalUrl(
      'http://www.oddsportal.com/football/england/premier-league/arsenal-chelsea-Ab12Cd34/'
    ), false);
    assert.strictEqual(isTrustedOddsPortalUrl(
      'https://www.oddsportal.com.evil.example/football/england/premier-league/arsenal-chelsea-Ab12Cd34/'
    ), false);
    assert.strictEqual(isTrustedOddsPortalUrl(
      'https://www.oddsportal.com@evil.example/football/england/premier-league/arsenal-chelsea-Ab12Cd34/'
    ), false);
  });
});
