/* eslint-disable complexity, max-lines */
'use strict';

const fs = require('node:fs/promises');
const path = require('node:path');
const { webcrypto } = require('node:crypto');
const { performance: nodePerformance } = require('node:perf_hooks');

function createStorageStub() {
  const store = new Map();
  return {
    getItem(key) {
      return store.has(String(key)) ? store.get(String(key)) : null;
    },
    setItem(key, value) {
      store.set(String(key), String(value));
    },
    removeItem(key) {
      store.delete(String(key));
    },
    clear() {
      store.clear();
    }
  };
}

function createEventTargetStub(target = {}) {
  const listeners = new Map();

  target.addEventListener = function addEventListener(type, handler) {
    const eventType = String(type || '').trim();
    if (!eventType || typeof handler !== 'function') {
      return;
    }

    if (!listeners.has(eventType)) {
      listeners.set(eventType, new Set());
    }
    listeners.get(eventType).add(handler);
  };

  target.removeEventListener = function removeEventListener(type, handler) {
    const eventType = String(type || '').trim();
    if (!eventType || typeof handler !== 'function' || !listeners.has(eventType)) {
      return;
    }

    listeners.get(eventType).delete(handler);
  };

  target.dispatchEvent = function dispatchEvent(event = {}) {
    const eventType = String(event?.type || '').trim();
    if (!eventType || !listeners.has(eventType)) {
      return true;
    }

    for (const handler of listeners.get(eventType).values()) {
      try {
        handler.call(target, event);
      } catch {
        // 纯解密沙盒中的事件监听器失败不应阻断主流程
      }
    }

    return true;
  };

  return target;
}

function createClassListStub() {
  const values = new Set();
  return {
    add(...tokens) {
      for (const token of tokens) {
        if (token) {
          values.add(String(token));
        }
      }
    },
    remove(...tokens) {
      for (const token of tokens) {
        values.delete(String(token));
      }
    },
    contains(token) {
      return values.has(String(token));
    },
    toggle(token, force) {
      const normalized = String(token);
      if (force === true) {
        values.add(normalized);
        return true;
      }
      if (force === false) {
        values.delete(normalized);
        return false;
      }
      if (values.has(normalized)) {
        values.delete(normalized);
        return false;
      }
      values.add(normalized);
      return true;
    },
    toString() {
      return [...values.values()].join(' ');
    }
  };
}

function createNodeLikeStub(tagName = 'DIV', ownerDocument = null) {
  const children = [];
  const attributes = new Map();
  const node = createEventTargetStub({
    nodeType: 1,
    nodeName: String(tagName || 'DIV').toUpperCase(),
    tagName: String(tagName || 'DIV').toUpperCase(),
    style: {},
    dataset: {},
    textContent: '',
    innerHTML: '',
    innerText: '',
    value: '',
    ownerDocument,
    parentNode: null,
    parentElement: null,
    classList: createClassListStub(),
    scrollTop: 0,
    scrollLeft: 0,
    scrollHeight: 0,
    scrollWidth: 0,
    clientHeight: 0,
    clientWidth: 0,
    offsetHeight: 0,
    offsetWidth: 0
  });

  const attachChild = (child) => {
    if (!child || typeof child !== 'object') {
      return child;
    }

    child.parentNode = node;
    child.parentElement = node;
    if (!children.includes(child)) {
      children.push(child);
    }
    return child;
  };

  node.appendChild = (child) => attachChild(child);
  node.prepend = (...items) => items.reverse().forEach((item) => attachChild(item));
  node.append = (...items) => items.forEach((item) => attachChild(item));
  node.insertBefore = (child) => attachChild(child);
  node.replaceChild = (newChild, oldChild) => {
    const index = children.indexOf(oldChild);
    if (index >= 0) {
      children.splice(index, 1);
    }
    return attachChild(newChild);
  };
  node.removeChild = (child) => {
    const index = children.indexOf(child);
    if (index >= 0) {
      children.splice(index, 1);
    }
    if (child && typeof child === 'object') {
      child.parentNode = null;
      child.parentElement = null;
    }
    return child;
  };
  node.remove = () => {
    if (node.parentNode && typeof node.parentNode.removeChild === 'function') {
      node.parentNode.removeChild(node);
    }
  };
  node.before = () => {};
  node.after = () => {};
  node.focus = () => {};
  node.blur = () => {};
  node.click = () => {};
  node.contains = (value) => value === node || children.includes(value);
  node.matches = () => false;
  node.closest = () => node;
  node.setAttribute = (name, value) => {
    attributes.set(String(name), String(value));
  };
  node.getAttribute = (name) => attributes.get(String(name)) || null;
  node.removeAttribute = (name) => {
    attributes.delete(String(name));
  };
  node.hasAttribute = (name) => attributes.has(String(name));
  node.cloneNode = () => createNodeLikeStub(node.tagName, ownerDocument);
  node.querySelector = () => createNodeLikeStub('DIV', ownerDocument);
  node.querySelectorAll = () => [];
  node.getRootNode = () => ownerDocument || node;
  node.attachShadow = () => createNodeLikeStub('DIV', ownerDocument);

  Object.defineProperty(node, 'children', {
    get() {
      return [...children];
    }
  });

  Object.defineProperty(node, 'childNodes', {
    get() {
      return [...children];
    }
  });

  Object.defineProperty(node, 'firstChild', {
    get() {
      return children[0] || null;
    }
  });

  Object.defineProperty(node, 'lastChild', {
    get() {
      return children[children.length - 1] || null;
    }
  });

  return node;
}

