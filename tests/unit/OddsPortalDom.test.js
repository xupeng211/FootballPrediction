'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

const { extractOddsFromDOM } = require('../../src/infrastructure/shared/helpers/oddsPortalDom');

async function withFakeDom(documentStub, callback) {
    const originalDocument = global.document;
    const originalWindow = global.window;
    global.document = documentStub;
    global.window = {
        location: {
            href: 'https://www.oddsportal.com/football/germany/2-bundesliga/sample/',
        },
    };

    try {
        return await callback();
    } finally {
        global.document = originalDocument;
        global.window = originalWindow;
    }
}

function buildPage() {
    return {
        evaluate(fn) {
            return fn();
        },
    };
}

test('oddsPortalDom 应优先从脚本 JSON 提取 1x2，并识别主力庄家行', async () => {
    const documentStub = {
        title: 'OddsPortal sample',
        body: {
            innerText: 'Pinnacle 1.91 3.40 4.20 Bet365 1.95 3.30 4.10',
        },
        querySelectorAll(selector) {
            if (selector === 'script') {
                return [
                    {
                        textContent: 'window.__DATA__={"odds":{"1x2":[1.91,3.4,4.2]}};',
                    },
                ];
            }
            if (selector === 'tr, .row, .bookmaker-row, [class*="bookmaker"]') {
                return [{ innerText: 'Pinnacle 1.91 3.40 4.20' }, { innerText: 'Bet365 1.95 3.30 4.10' }];
            }
            return [];
        },
    };

    const result = await withFakeDom(documentStub, () => extractOddsFromDOM(buildPage()));

    assert.deepEqual(result['1x2'], ['1.91', '3.40', '4.20']);
    assert.deepEqual(result.pinnacleOdds, ['1.91', '3.40', '4.20']);
    assert.deepEqual(result.bet365Odds, ['1.95', '3.30', '4.10']);
    assert.equal(result._source, 'script_json');
    assert.equal(result._diagnostic.title, 'OddsPortal sample');
});

test('oddsPortalDom 应在无脚本赔率时回退到标准 DOM 选择器并设置主赔率', async () => {
    const documentStub = {
        title: 'DOM odds sample',
        body: {
            innerText: 'fallback text 9.99 8.88 7.77',
        },
        querySelectorAll(selector) {
            if (selector === 'script' || selector === 'tr, .row, .bookmaker-row, [class*="bookmaker"]') {
                return [];
            }
            if (selector === '[data-testid*="odd"]') {
                return [{ textContent: '2.05' }, { textContent: '3.15' }, { textContent: '3.80' }];
            }
            return [];
        },
    };

    const result = await withFakeDom(documentStub, () => extractOddsFromDOM(buildPage()));

    assert.deepEqual(result['1x2'], ['2.05', '3.15', '3.80']);
    assert.deepEqual(result.pinnacleOdds, ['2.05', '3.15', '3.80']);
    assert.equal(result.bet365Odds, null);
    assert.equal(result._source, 'dom_[data-testid*="odd"]');
});

test('oddsPortalDom 应在脚本扫描异常或脚本无效时继续走文本回退', async () => {
    const selectorCalls = [];
    const documentStub = {
        title: 'Fallback odds sample',
        body: {
            innerText: 'Pinnacle suspended 1.88 3.25 4.50',
        },
        querySelectorAll(selector) {
            selectorCalls.push(selector);
            if (selector === 'script') {
                throw new Error('blocked script access');
            }
            if (selector === 'tr, .row, .bookmaker-row, [class*="bookmaker"]') {
                return [{ innerText: 'Pinnacle suspended' }];
            }
            if (selector === '.odds') {
                return [{ textContent: 'N/A' }, { textContent: '0.99' }, { textContent: '101.00' }];
            }
            return [];
        },
    };

    const result = await withFakeDom(documentStub, () => extractOddsFromDOM(buildPage()));

    assert.ok(selectorCalls.includes('script'));
    assert.deepEqual(result['1x2'], ['1.88', '3.25', '4.50']);
    assert.deepEqual(result.pinnacleOdds, ['1.88', '3.25', '4.50']);
    assert.equal(result.bet365Odds, null);
    assert.equal(result._source, 'text_extract');
});
