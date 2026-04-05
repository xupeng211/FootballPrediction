'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert');

const { reconProtocolFetchFlow } = require('../../src/infrastructure/recon/services/ReconProtocolFetchFlow');

describe('ReconProtocolFetchFlow', () => {
  it('应从 HTML 中提取 pure protocol 所需的 bundle、token 与赛季信息', async () => {
    const fakeHandler = {
      logger: { info() {}, warn() {}, error() {}, debug() {} },
      navigator: {
        traceId: 'trace-pure-protocol',
        archiveMaxPages: 3,
        archiveTimeoutMs: 1234,
        stateProber: {
          extractPageOutrightsMetaFromHtml() {
            return {
              id: 'xbsqV0go',
              sid: 1,
              cid: 200,
              archive: true
            };
          }
        }
      },
      async _fetchPureProtocolText() {
        return {
          success: true,
          status: 200,
          text: [
            '<html lang="en"><head>',
            '<script>var pageOutrightsVar = \'{"id":"xbsqV0go","sid":1,"cid":200,"archive":true}\';</script>',
            '<script type="module" src="/build/assets/app-HnniEWV5.js"></script>',
            '</head><body>',
            '<div data-json="&quot;_tournamentId&quot;:80299,&quot;_lang&quot;:&quot;en&quot;"></div>',
            '</body></html>'
          ].join('')
        };
      }
    };

    Object.assign(fakeHandler, reconProtocolFetchFlow);
    fakeHandler._fetchPureProtocolText = async function _fetchPureProtocolText() {
      return {
        success: true,
        status: 200,
        text: [
          '<html lang="en"><head>',
          '<script>var pageOutrightsVar = \'{"id":"xbsqV0go","sid":1,"cid":200,"archive":true}\';</script>',
          '<script type="module" src="/build/assets/app-HnniEWV5.js"></script>',
          '</head><body>',
          '<div data-json="&quot;_tournamentId&quot;:80299,&quot;_lang&quot;:&quot;en&quot;"></div>',
          '</body></html>'
        ].join('')
      };
    };
    const context = await fakeHandler._resolvePureProtocolContext(
      'https://www.oddsportal.com/football/usa/mls-2025/results/',
      {}
    );

    assert.strictEqual(context.outrightId, 'xbsqV0go');
    assert.strictEqual(context.tournamentId, '80299');
    assert.strictEqual(context.seasonToken, '2025');
    assert.strictEqual(context.locale, 'en');
    assert.strictEqual(
      context.appBundleUrl,
      'https://www.oddsportal.com/build/assets/app-HnniEWV5.js'
    );
  });
});
