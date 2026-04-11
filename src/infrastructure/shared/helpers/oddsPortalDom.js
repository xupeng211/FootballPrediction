'use strict';

function runOddsPortalDomExtraction() {
  function createResults() {
    return {
      '1x2': null,
      pinnacleOdds: null,
      bet365Odds: null,
      allBookmakers: [],
      _source: 'unknown',
      _diagnostic: {
        title: document.title,
        url: window.location.href,
        bodyTextLength: document.body?.innerText?.length || 0,
        hasBody: Boolean(document.body),
        timestamp: new Date().toISOString()
      }
    };
  }

  function parseOddsTriplet(text) {
    const matches = String(text || '').match(/(\d+\.\d{2,3})/g);
    return matches && matches.length >= 3 ? matches.slice(0, 3) : null;
  }

  function extractScriptOddsPayload(text) {
    if (!text || (!text.includes('"odds"') && !text.includes('"initialOdds"') && !text.includes('"fullTime"'))) {
      return null;
    }

    const patterns = [
      /"odds"\s*:\s*(\{[^}]+\})/,
      /"initialOdds"\s*:\s*(\{[^}]+\})/,
      /"fullTime"\s*:\s*(\[[^\]]+\])/
    ];

    for (const pattern of patterns) {
      const match = text.match(pattern);
      if (!match) {
        continue;
      }

      try {
        const parsed = JSON.parse(match[1]);
        const odds = parsed['1x2'] || parsed.fullTime || parsed;
        return Array.isArray(odds) && odds.length === 3
          ? odds.map(value => (typeof value === 'number' ? value.toFixed(2) : String(value)))
          : null;
      } catch (error) {
        continue;
      }
    }

    return null;
  }

  function scanScripts(results) {
    try {
      const scripts = Array.from(document.querySelectorAll('script'));
      for (const script of scripts) {
        const odds = extractScriptOddsPayload(script.textContent || '');
        if (odds) {
          results['1x2'] = odds;
          results._source = 'script_json';
          return;
        }
      }
    } catch (error) {
      return;
    }
  }

  function assignBookmakerOdds(results, text) {
    const lowerText = text.toLowerCase();
    const odds = parseOddsTriplet(text);
    if (!odds) {
      return;
    }

    if (lowerText.includes('pinnacle') && !results.pinnacleOdds) {
      results.pinnacleOdds = odds;
    }

    if ((lowerText.includes('bet365') || lowerText.includes('365')) && !results.bet365Odds) {
      results.bet365Odds = odds;
    }
  }

  function scanBookmakerRows(results) {
    if (results.pinnacleOdds && results.bet365Odds) {
      return;
    }

    const rows = document.querySelectorAll('tr, .row, .bookmaker-row, [class*="bookmaker"]');
    rows.forEach(row => {
      const text = row.innerText || row.textContent || '';
      assignBookmakerOdds(results, text);
    });
  }

  function extractSelectorOdds(selector) {
    const elements = Array.from(document.querySelectorAll(selector));
    const values = elements
      .map(element => element.textContent?.trim())
      .filter(text => text && /^\d+\.\d+$/.test(text))
      .map(text => parseFloat(text))
      .filter(value => value > 1 && value < 100);

    return values.length >= 3 ? values.slice(0, 3).map(value => value.toFixed(2)) : null;
  }

  function scanStandardSelectors(results) {
    if (results['1x2']) {
      return;
    }

    const selectors = [
      '[data-testid*="odd"]',
      '.odds',
      '.odds-value',
      '.price',
      '.flex-center.height-100',
      '[class*="odd"]',
      'div[title]'
    ];

    for (const selector of selectors) {
      const odds = extractSelectorOdds(selector);
      if (odds) {
        results['1x2'] = odds;
        results._source = `dom_${selector}`;
        return;
      }
    }
  }

  function scanBodyText(results) {
    if (results['1x2']) {
      return;
    }

    const matches = (document.body?.innerText || '').match(/\b(\d+\.\d{2})\b/g);
    if (matches && matches.length >= 3) {
      results['1x2'] = matches.slice(0, 3);
      results._source = 'text_extract';
    }
  }

  function applyPrimaryFallback(results) {
    if (results['1x2'] && !results.pinnacleOdds && !results.bet365Odds) {
      results.pinnacleOdds = results['1x2'];
    }
  }

  const results = createResults();
  scanScripts(results);
  scanBookmakerRows(results);
  scanStandardSelectors(results);
  scanBodyText(results);
  applyPrimaryFallback(results);
  return results;
}

async function extractOddsFromDOM(page) {
  return page.evaluate(runOddsPortalDomExtraction);
}

module.exports = {
  extractOddsFromDOM
};
