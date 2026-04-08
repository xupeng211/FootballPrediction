'use strict';

const { afterEach, describe, it } = require('node:test');
const assert = require('node:assert');
const { JSDOM } = require('jsdom');

const { reconExtractionUtils } = require('../../src/infrastructure/recon/services/ReconExtractionUtils');
const { reconDomCollectionFlow } = require('../../src/infrastructure/recon/services/ReconDomCollectionFlow');

function snapshotDescriptor(key) {
  return {
    key,
    exists: Object.prototype.hasOwnProperty.call(globalThis, key),
    descriptor: Object.getOwnPropertyDescriptor(globalThis, key)
  };
}

function restoreDescriptor(snapshot) {
  if (snapshot.exists) {
    Object.defineProperty(globalThis, snapshot.key, snapshot.descriptor);
    return;
  }

  delete globalThis[snapshot.key];
}

describe('ReconDomCollectionFlow', () => {
  const globalSnapshots = ['window', 'document', 'MouseEvent'].map(snapshotDescriptor);

  const createFlowWithEvaluateHtml = (html) => ({
    baseUrl: 'https://www.oddsportal.com',
    page: {
      async evaluate(handler, args) {
        const dom = new JSDOM(html, {
          url: args.pageUrl || args.currentResultsUrl || 'https://www.oddsportal.com/'
        });

        Object.defineProperty(globalThis, 'window', {
          value: dom.window,
          configurable: true,
          writable: true
        });
        Object.defineProperty(globalThis, 'document', {
          value: dom.window.document,
          configurable: true,
          writable: true
        });
        Object.defineProperty(globalThis, 'MouseEvent', {
          value: dom.window.MouseEvent,
          configurable: true,
          writable: true
        });

        return handler(args);
      }
    },
    ...reconExtractionUtils,
    ...reconDomCollectionFlow
  });

  afterEach(() => {
    globalSnapshots.forEach(restoreDescriptor);
  });

  it('__NEXT_DATA__ 解析失败时应回退到 DOM 锚点提取', async () => {
    const html = [
      '<html><body>',
      '  <script id="__NEXT_DATA__" type="application/json">{invalid-json}</script>',
      '  <div data-testid="event-row">',
      '    <a href="/football/england/championship-2025-2026/leeds-united-burnley-AbCd1234/">',
      '      <span data-testid="home-team">Leeds United</span>',
      '      <span data-testid="away-team">Burnley</span>',
      '    </a>',
      '  </div>',
      '</body></html>'
    ].join('');

    const flow = createFlowWithEvaluateHtml(html);

    const matches = await flow.extractCurrentSeasonResultRows(
      'https://www.oddsportal.com/football/england/championship-2025-2026/results/'
    );

    assert.deepStrictEqual(matches, [
      {
        url: 'https://www.oddsportal.com/football/england/championship-2025-2026/leeds-united-burnley-AbCd1234/',
        hash: 'AbCd1234',
        homeTeam: 'Leeds United',
        awayTeam: 'Burnley',
        matchDate: null,
        source: 'current_results_dom'
      }
    ]);
  });

  it('evaluate 路径应提取分页元数据', async () => {
    const flow = createFlowWithEvaluateHtml([
      '<html><body>',
      '  <nav>',
      '    <a href="/football/england/championship-2025-2026/results/">1</a>',
      '    <a href="/football/england/championship-2025-2026/results/page/2/">2</a>',
      '    <a href="/football/england/championship-2025-2026/results/page/4/">4</a>',
      '  </nav>',
      '</body></html>'
    ].join(''));

    const meta = await flow.extractPaginationMeta(
      'https://www.oddsportal.com/football/england/championship-2025-2026/results/'
    );

    assert.deepStrictEqual(meta, {
      pageUrls: [
        'https://www.oddsportal.com/football/england/championship-2025-2026/results/page/2/',
        'https://www.oddsportal.com/football/england/championship-2025-2026/results/page/4/'
      ],
      totalPages: 4
    });
  });

  it('evaluate 路径应识别并按年份倒序返回赛季导航链接', async () => {
    const flow = createFlowWithEvaluateHtml([
      '<html><body>',
      '  <a href="/football/usa/mls/results/">Current</a>',
      '  <a href="/football/usa/mls-2024/results/">2024</a>',
      '  <a href="/football/usa/mls-2022/results/page/2/">2022 page</a>',
      '  <a href="/football/usa/mls-2023/results/">2023</a>',
      '  <a href="/football/usa/mls/standings/">standings</a>',
      '</body></html>'
    ].join(''));

    const seasonUrls = await flow.extractSeasonNavigationUrls(
      'https://www.oddsportal.com/football/usa/mls/results/'
    );

    assert.deepStrictEqual(seasonUrls, [
      'https://www.oddsportal.com/football/usa/mls-2024/results/',
      'https://www.oddsportal.com/football/usa/mls-2023/results/',
      'https://www.oddsportal.com/football/usa/mls-2022/results/page/2/'
    ]);
  });

  it('extractSeasonNavigationUrls 应过滤跨联赛与无赛季编号链接', async () => {
    const flow = createFlowWithEvaluateHtml([
      '<html><body>',
      '  <a href="/football/mexico/liga-mx-2024/results/">cross-league</a>',
      '  <a href="/football/usa/mls/results/page/2/">current-pagination</a>',
      '  <a href="/football/usa/mls-2024/results/">valid-season</a>',
      '</body></html>'
    ].join(''));

    const seasonUrls = await flow.extractSeasonNavigationUrls(
      'https://www.oddsportal.com/football/usa/mls/results/'
    );

    assert.deepStrictEqual(seasonUrls, [
      'https://www.oddsportal.com/football/usa/mls-2024/results/'
    ]);
  });

  it('应按信息密度合并首屏候选并准确描述来源', () => {
    const flow = {
      ...reconDomCollectionFlow
    };

    const merged = flow.mergeInitialMatches(
      [{ hash: 'same', url: 'https://a.test', homeTeam: 'A' }],
      [
        {
          hash: 'same',
          url: 'https://a.test',
          homeTeam: 'A',
          awayTeam: 'B',
          matchDate: '2026-04-06T00:00:00.000Z'
        },
        {
          hash: 'dom-only',
          url: 'https://b.test',
          homeTeam: 'C',
          awayTeam: 'D'
        }
      ]
    );

    assert.deepStrictEqual(merged, [
      {
        hash: 'same',
        url: 'https://a.test',
        homeTeam: 'A',
        awayTeam: 'B',
        matchDate: '2026-04-06T00:00:00.000Z'
      },
      {
        hash: 'dom-only',
        url: 'https://b.test',
        homeTeam: 'C',
        awayTeam: 'D'
      }
    ]);
    assert.strictEqual(flow.describeInitialSource([{ hash: 'x' }], [{ hash: 'y' }]), 'page_intercept+page_dom');
    assert.strictEqual(flow.describeInitialSource([{ hash: 'x' }], []), 'page_intercept');
    assert.strictEqual(flow.describeInitialSource([], [{ hash: 'y' }]), 'page_dom');
    assert.strictEqual(flow.describeInitialSource([], []), 'page_empty');
  });

  it('mergeInitialMatches 应忽略缺失 hash/url 的候选', () => {
    const flow = {
      ...reconDomCollectionFlow
    };

    const merged = flow.mergeInitialMatches(
      [
        { homeTeam: 'NoKey FC', awayTeam: 'Ghost FC' },
        { hash: 'stable', url: 'https://a.test', homeTeam: 'A' }
      ],
      [
        { hash: 'stable', url: 'https://a.test', homeTeam: 'A', awayTeam: 'B' }
      ]
    );

    assert.deepStrictEqual(merged, [
      { hash: 'stable', url: 'https://a.test', homeTeam: 'A', awayTeam: 'B' }
    ]);
  });

  it('collectCurrentSeasonResults 应在停滞后停止滚动并返回最佳结果', async () => {
    const scrollSteps = [];
    const waits = [];
    const rounds = [];
    const batches = [
      [{ hash: 'A' }],
      [{ hash: 'A' }, { hash: 'B' }],
      [{ hash: 'A' }, { hash: 'B' }]
    ];
    const flow = {
      ...reconDomCollectionFlow,
      minScrollRounds: 1,
      scrollAttempts: 4,
      stagnantRoundsThreshold: 1,
      pageScrollFloorPx: 500,
      pageScrollStepBasePx: 200,
      pageScrollWaitCapMs: 100,
      pageScrollWaitMs: 40,
      scrollDelayMs: 80,
      page: {
        async evaluate(_handler, step) {
          scrollSteps.push(step);
        }
      },
      async wakeCurrentSeasonDom(round) {
        rounds.push(round);
      },
      async extractCurrentSeasonResultRows() {
        return batches.shift() || [];
      },
      async _wait(_hook, ms) {
        waits.push(ms);
      }
    };

    const summary = await flow.collectCurrentSeasonResults(
      'https://www.oddsportal.com/football/usa/mls/results/',
      { maxScrollRounds: 4, scrollDelayMs: 80 }
    );

    assert.deepStrictEqual(scrollSteps, [500, 500]);
    assert.deepStrictEqual(waits, [80, 80]);
    assert.deepStrictEqual(rounds, [0, 1, 2]);
    assert.strictEqual(summary.totalCandidates, 2);
    assert.deepStrictEqual(summary.matches, [{ hash: 'A' }, { hash: 'B' }]);
    assert.deepStrictEqual(summary.pageStats, [{
      page: 1,
      rows: 2,
      newRows: 2,
      total: 2
    }]);
  });

  it('collectCurrentSeasonResults 应执行页面滚动 evaluate 回调', async () => {
    const scrollByCalls = [];
    const waits = [];
    const flow = {
      ...reconDomCollectionFlow,
      minScrollRounds: 1,
      scrollAttempts: 2,
      stagnantRoundsThreshold: 99,
      pageScrollFloorPx: 100,
      pageScrollStepBasePx: 20,
      pageScrollWaitCapMs: 120,
      pageScrollWaitMs: 20,
      scrollDelayMs: 80,
      page: {
        async evaluate(handler, step) {
          Object.defineProperty(globalThis, 'window', {
            value: {
              scrollBy(x, y) {
                scrollByCalls.push([x, y]);
              }
            },
            configurable: true,
            writable: true
          });

          return handler(step);
        }
      },
      async wakeCurrentSeasonDom() {},
      async extractCurrentSeasonResultRows() {
        return [];
      },
      async _wait(_hook, ms) {
        waits.push(ms);
      }
    };

    const summary = await flow.collectCurrentSeasonResults(
      'https://www.oddsportal.com/football/usa/mls/results/',
      { maxScrollRounds: 2, scrollDelayMs: 80 }
    );

    assert.deepStrictEqual(scrollByCalls, [[0, 100]]);
    assert.deepStrictEqual(waits, [80]);
    assert.strictEqual(summary.totalCandidates, 0);
  });

  it('wakeCurrentSeasonDom 与 _wait 应覆盖异常与双分支等待路径', async () => {
    const waits = [];
    let clickCount = 0;
    const flow = {
      wakeMouseX: 12,
      wakeMouseY: 18,
      wakeScrollStepPx: 90,
      page: {
        mouse: {
          async click() {
            clickCount += 1;
            throw new Error('mouse failed');
          }
        },
        async evaluate() {
          throw new Error('evaluate failed');
        },
        async waitForTimeout(ms) {
          waits.push(`page:${ms}`);
        }
      },
      ...reconDomCollectionFlow
    };

    await assert.doesNotReject(flow.wakeCurrentSeasonDom(2));
    await flow._wait((ms) => {
      waits.push(`hook:${ms}`);
    }, 25);
    await flow._wait(null, 40);

    assert.strictEqual(clickCount, 1);
    assert.deepStrictEqual(waits, ['hook:25', 'page:40']);
  });

  it('wakeCurrentSeasonDom 在无 page 时应直接返回', async () => {
    const flow = {
      ...reconDomCollectionFlow,
      page: null
    };

    await assert.doesNotReject(flow.wakeCurrentSeasonDom(1));
  });

  it('wakeCurrentSeasonDom 应执行 evaluate 回调内的 DOM 唤醒逻辑', async () => {
    const dispatchedEvents = [];
    const scrollToCalls = [];
    let clickCount = 0;

    class FakeMouseEvent {
      constructor(type, options) {
        this.type = type;
        this.options = options;
      }
    }

    Object.defineProperty(globalThis, 'window', {
      value: {
        innerHeight: 500,
        scrollTo(payload) {
          scrollToCalls.push(payload);
        }
      },
      configurable: true,
      writable: true
    });
    Object.defineProperty(globalThis, 'document', {
      value: {
        body: {
          scrollHeight: 1200,
          dispatchEvent(event) {
            dispatchedEvents.push(event);
          }
        }
      },
      configurable: true,
      writable: true
    });
    Object.defineProperty(globalThis, 'MouseEvent', {
      value: FakeMouseEvent,
      configurable: true,
      writable: true
    });

    const flow = {
      ...reconDomCollectionFlow,
      wakeMouseX: 33,
      wakeMouseY: 44,
      wakeScrollStepPx: 150,
      page: {
        mouse: {
          async click() {
            clickCount += 1;
          }
        },
        async evaluate(handler, payload) {
          return handler(payload);
        }
      }
    };

    await assert.doesNotReject(flow.wakeCurrentSeasonDom(1));
    assert.strictEqual(clickCount, 1);
    assert.strictEqual(dispatchedEvents.length, 1);
    assert.strictEqual(dispatchedEvents[0].type, 'click');
    assert.deepStrictEqual(scrollToCalls, [{ top: 800, behavior: 'auto' }]);
  });
});