function createLocationStub(locationUrl = 'https://www.oddsportal.com/') {
  const parsed = new URL(locationUrl || 'https://www.oddsportal.com/');
  const location = {
    href: parsed.href,
    origin: parsed.origin,
    protocol: parsed.protocol,
    host: parsed.host,
    hostname: parsed.hostname,
    port: parsed.port,
    pathname: parsed.pathname,
    search: parsed.search,
    hash: parsed.hash,
    assign(nextUrl) {
      const next = new URL(String(nextUrl || ''), this.href);
      this.href = next.href;
      this.origin = next.origin;
      this.protocol = next.protocol;
      this.host = next.host;
      this.hostname = next.hostname;
      this.port = next.port;
      this.pathname = next.pathname;
      this.search = next.search;
      this.hash = next.hash;
    },
    replace(nextUrl) {
      this.assign(nextUrl);
    },
    reload() {},
    toString() {
      return this.href;
    }
  };

  return location;
}

function createHistoryStub(location) {
  return {
    state: null,
    length: 1,
    pushState(state, _title, url) {
      this.state = state;
      if (url) {
        location.assign(url);
      }
    },
    replaceState(state, _title, url) {
      this.state = state;
      if (url) {
        location.replace(url);
      }
    },
    back() {},
    forward() {},
    go() {}
  };
}

function createDocumentStub(locationUrl) {
  const location = createLocationStub(locationUrl);
  const cookieStore = new Map();
  const document = createEventTargetStub({
    readyState: 'complete',
    hidden: false,
    visibilityState: 'visible',
    referrer: '',
    URL: location.href
  });

  const htmlElement = createNodeLikeStub('HTML', document);
  const headElement = createNodeLikeStub('HEAD', document);
  const bodyElement = createNodeLikeStub('BODY', document);
  const appRootElement = createNodeLikeStub('DIV', document);
  appRootElement.setAttribute('id', 'app');

  htmlElement.appendChild(headElement);
  htmlElement.appendChild(bodyElement);
  bodyElement.appendChild(appRootElement);

  document.location = location;
  document.documentElement = htmlElement;
  document.head = headElement;
  document.body = bodyElement;

  document.createElement = function createElement(tagName = 'div') {
    return createNodeLikeStub(tagName, document);
  };
  document.createTextNode = function createTextNode(value = '') {
    return { nodeType: 3, textContent: String(value) };
  };
  document.createComment = function createComment(value = '') {
    return { nodeType: 8, textContent: String(value) };
  };
  document.createElementNS = function createElementNS(_namespace, tagName = 'div') {
    return createNodeLikeStub(tagName, document);
  };
  document.getElementById = function getElementById(id = '') {
    return String(id || '').trim().toLowerCase() === 'app'
      ? appRootElement
      : createNodeLikeStub('DIV', document);
  };
  document.getElementsByClassName = function getElementsByClassName() {
    return [];
  };
  document.getElementsByTagName = function getElementsByTagName(tagName = '') {
    const normalized = String(tagName || '').trim().toLowerCase();
    if (normalized === 'html') return [this.documentElement];
    if (normalized === 'body') return [this.body];
    if (normalized === 'head') return [this.head];
    return [];
  };
  document.querySelector = function querySelector(selector = '') {
    const normalized = String(selector || '').trim().toLowerCase();
    if (normalized === '#app' || normalized === '[data-app="true"]' || normalized === 'main') {
      return appRootElement;
    }
    if (normalized === 'html') return this.documentElement;
    if (normalized === 'body') return this.body;
    if (normalized === 'head') return this.head;
    return createNodeLikeStub('DIV', document);
  };
  document.querySelectorAll = function querySelectorAll(selector = '') {
    const normalized = String(selector || '').trim().toLowerCase();
    if (normalized === '#app') {
      return [appRootElement];
    }
    return [];
  };

  Object.defineProperty(document, 'cookie', {
    get() {
      return [...cookieStore.entries()].map(([key, value]) => `${key}=${value}`).join('; ');
    },
    set(value) {
      const pair = String(value || '').split(';')[0];
      const separatorIndex = pair.indexOf('=');
      if (separatorIndex > 0) {
        cookieStore.set(pair.slice(0, separatorIndex).trim(), pair.slice(separatorIndex + 1).trim());
      }
    }
  });

  return document;
}

