'use strict';

const MENU_VISIBILITY_TIMEOUT_MS = 250;
const MENU_CLICK_TIMEOUT_MS = 1000;

function normalizeStringList(value, fallback) {
  return Array.isArray(value) && value.length > 0 ? [...value] : [...fallback];
}

function createForceUnlockJ1Config(value = {}) {
  return {
    enabled: value.enabled === true,
    urlPatterns: normalizeStringList(value.url_patterns, []),
    menuLabels: normalizeStringList(value.menu_labels, []),
    selectAllLabels: normalizeStringList(value.select_all_labels, []),
    fallbackBookmakers: normalizeStringList(value.fallback_bookmakers, []),
    openWaitMs: Number(value.open_wait_ms ?? 1200),
    postSelectWaitMs: Number(value.post_select_wait_ms ?? 1800),
    stateWaitMs: Number(value.state_wait_ms ?? 5000),
    retriggerTimeoutMs: Number(value.retrigger_timeout_ms ?? 10000)
  };
}

class ReconBookmakerUnlocker {
  constructor(options = {}) {
    this.logger = options.logger || console;
    this.traceId = options.traceId || 'trace-unknown';
    this.config = createForceUnlockJ1Config(options.forceUnlockJ1 || {});
  }

  shouldForceUnlockJ1(url) {
    if (!this.config.enabled) {
      return false;
    }

    const currentUrl = String(url || '').trim().toLowerCase();
    if (!currentUrl) {
      return false;
    }

    return this.config.urlPatterns.some((pattern) => currentUrl.includes(String(pattern || '').trim().toLowerCase()));
  }

  async maybeForceUnlockJ1(page, url, callbacks = {}) {
    const shouldUnlock = typeof callbacks.shouldForceUnlockJ1 === 'function'
      ? callbacks.shouldForceUnlockJ1(url)
      : this.shouldForceUnlockJ1(url);
    if (!page || !shouldUnlock) {
      return {
        applied: false,
        reason: 'not_applicable'
      };
    }

    const before = await callbacks.readBookmakerState();
    const menuOpened = await callbacks.openBookmakerMenu();
    if (!menuOpened) {
      this.logger.warn('recon_force_unlock_j1_menu_missing', {
        traceId: this.traceId,
        url
      });
      return {
        applied: false,
        reason: 'menu_missing',
        before
      };
    }

    if (this.config.openWaitMs > 0) {
      await page.waitForTimeout(this.config.openWaitMs);
    }

    const selection = await callbacks.applyBookmakerSelection();

    if (this.config.postSelectWaitMs > 0) {
      await page.waitForTimeout(this.config.postSelectWaitMs);
    }

    const after = await callbacks.waitForBookmakerStateChange(before, this.config.stateWaitMs);
    const changed = this.bookmakerStateChanged(before, after);

    if (changed) {
      const retrigger = await callbacks.retriggerArchiveRequest({
        timeoutMs: this.config.retriggerTimeoutMs
      });
      this.logger.info('recon_force_unlock_j1_changed', {
        traceId: this.traceId,
        beforeCount: Array.isArray(before?.myBookmakers) ? before.myBookmakers.length : 0,
        afterCount: Array.isArray(after?.myBookmakers) ? after.myBookmakers.length : 0,
        selection,
        retriggered: retrigger.success
      });
      return {
        applied: true,
        changed,
        before,
        after,
        selection,
        retrigger
      };
    }

    this.logger.warn('recon_force_unlock_j1_no_state_change', {
      traceId: this.traceId,
      beforeCount: Array.isArray(before?.myBookmakers) ? before.myBookmakers.length : 0,
      afterCount: Array.isArray(after?.myBookmakers) ? after.myBookmakers.length : 0,
      selection
    });

    return {
      applied: true,
      changed: false,
      before,
      after,
      selection
    };
  }

