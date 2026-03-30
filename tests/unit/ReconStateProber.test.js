'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');

const { ReconStateProber } = require('../../src/infrastructure/recon/services/ReconStateProber');

describe('ReconStateProber', () => {
  it('应从 pageOutrightsVar 脚本字符串中提取 tournamentId', () => {
    const prober = new ReconStateProber({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    const html = [
      '<html><body>',
      '<script>',
      "window.pageOutrightsVar = '{\"id\":\"KKay4EE8\",\"sid\":1,\"cid\":198,\"archive\":true}';",
      '</script>',
      '</body></html>'
    ].join('');

    const meta = prober.extractPageOutrightsMetaFromHtml(html);

    assert.deepStrictEqual(meta, {
      id: 'KKay4EE8',
      sid: 1,
      cid: 198,
      archive: true
    });
  });

  it('应使用提取出的 tournamentId 修复缺失 id 的 archive endpoint', async () => {
    const prober = new ReconStateProber({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    prober.setPage({
      async content() {
        return [
          '<html><body>',
          '<script>',
          "pageOutrightsVar = '{\"id\":\"KKay4EE8\",\"sid\":1,\"cid\":198}';",
          '</script>',
          '</body></html>'
        ].join('');
      }
    });

    const repaired = await prober.resolveCurrentSeasonArchiveEndpoint([
      'https://www.oddsportal.com/ajax-sport-country-tournament-archive_/1//X262144/1/0/?_=1'
    ], {
      scoreArchiveUrl(url) {
        return url.includes('/1//X') ? 1 : 10;
      }
    });

    assert.strictEqual(
      repaired,
      'https://www.oddsportal.com/ajax-sport-country-tournament-archive_/1/KKay4EE8/X262144/1/0/?_=1'
    );
  });

  it('缺失 outright id 时应回退到 pageVar.otCode 修复 archive endpoint', async () => {
    const prober = new ReconStateProber({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    prober.setPage({
      async content() {
        return [
          '<html><body>',
          '<script>',
          "pageOutrightsVar = '{\"id\":\"\",\"sid\":1,\"cid\":100,\"archive\":true}';",
          '</script>',
          '</body></html>'
        ].join('');
      },
      async evaluate() {
        return '5fdb38ad-528a-4fb9-a576-b8c42e07565d';
      }
    });

    const repaired = await prober.resolveCurrentSeasonArchiveEndpoint([
      'https://www.oddsportal.com/ajax-sport-country-tournament-archive_/1//X262144/1/0/?_=1'
    ], {
      scoreArchiveUrl(url) {
        return url.includes('/1//X') ? 1 : 10;
      }
    });

    assert.strictEqual(
      repaired,
      'https://www.oddsportal.com/ajax-sport-country-tournament-archive_/1/5fdb38ad-528a-4fb9-a576-b8c42e07565d/X262144/1/0/?_=1'
    );
  });

  it('seasonless results URL 应能反推出联赛主页 URL', () => {
    const prober = new ReconStateProber({
      logger: { info() {}, warn() {}, error() {}, debug() {} }
    });

    assert.strictEqual(
      prober.deriveLeaguePageUrl('https://www.oddsportal.com/football/brazil/serie-a/results/'),
      'https://www.oddsportal.com/football/brazil/serie-a/'
    );
  });
});
