'use strict';

const { test } = require('node:test');
const assert = require('node:assert/strict');

const { FotMobStrategy } = require('../../../../src/infrastructure/harvesters/strategies/FotMobStrategy');
const { resolveFotMobComplianceMode } = require('../../../../src/infrastructure/compliance/FotMobComplianceMode');

test('resolveFotMobComplianceMode 应让环境变量优先强制开启', () => {
  const previous = process.env.FOTMOB_COMPLIANCE_MODE;
  process.env.FOTMOB_COMPLIANCE_MODE = 'true';

  try {
    assert.equal(resolveFotMobComplianceMode({ complianceMode: false }), true);
  } finally {
    if (previous === undefined) {
      delete process.env.FOTMOB_COMPLIANCE_MODE;
    } else {
      process.env.FOTMOB_COMPLIANCE_MODE = previous;
    }
  }
});

test('FotMobStrategy 合规模式应使用 native fetch，且不调用 Cookie API client', async () => {
  const previousFetch = global.fetch;
  let apiClientCalled = false;
  const filler = 'x'.repeat(1200);
  const nextData = {
    props: {
      pageProps: {
        content: { stats: { filler } },
        general: { matchId: '4506745' },
        header: {}
      }
    }
  };

  global.fetch = async (url, options) => {
    assert.equal(options.headers.cookie, undefined);
    assert.equal(options.headers['x-requested-with'], undefined);
    assert.match(String(url), /\/match\/4506745/);
    return {
      ok: true,
      status: 200,
      async text() {
        return `<script id="__NEXT_DATA__" type="application/json">${JSON.stringify(nextData)}</script>`;
      }
    };
  };

  const strategy = new FotMobStrategy({
    complianceMode: true,
    apiClient: {
      async fetchMatchDetails() {
        apiClientCalled = true;
        throw new Error('api client should not be called');
      }
    }
  });

  try {
    const data = await strategy.fetchDataDirect({ external_id: '4506745' });
    assert.equal(data.matchId, '4506745');
    assert.equal(apiClientCalled, false);
  } finally {
    global.fetch = previousFetch;
  }
});

test('FotMobStrategy 合规模式遇到 403 应抛出不可重试语义错误', async () => {
  const previousFetch = global.fetch;
  global.fetch = async () => ({
    ok: false,
    status: 403,
    async text() {
      return 'forbidden';
    }
  });

  const strategy = new FotMobStrategy({ complianceMode: true });

  try {
    await assert.rejects(
      () => strategy.fetchDataDirect({ external_id: '4506745' }),
      /COMPLIANCE_HTTP_403/
    );
  } finally {
    global.fetch = previousFetch;
  }
});
