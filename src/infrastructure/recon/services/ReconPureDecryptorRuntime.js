'use strict';

const fs = require('node:fs/promises');
const path = require('node:path');
const { webcrypto } = require('node:crypto');

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

function createDocumentStub(locationUrl) {
  const parsed = new URL(locationUrl || 'https://www.oddsportal.com/');
  const cookieStore = new Map();
  const noopElement = (tagName = 'DIV') => ({
    nodeType: 1,
    nodeName: String(tagName || 'DIV').toUpperCase(),
    tagName: String(tagName || 'DIV').toUpperCase(),
    style: {},
    dataset: {},
    textContent: '',
    innerHTML: '',
    classList: {
      add() {},
      remove() {},
      contains() {
        return false;
      }
    },
    appendChild() {},
    remove() {},
    setAttribute() {},
    getAttribute() {
      return null;
    },
    hasAttribute() {
      return false;
    },
    addEventListener() {},
    removeEventListener() {},
    dispatchEvent() {
      return true;
    },
    querySelector() {
      return noopElement();
    },
    querySelectorAll() {
      return [];
    }
  });

  const document = {
    readyState: 'complete',
    hidden: false,
    visibilityState: 'visible',
    referrer: '',
    URL: parsed.href,
    documentElement: noopElement(),
    body: noopElement(),
    head: noopElement(),
    createElement() {
      return noopElement();
    },
    createTextNode(value = '') {
      return { nodeType: 3, textContent: String(value) };
    },
    createComment(value = '') {
      return { nodeType: 8, textContent: String(value) };
    },
    createElementNS(_namespace, tagName = 'div') {
      return noopElement(tagName);
    },
    getElementById() {
      return noopElement();
    },
    getElementsByClassName() {
      return [];
    },
    getElementsByTagName(tagName = '') {
      const normalized = String(tagName || '').trim().toLowerCase();
      if (normalized === 'html') return [this.documentElement];
      if (normalized === 'body') return [this.body];
      if (normalized === 'head') return [this.head];
      return [];
    },
    querySelector(selector = '') {
      const normalized = String(selector || '').trim().toLowerCase();
      if (normalized === '#app') return null;
      if (normalized === 'html') return this.documentElement;
      if (normalized === 'body') return this.body;
      if (normalized === 'head') return this.head;
      return noopElement();
    },
    querySelectorAll() {
      return [];
    }
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
  _installBrowserLikeGlobals(globals = {}) {
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
    if (!globalThis.navigator) {
      globalThis.navigator = {
        userAgent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36',
        language: 'en-US'
      };
    }
    if (!globalThis.location) {
      globalThis.location = new URL(this.entryUrl || 'https://www.oddsportal.com/');
    }
    if (!globalThis.document) {
      globalThis.document = createDocumentStub(this.entryUrl || 'https://www.oddsportal.com/');
    }
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
    if (typeof globalThis.atob !== 'function') {
      globalThis.atob = (value) => Buffer.from(String(value || ''), 'base64').toString('binary');
    }
    if (typeof globalThis.btoa !== 'function') {
      globalThis.btoa = (value) => Buffer.from(String(value || ''), 'binary').toString('base64');
    }

    for (const [key, value] of Object.entries(globals || {})) {
      globalThis[key] = value;
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

      if (!/\.m?js(?:[?#].*)?$/i.test(specifier)) {
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