  async openBookmakerMenu(page) {
    if (!page) {
      return false;
    }

    if (typeof page.evaluate === 'function') {
      const domClicked = await page.evaluate(({ menuLabels }) => {
        const normalize = (value) => String(value || '').replace(/\s+/g, ' ').trim().toLowerCase();
        const labels = menuLabels.map((item) => normalize(item)).filter(Boolean);
        const isVisible = (element) => {
          if (!element) {
            return false;
          }

          const style = window.getComputedStyle?.(element);
          return element.isConnected !== false
            && style?.display !== 'none'
            && style?.visibility !== 'hidden'
            && style?.opacity !== '0'
            && (element.getClientRects?.().length || 0) > 0;
        };
        const elements = Array.from(document.querySelectorAll(
          [
            'button',
            'a',
            '[role="button"]',
            '[role="link"]',
            '[data-testid*="bookmaker"]',
            '[data-test*="bookmaker"]',
            '[aria-controls*="bookmaker"]'
          ].join(',')
        ));
        const candidate = elements.find((element) => {
          const text = normalize(element.textContent);
          const aria = normalize(element.getAttribute?.('aria-label'));
          const title = normalize(element.getAttribute?.('title'));
          const dataTestId = normalize(element.getAttribute?.('data-testid'));
          const dataTest = normalize(element.getAttribute?.('data-test'));
          const href = String(element.getAttribute?.('href') || '').trim();
          const explicitBookmakerTrigger = dataTestId.includes('bookmaker')
            || dataTest.includes('bookmaker')
            || title.includes('bookmaker');
          const matchedByLabel = labels.includes(text) || labels.includes(aria) || labels.includes(title);
          return isVisible(element)
            && !/\/bookmakers\/?$/i.test(href)
            && (explicitBookmakerTrigger || matchedByLabel);
        });

        if (!candidate) {
          return false;
        }

        (candidate.closest('button,a,[role="button"],[role="link"]') || candidate).click();
        return true;
      }, {
        menuLabels: this.config.menuLabels
      });
      if (domClicked) {
        return true;
      }
    }

    if (typeof page.getByRole === 'function') {
      for (const label of this.config.menuLabels) {
        for (const role of ['link', 'button']) {
          try {
            const target = page.getByRole(role, { name: label }).first();
            const href = typeof target.getAttribute === 'function'
              ? await target.getAttribute('href')
              : null;
            if (typeof href === 'string' && /\/bookmakers\/?$/i.test(href.trim())) {
              continue;
            }
            if (await target.isVisible({ timeout: MENU_VISIBILITY_TIMEOUT_MS })) {
              await target.click({ timeout: MENU_CLICK_TIMEOUT_MS });
              return true;
            }
          } catch (_error) {
            // 继续尝试下一组 role/name 组合
          }
        }
      }
    }

    return false;
  }

  async applyBookmakerSelection(page) {
    if (!page || typeof page.evaluate !== 'function') {
      return {
        selectAllClicked: false,
        clickedBookmakers: []
      };
    }

    return page.evaluate(({ selectAllLabels, fallbackBookmakers }) => {
      const normalize = (value) => String(value || '').replace(/\s+/g, ' ').trim().toLowerCase();
      const selectAllTargets = selectAllLabels.map((item) => normalize(item)).filter(Boolean);
      const bookmakerTargets = fallbackBookmakers.map((item) => normalize(item)).filter(Boolean);
      const clickedBookmakers = [];

      const clickElement = (element) => {
        if (!element) {
          return false;
        }

        const target = element.closest('label,button,[role="button"],[role="checkbox"],a,div') || element;
        if (typeof target.click === 'function') {
          target.click();
          return true;
        }

        target.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
        return true;
      };

      const elements = Array.from(document.querySelectorAll('label,button,[role="button"],[role="checkbox"],input[type="checkbox"],a,span,div'));
      let selectAllClicked = false;

      for (const element of elements) {
        const text = normalize(element.textContent);
        const aria = normalize(element.getAttribute?.('aria-label'));
        if (!selectAllTargets.includes(text) && !selectAllTargets.includes(aria)) {
          continue;
        }

        if (clickElement(element)) {
          selectAllClicked = true;
          break;
        }
      }

      if (selectAllClicked) {
        return { selectAllClicked, clickedBookmakers };
      }

      for (const target of bookmakerTargets) {
        const element = elements.find((candidate) => {
          const text = normalize(candidate.textContent);
          const aria = normalize(candidate.getAttribute?.('aria-label'));
          return text.includes(target) || aria.includes(target);
        });

        if (element && clickElement(element)) {
          clickedBookmakers.push(target);
        }
      }

      return {
        selectAllClicked,
        clickedBookmakers
      };
    }, {
      selectAllLabels: this.config.selectAllLabels,
      fallbackBookmakers: this.config.fallbackBookmakers
    });
  }