const reconPureDecryptorRuntime = {
  _createDefaultRuntimeGlobals(globals = {}) {
    const locationHref = String(
      globals?.location?.href
      || globals?.document?.URL
      || this.entryUrl
      || 'https://www.oddsportal.com/'
    );
    const location = globals.location instanceof URL
      ? createLocationStub(globals.location.href)
      : createLocationStub(locationHref);
    const document = globals.document || createDocumentStub(location.href);
    const locale = String(
      globals?.pageVar?.locale
      || globals?.locale
      || globals?.navigator?.language
      || 'en'
    ).split('-')[0].trim() || 'en';
    const pageVar = {
      locale,
      otCode: '',
      myot: 'X',
      bookiehash: 'X',
      myBookmakers: [],
      userData: {
        myBookmakers: []
      },
      ...(globals.pageVar || {})
    };

    if (!Array.isArray(pageVar.myBookmakers)) {
      pageVar.myBookmakers = [];
    }
    if (!pageVar.userData || typeof pageVar.userData !== 'object') {
      pageVar.userData = {};
    }
    if (!Array.isArray(pageVar.userData.myBookmakers)) {
      pageVar.userData.myBookmakers = [...pageVar.myBookmakers];
    }
    if (typeof pageVar.myot !== 'string' || !pageVar.myot.trim()) {
      pageVar.myot = typeof pageVar.bookiehash === 'string' && pageVar.bookiehash.trim()
        ? pageVar.bookiehash.trim()
        : 'X';
    }
    if (typeof pageVar.bookiehash !== 'string' || !pageVar.bookiehash.trim()) {
      pageVar.bookiehash = typeof pageVar.myot === 'string' && pageVar.myot.trim()
        ? pageVar.myot.trim()
        : 'X';
    }

    return {
      location,
      document,
      navigator: {
        userAgent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36',
        language: 'en-US',
        languages: ['en-US', 'en'],
        platform: 'Linux x86_64',
        hardwareConcurrency: 8,
        ...(globals.navigator || {})
      },
      history: createHistoryStub(location),
      performance: {
        ...nodePerformance,
        now: typeof nodePerformance.now === 'function'
          ? nodePerformance.now.bind(nodePerformance)
          : (() => Date.now()),
        getEntriesByType() {
          return [];
        },
        mark() {},
        measure() {}
      },
      pageVar,
      pageOutrightsVar: {
        id: '',
        sid: 1,
        cid: 0,
        archive: true,
        ...(globals.pageOutrightsVar || {})
      }
    };
  },

  _installBrowserLikeGlobals(globals = {}) {
    const runtimeGlobals = this._createDefaultRuntimeGlobals(globals);
    const installGlobal = (key, value) => {
      const descriptor = Object.getOwnPropertyDescriptor(globalThis, key);
      if (!descriptor || descriptor.writable || descriptor.set) {
        globalThis[key] = value;
        return;
      }

      Object.defineProperty(globalThis, key, {
        value,
        configurable: true,
        enumerable: descriptor.enumerable ?? true,
        writable: true
      });
    };

    if (!globalThis.crypto) {
      globalThis.crypto = webcrypto;
    }
    if (!globalThis.window) {
      globalThis.window = globalThis;
    }
    if (!globalThis.self) {
      globalThis.self = globalThis;
    }
    if (!globalThis.localStorage) {
      globalThis.localStorage = createStorageStub();
    }
    if (!globalThis.sessionStorage) {
      globalThis.sessionStorage = createStorageStub();
    }

    installGlobal('navigator', runtimeGlobals.navigator);
    installGlobal('location', runtimeGlobals.location);
    installGlobal('document', runtimeGlobals.document);
    installGlobal('history', runtimeGlobals.history);
    installGlobal('performance', runtimeGlobals.performance);
    installGlobal('pageVar', runtimeGlobals.pageVar);
    installGlobal('pageOutrightsVar', runtimeGlobals.pageOutrightsVar);

    globalThis.window.document = globalThis.document;
    globalThis.window.location = globalThis.location;
    globalThis.window.navigator = globalThis.navigator;
    globalThis.window.history = globalThis.history;
    globalThis.window.performance = globalThis.performance;
    globalThis.window.pageVar = globalThis.pageVar;
    globalThis.window.pageOutrightsVar = globalThis.pageOutrightsVar;

    if (!globalThis.Node) {
      globalThis.Node = class Node {};
    }
    if (!globalThis.Element) {
      globalThis.Element = class Element extends globalThis.Node {};
    }
    if (!globalThis.HTMLElement) {
      globalThis.HTMLElement = class HTMLElement extends globalThis.Element {};
    }
    if (!globalThis.SVGElement) {
      globalThis.SVGElement = class SVGElement extends globalThis.Element {};
    }
    if (typeof globalThis.addEventListener !== 'function') {
      globalThis.addEventListener = () => {};
    }
    if (typeof globalThis.removeEventListener !== 'function') {
      globalThis.removeEventListener = () => {};
    }
    if (typeof globalThis.dispatchEvent !== 'function') {
      globalThis.dispatchEvent = () => true;
    }
    if (typeof globalThis.requestAnimationFrame !== 'function') {
      globalThis.requestAnimationFrame = (callback) => setTimeout(() => callback(Date.now()), 0);
    }
    if (typeof globalThis.cancelAnimationFrame !== 'function') {
      globalThis.cancelAnimationFrame = (handle) => clearTimeout(handle);
    }
    if (typeof globalThis.matchMedia !== 'function') {
      globalThis.matchMedia = (query = '') => ({
        matches: false,
        media: String(query),
        onchange: null,
        addListener() {},
        removeListener() {},
        addEventListener() {},
        removeEventListener() {},
        dispatchEvent() {
          return true;
        }
      });
    }
    if (typeof globalThis.getComputedStyle !== 'function') {
      globalThis.getComputedStyle = () => ({
        getPropertyValue() {
          return '';
        }
      });
    }
    if (!globalThis.MutationObserver) {
      globalThis.MutationObserver = class MutationObserver {
        observe() {}
        disconnect() {}
        takeRecords() {
          return [];
        }
      };
    }
    if (!globalThis.ResizeObserver) {
      globalThis.ResizeObserver = class ResizeObserver {
        observe() {}
        disconnect() {}
        unobserve() {}
      };
    }
    if (!globalThis.IntersectionObserver) {
      globalThis.IntersectionObserver = class IntersectionObserver {
        observe() {}
        disconnect() {}
        unobserve() {}
        takeRecords() {
          return [];
        }
      };
    }
    if (!globalThis.Event) {
      globalThis.Event = class Event {
        constructor(type, init = {}) {
          this.type = type;
          Object.assign(this, init);
        }
      };
    }
    if (!globalThis.CustomEvent) {
      globalThis.CustomEvent = class CustomEvent extends globalThis.Event {
        constructor(type, init = {}) {
          super(type, init);
          this.detail = init.detail;
        }
      };
    }
    if (!globalThis.Image) {
      globalThis.Image = class Image {
        constructor() {
          this.src = '';
        }
      };
    }
    if (typeof globalThis.atob !== 'function') {
      globalThis.atob = (value) => Buffer.from(String(value || ''), 'base64').toString('binary');
    }
    if (typeof globalThis.btoa !== 'function') {
      globalThis.btoa = (value) => Buffer.from(String(value || ''), 'binary').toString('base64');
    }

    for (const [key, value] of Object.entries(globals || {})) {
      globalThis[key] = value;
    }

    if (!globalThis.pageVar || typeof globalThis.pageVar !== 'object') {
      globalThis.pageVar = runtimeGlobals.pageVar;
    }
    if (typeof globalThis.pageVar.locale !== 'string' || !globalThis.pageVar.locale.trim()) {
      globalThis.pageVar.locale = runtimeGlobals.pageVar.locale;
    }
    if (!globalThis.pageOutrightsVar || typeof globalThis.pageOutrightsVar !== 'object') {
      globalThis.pageOutrightsVar = runtimeGlobals.pageOutrightsVar;
    }
  },

  async _ensureLanguageFallbackModules(rootDir) {
    if (!rootDir) {
      return;
    }

    const langRoot = path.join(rootDir, 'build', 'assets', 'resources', 'lang');
    try {
      await fs.mkdir(langRoot, { recursive: true });

      const englishPath = path.join(langRoot, 'en.json');
      const undefinedPath = path.join(langRoot, 'undefined.json');

      try {
        await fs.access(englishPath);
      } catch {
        await fs.writeFile(englishPath, '{}', 'utf8');
      }

      try {
        await fs.access(undefinedPath);
      } catch {
        const fallback = await fs.readFile(englishPath, 'utf8').catch(() => '{}');
        await fs.writeFile(undefinedPath, fallback || '{}', 'utf8');
      }
    } catch (error) {
      this.logger.debug?.('pure_decryptor_lang_fallback_prepare_failed', {
        traceId: this.traceId,
        error: error.message
      });
    }
  },

  async _selectCandidate(moduleNamespace, candidateNames = [], sampleEncryptedData = null) {
    const candidates = [];
    const seen = new Set();

    const addCandidate = (name) => {
      if (!name || seen.has(name)) {
        return;
      }

      const fn = name === 'default' ? moduleNamespace.default : moduleNamespace[name];
      if (typeof fn === 'function') {
        seen.add(name);
        candidates.push({ name, fn });
      }
    };

    for (const name of candidateNames) {
      addCandidate(name);
    }

    addCandidate('ai');
    addCandidate('default');

    for (const key of Object.keys(moduleNamespace || {})) {
      addCandidate(key);
    }

    if (sampleEncryptedData) {
      for (const candidate of candidates) {
        try {
          const output = await candidate.fn(sampleEncryptedData);
          const normalized = typeof output === 'string' ? JSON.parse(output) : output;
          if (normalized && typeof normalized === 'object') {
            return {
              ...candidate,
              validated: Boolean(normalized.d || normalized.rows || normalized.matches)
            };
          }
        } catch {
          // ignore and continue
        }
      }
    }

    if (candidates.length === 0) {
      return null;
    }

    return {
      ...candidates[0],
      validated: false
    };
  },

  async _materializeModuleTree(entryUrl, headers = {}) {
    const visited = new Map();
    await fs.mkdir(this.moduleRoot, { recursive: true });
    const rootDir = await fs.mkdtemp(path.join(this.moduleRoot, 'bundle-'));
    await this._downloadModuleRecursive(entryUrl, rootDir, headers, visited);
    await this._ensureLanguageFallbackModules(rootDir);

    const localEntry = visited.get(entryUrl);
    if (!localEntry) {
      throw new Error('PURE_DECRYPTOR_ENTRY_MISSING');
    }

    return localEntry;
  },

  async _downloadModuleRecursive(moduleUrl, rootDir, headers, visited) {
    if (visited.has(moduleUrl)) {
      return visited.get(moduleUrl);
    }

    const source = await this._fetchText(moduleUrl, headers);
    const localPath = this._resolveLocalModulePath(rootDir, moduleUrl);
    visited.set(moduleUrl, localPath);

    await fs.mkdir(path.dirname(localPath), { recursive: true });
    await fs.writeFile(localPath, source, 'utf8');

    const specifiers = this._extractModuleSpecifiers(source);
    for (const specifier of specifiers) {
      if (!/^(?:\.{1,2}\/)/.test(specifier)) {
        continue;
      }

      if (!/\.(?:m?js|json)(?:[?#].*)?$/i.test(specifier)) {
        continue;
      }

      const childUrl = new URL(specifier, moduleUrl).href;
      await this._downloadModuleRecursive(childUrl, rootDir, headers, visited);
    }

    return localPath;
  },

  _resolveLocalModulePath(rootDir, moduleUrl) {
    const parsed = new URL(moduleUrl);
    const pathname = parsed.pathname.replace(/^\/+/, '');
    return path.join(rootDir, pathname);
  },

  _extractModuleSpecifiers(source) {
    const text = String(source || '');
    const specifiers = new Set();
    const patterns = [
      /\bfrom\s*["']([^"']+)["']/g,
      /\bimport\s*["']([^"']+)["']/g
    ];

    for (const pattern of patterns) {
      for (const match of text.matchAll(pattern)) {
        if (match[1]) {
          specifiers.add(match[1]);
        }
      }
    }

    return [...specifiers.values()];
  },

  async _fetchText(url, headers = {}) {
    let lastError = null;

    for (let attempt = 1; attempt <= this.fetchRetries; attempt++) {
      try {
        const response = await this.fetchImpl(url, {
          headers,
          redirect: 'follow'
        });

        if (!response.ok) {
          lastError = new Error(`HTTP_${response.status}:${url}`);
        } else {
          return response.text();
        }
      } catch (error) {
        lastError = new Error(`FETCH_FAILED:${url}:${error.message}`);
      }
    }

    throw lastError || new Error(`FETCH_FAILED:${url}:unknown`);
  }
};

module.exports = { reconPureDecryptorRuntime };
