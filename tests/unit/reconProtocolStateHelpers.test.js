'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');

const {
  detectEmbeddedHttpFailure,
  extractAppBundleUrlFromHtml,
  extractEmbeddedProtocolStateFromHtml,
  extractLocaleFromHtml,
  extractPureProtocolSeasonToken,
  extractTournamentIdFromHtml,
  normalizePureProtocolComparableUrl
} = require('../../src/infrastructure/shared/helpers/reconProtocolStateHelpers');

describe('reconProtocolStateHelpers', () => {
  describe('extractEmbeddedProtocolStateFromHtml', () => {
    it('应从 __NEXT_DATA__ 中提取 outrightId、tournamentId 与 bookmakerHash', () => {
      const html = `
        <script id="__NEXT_DATA__" type="application/json">
          {"props":{"pageProps":{"sportsData":{"pageVar":{"otCode":"ot-11","bookiehash":"X1X2"},"tournament":{"tournamentId":"tid-11"}}}}}
        </script>
      `;

      const state = extractEmbeddedProtocolStateFromHtml(html, { baseUrl: 'https://www.oddsportal.com/football/england/premier-league-2025-2026/results/' });

      assert.deepStrictEqual(state, {
        outrightId: 'ot-11',
        tournamentId: 'tid-11',
        bookmakerHash: 'X1X2'
      });
    });

    it('应支持 pageVar 字符串 JSON 与属性内嵌结构', () => {
      const html = `
        <div data-json="{&quot;tournament&quot;:{&quot;encodedTurnamentId&quot;:&quot;ot-22&quot;},&quot;pageVar&quot;:{&quot;myot&quot;:&quot;X9X10&quot;}}"></div>
        <script>window.pageVar = "{\"otCode\":\"ot-33\",\"bookiehash\":\"X3X4\"}";</script>
      `;

      const state = extractEmbeddedProtocolStateFromHtml(html, { baseUrl: 'https://www.oddsportal.com/football/spain/laliga/results/' });

      assert.strictEqual(state.outrightId, 'ot-22');
      assert.strictEqual(state.bookmakerHash, 'X9X10');
    });
  });

  describe('detectEmbeddedHttpFailure', () => {
    it('空文本不应识别为 embedded failure', () => {
      assert.strictEqual(detectEmbeddedHttpFailure(''), null);
    });

    it('placeholder 状态页应返回嵌入式 HTTP 状态', () => {
      assert.deepStrictEqual(
        detectEmbeddedHttpFailure('URL: https://op.com/archive\nStatus: 503'),
        { statusCode: 503, error: 'EMBEDDED_HTTP_503' }
      );
    });

    it('backend fetch failed 页面应返回 503', () => {
      assert.deepStrictEqual(
        detectEmbeddedHttpFailure('Guru Meditation: backend fetch failed'),
        { statusCode: 503, error: 'EMBEDDED_HTTP_503' }
      );
    });
  });

  describe('extractPureProtocolSeasonToken', () => {
    it('应优先从 results URL 中提取赛季 token', () => {
      assert.strictEqual(
        extractPureProtocolSeasonToken('https://www.oddsportal.com/football/england/premier-league-2025-2026/results/'),
        '2025-2026'
      );
    });

    it('应支持 season 形如 YYYY/YYYY 的输入', () => {
      assert.strictEqual(
        extractPureProtocolSeasonToken('', { season: '2025/2026' }),
        '2025-2026'
      );
    });

    it('非法 season 输入应返回空字符串', () => {
      assert.strictEqual(extractPureProtocolSeasonToken('', { season: 'current' }), '');
    });
  });

  describe('extractAppBundleUrlFromHtml', () => {
    it('应解析 build assets app bundle 的绝对 URL', () => {
      const html = '<script src="/build/assets/app-abc123.js"></script>';
      const url = extractAppBundleUrlFromHtml(html, 'https://www.oddsportal.com/football/england/premier-league/results/');
      assert.strictEqual(url, 'https://www.oddsportal.com/build/assets/app-abc123.js');
    });

    it('非 app bundle 资源应返回空字符串', () => {
      const html = '<script src="/build/assets/vendor-abc123.js"></script>';
      assert.strictEqual(extractAppBundleUrlFromHtml(html, 'https://www.oddsportal.com/'), '');
    });
  });

  describe('extractTournamentIdFromHtml', () => {
    it('应解析 tournamentId 字段', () => {
      assert.strictEqual(extractTournamentIdFromHtml('{"tournamentId":"tid-55"}'), 'tid-55');
    });

    it('null 或 undefined token 应回退为空字符串', () => {
      assert.strictEqual(extractTournamentIdFromHtml('{"tournamentId":"null"}'), '');
      assert.strictEqual(extractTournamentIdFromHtml('{"_tournamentId":"undefined"}'), '');
    });
  });

  describe('extractLocaleFromHtml', () => {
    it('应优先读取 _lang 字段', () => {
      assert.strictEqual(extractLocaleFromHtml('{"_lang":"es"}'), 'es');
    });

    it('无 _lang 时回退到 html lang 属性', () => {
      assert.strictEqual(extractLocaleFromHtml('<html lang="fr"><body></body></html>'), 'fr');
    });

    it('无任何 locale 标识时默认 en', () => {
      assert.strictEqual(extractLocaleFromHtml('<html></html>'), 'en');
    });
  });

  describe('normalizePureProtocolComparableUrl', () => {
    it('应移除 search、hash 与尾部斜杠', () => {
      assert.strictEqual(
        normalizePureProtocolComparableUrl('https://www.oddsportal.com/football/england/premier-league/results/?page=2#top'),
        'https://www.oddsportal.com/football/england/premier-league/results'
      );
    });

    it('非法 URL 也应尽量移除 query/hash', () => {
      assert.strictEqual(
        normalizePureProtocolComparableUrl('/football/results/?page=2#top'),
        '/football/results'
      );
    });
  });
});