  async readBookmakerState(page) {
    if (!page || typeof page.evaluate !== 'function') {
      return {
        myBookmakers: [],
        bookiehash: '',
        otCode: '',
        geoIPcode: ''
      };
    }

    return page.evaluate(() => ({
      myBookmakers: Array.isArray(window.pageVar?.userData?.myBookmakers)
        ? [...window.pageVar.userData.myBookmakers]
        : [],
      bookiehash: typeof window.pageVar?.bookiehash === 'string' ? window.pageVar.bookiehash : '',
      otCode: typeof window.pageVar?.otCode === 'string' ? window.pageVar.otCode : '',
      geoIPcode: typeof window.pageVar?.geoIPcode === 'string' ? window.pageVar.geoIPcode : ''
    }));
  }

  async waitForBookmakerStateChange(page, beforeState, timeoutMs) {
    if (!page || typeof page.waitForFunction !== 'function') {
      return this.readBookmakerState(page);
    }

    const timeout = Number(timeoutMs || 0);
    try {
      await page.waitForFunction(({ before }) => {
        const current = Array.isArray(window.pageVar?.userData?.myBookmakers)
          ? [...window.pageVar.userData.myBookmakers]
          : [];
        const previous = Array.isArray(before?.myBookmakers) ? before.myBookmakers : [];
        return current.length !== previous.length || current.some((value, index) => value !== previous[index]);
      }, { timeout }, { before: beforeState });
    } catch (_error) {
      // 超时后直接读取当前状态，由调用方判定是否变化
    }

    return this.readBookmakerState(page);
  }

  bookmakerStateChanged(beforeState, afterState) {
    const before = Array.isArray(beforeState?.myBookmakers) ? beforeState.myBookmakers : [];
    const after = Array.isArray(afterState?.myBookmakers) ? afterState.myBookmakers : [];

    if (before.length !== after.length) {
      return true;
    }

    if (before.some((value, index) => value !== after[index])) {
      return true;
    }

    return String(beforeState?.bookiehash || '') !== String(afterState?.bookiehash || '');
  }

  async retriggerArchiveRequest(page, options = {}) {
    if (!page || typeof page.evaluate !== 'function') {
      return { success: false, reason: 'page_unavailable' };
    }

    const timeoutMs = Number(options.timeoutMs ?? this.config.retriggerTimeoutMs);
    return page.evaluate(async ({ timeout }) => {
      const token = typeof window.pageVar?.otCode === 'string' ? window.pageVar.otCode.trim() : '';
      const bookiehash = typeof window.pageVar?.bookiehash === 'string' ? window.pageVar.bookiehash.trim() : '';
      if (!token || !bookiehash) {
        return {
          success: false,
          reason: 'missing_state',
          token,
          bookiehash
        };
      }

      const url = `https://www.oddsportal.com/ajax-sport-country-tournament-archive_/1/${token}/${bookiehash}/1/0/?_=${Date.now()}`;
      const ctrl = new AbortController();
      const timer = setTimeout(() => ctrl.abort(), timeout);

      try {
        const response = await fetch(url, {
          credentials: 'include',
          signal: ctrl.signal,
          headers: {
            'x-requested-with': 'XMLHttpRequest'
          }
        });
        const body = await response.text();
        clearTimeout(timer);
        return {
          success: response.ok,
          status: response.status,
          url,
          bodyPreview: String(body || '').slice(0, 240)
        };
      } catch (error) {
        clearTimeout(timer);
        return {
          success: false,
          reason: error.message,
          url
        };
      }
    }, {
      timeout: timeoutMs
    });
  }
}

module.exports = {
  ReconBookmakerUnlocker,
  createForceUnlockJ1Config
};
