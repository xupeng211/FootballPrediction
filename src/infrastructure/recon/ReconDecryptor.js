/**
 * ReconDecryptor - 协议解密专家 (V11.0 Clean Sweep)
 * ================================================
 *
 * 职责: 动态提取并执行 OddsPortal 的解密逻辑
 * 核心特性:
 * 1. 不再硬编码依赖 mod.ai，使用正则动态提取特征函数名
 * 2. 支持多种解密算法自适应切换
 * 3. 完全无头，不依赖特定 JS 文件结构
 *
 * @module infrastructure/recon/ReconDecryptor
 * @version V11.0-CLEAN-SWEEP
 * @date 2026-03-25
 */

'use strict';

/**
 * 解密专家类
 * @class ReconDecryptor
 */
class ReconDecryptor {
  constructor(options = {}) {
    this.logger = options.logger || console;
    this.traceId = options.traceId || 'no-trace';
    this.decryptFn = null;
    this.algorithmVersion = null;
    this.allowBestEffortCandidate = options.allowBestEffortCandidate === true;
  }

  /**
   * 从页面动态提取解密函数
   * @param {Page} page - Playwright Page 实例
   * @returns {Promise<Function>} 解密函数
   */
  async extractDecryptor(page, sampleEncryptedData = null) {
    if (!page) {
      throw new Error('Page instance required');
    }

    try {
      // 方法1: 尝试从 app-*.js 提取
      const decryptFn = await this._extractFromAppScript(page, sampleEncryptedData);
      if (decryptFn) {
        this.decryptFn = decryptFn; // V11.0 FIX: 保存解密函数
        this.logger.info('decryptor_extracted', {
          method: 'app_script',
          version: this.algorithmVersion,
          validated: decryptFn.__validated !== false,
          bestEffort: decryptFn.__bestEffort === true
        });
        return decryptFn;
      }

      // 方法2: 尝试页面内联脚本
      const inlineFn = await this._extractFromInlineScripts(page);
      if (inlineFn) {
        this.decryptFn = inlineFn; // V11.0 FIX: 保存解密函数
        this.logger.info('decryptor_extracted', { method: 'inline_script', version: this.algorithmVersion });
        return inlineFn;
      }

      // 方法3: 尝试全局暴露的函数
      const globalFn = await this._extractFromGlobalScope(page);
      if (globalFn) {
        this.decryptFn = globalFn; // V11.0 FIX: 保存解密函数
        this.logger.info('decryptor_extracted', { method: 'global_scope', version: this.algorithmVersion });
        return globalFn;
      }

      throw new Error('Failed to extract decryptor from any source');
    } catch (error) {
      this.logger.error('decryptor_extraction_failed', { error: error.message });
      throw error;
    }
  }

  /**
   * 从 app-*.js 提取解密函数
   * @private
   */
  async _extractFromAppScript(page, sampleEncryptedData = null) {
    try {
      // 动态导入 app script
      const appScriptUrl = await page.evaluate(() => {
        const script = Array.from(document.querySelectorAll('script[src*="/build/assets/app-"]'))
          .map(s => s.src)
          .find(Boolean);
        return script;
      });

      if (!appScriptUrl) {
        return null;
      }

      const sampleProbe = sampleEncryptedData
        ? this._probeEncryptedPayload(this._cleanPayload(sampleEncryptedData))
        : null;
      const bundleSource = await this._fetchBundleSource(page, appScriptUrl);
      const bundleCandidateNames = this._extractFromBundle(bundleSource);

      if (sampleEncryptedData && sampleProbe && !sampleProbe.valid) {
        this.logger.debug('app_script_sample_invalid_skip_best_effort', {
          traceId: this.traceId,
          preview: sampleProbe.preview || ''
        });
      }

      // 在页面上下文中动态导入并提取解密函数
      const decryptFn = await page.evaluate(async ({ url, sample, allowBestEffort, candidateNames }) => {
        try {
          const module = await import(url);

          const candidates = [];
          const seen = new Set();
          const possibleNames = Array.isArray(candidateNames) && candidateNames.length > 0
            ? candidateNames
            : ['ai', 'decrypt', 'decode', 'parse', 'unpack', 'transform', 'deserialize', 'unzip'];

          const addCandidate = (name, type) => {
            if (!name || seen.has(name)) return;
            const fn = name === 'default' ? module.default : module[name];
            if (typeof fn === 'function') {
              seen.add(name);
              candidates.push({ name, type });
            }
          };

          for (const name of possibleNames) {
            addCandidate(name, 'named_export');
          }

          addCandidate('default', 'default_export');

          for (const key of Object.keys(module)) {
            addCandidate(key, 'auto_detected');
          }

          const isValidPayload = (value) => {
            try {
              const raw = typeof value === 'string' ? value : JSON.stringify(value);
              if (!raw || typeof raw !== 'string') return false;

              const trimmed = raw.trim();
              if (!trimmed.startsWith('{') && !trimmed.startsWith('[')) {
                return false;
              }

              const parsed = typeof value === 'object' && value !== null
                ? value
                : JSON.parse(trimmed);

              return Boolean(parsed && typeof parsed === 'object' && (
                parsed.d ||
                parsed.rows ||
                parsed.s !== undefined ||
                parsed.refresh !== undefined
              ));
            } catch {
              return false;
            }
          };

          if (sample) {
            for (const candidate of candidates) {
              try {
                const fn = candidate.name === 'default' ? module.default : module[candidate.name];
                const output = await fn(sample);
                if (isValidPayload(output)) {
                  return { found: true, name: candidate.name, type: candidate.type, validated: true };
                }
              } catch {
                // ignore and continue probing
              }
            }
          }

          if (allowBestEffort && candidates.length > 0) {
            const bestEffortCandidate = candidates.find((candidate) => candidate.name === 'ai')
              || candidates.find((candidate) => candidate.type === 'named_export')
              || candidates[0];

            return {
              found: true,
              name: bestEffortCandidate.name,
              type: bestEffortCandidate.type,
              validated: false,
              bestEffort: true
            };
          }

          return { found: false, validated: false };
        } catch (e) {
          return { found: false, error: e.message };
        }
      }, {
        url: appScriptUrl,
        sample: sampleEncryptedData,
        allowBestEffort: this.allowBestEffortCandidate && (!sampleProbe || sampleProbe.valid),
        candidateNames: bundleCandidateNames
      });

      if (!decryptFn || !decryptFn.found) {
        if (sampleEncryptedData) {
          this.logger.warn('app_script_candidate_rejected', {
            reason: 'sample_validation_failed'
          });
        }
        return null;
      }

      this.algorithmVersion = `app_${decryptFn.name}`;
      if (decryptFn.bestEffort) {
        this.logger.warn('app_script_best_effort_selected', {
          candidate: decryptFn.name,
          validated: false
        });
      }
      
      // 返回实际的解密函数包装器 (V11.0 FIX: 将参数包装成对象)
      const wrappedDecryptFn = async (encryptedData) => {
        return page.evaluate(async ({ url, fnName, data }) => {
          const mod = await import(url);
          const fn = fnName === 'default' ? mod.default : mod[fnName];
          return fn(data);
        }, { url: appScriptUrl, fnName: decryptFn.name, data: encryptedData });
      };
      wrappedDecryptFn.__validated = decryptFn.validated !== false;
      wrappedDecryptFn.__bestEffort = decryptFn.bestEffort === true;
      return wrappedDecryptFn;
    } catch (error) {
      this.logger.warn('app_script_extraction_failed', { error: error.message });
      return null;
    }
  }

  async _fetchBundleSource(page, appScriptUrl) {
    if (!page || typeof page.evaluate !== 'function' || !appScriptUrl) {
      return '';
    }

    try {
      return await page.evaluate(async (url) => {
        const response = await fetch(url, { credentials: 'include' });
        if (!response.ok) {
          return '';
        }
        return response.text();
      }, appScriptUrl);
    } catch (error) {
      this.logger.debug('app_script_bundle_fetch_failed', {
        traceId: this.traceId,
        error: error.message
      });
      return '';
    }
  }

  _extractFromBundle(bundleSource) {
    const text = String(bundleSource || '');
    if (!text) {
      return [];
    }

    const exportMap = this._parseBundleExportMap(text);
    if (exportMap.size === 0) {
      return [];
    }

    const candidates = [];
    for (const [alias, original] of exportMap.entries()) {
      const snippet = this._findBundleSnippet(text, original);
      const score = this._scoreBundleSnippet(alias, snippet);
      if (score > 0) {
        candidates.push({ alias, score });
      }
    }

    return candidates
      .sort((left, right) => right.score - left.score)
      .map((candidate) => candidate.alias);
  }

  _parseBundleExportMap(bundleSource) {
    const text = String(bundleSource || '');
    const exportBlock = text.match(/export\{([\s\S]+)\};\s*$/);
    if (!exportBlock) {
      return new Map();
    }

    const entries = exportBlock[1]
      .split(',')
      .map((entry) => entry.trim())
      .filter(Boolean);

    const exportMap = new Map();
    for (const entry of entries) {
      const match = entry.match(/^(\S+)\s+as\s+(\S+)$/);
      if (!match) {
        continue;
      }
      exportMap.set(match[2], match[1]);
    }

    return exportMap;
  }

  _findBundleSnippet(bundleSource, symbolName) {
    if (!bundleSource || !symbolName) {
      return '';
    }

    const markers = [
      `function ${symbolName}`,
      `const ${symbolName}=`,
      `const ${symbolName} =`,
      `let ${symbolName}=`,
      `let ${symbolName} =`
    ];

    for (const marker of markers) {
      const index = bundleSource.indexOf(marker);
      if (index >= 0) {
        return bundleSource.slice(index, index + 1600);
      }
    }

    return '';
  }

  _scoreBundleSnippet(alias, snippet) {
    const text = String(snippet || '');
    if (!text) {
      return 0;
    }

    let score = 0;
    if (/^ai$/i.test(alias)) score += 3;
    if (/atob\(/.test(text)) score += 5;
    if (/crypto/.test(text)) score += 5;
    if (/TextDecoder/.test(text)) score += 4;
    if (/TextEncoder/.test(text)) score += 2;
    if (/Uint8Array/.test(text)) score += 2;
    if (/importKey|deriveKey|decrypt/.test(text)) score += 6;
    if (/PBKDF2|AES-CBC|AES-GCM/.test(text)) score += 4;

    return score >= 8 ? score : 0;
  }

  /**
   * 从内联脚本提取解密函数
   * @private
   */
  async _extractFromInlineScripts(page) {
    try {
      // 查找包含解密逻辑的内联脚本
      const inlineDecryptor = await page.evaluate(() => {
        const scripts = Array.from(document.querySelectorAll('script:not([src])'));
        
        for (const script of scripts) {
          const text = script.textContent || '';
          
          // 查找典型的解密函数模式
          const patterns = [
            /function\s+(\w+)\s*\([^)]*\)\s*\{[^}]*(?:decrypt|decode|parse|unpack)/i,
            /const\s+(\w+)\s*=\s*\([^)]*\)\s*=>\s*\{[^}]*(?:decrypt|decode|parse|unpack)/i,
            /var\s+(\w+)\s*=\s*function\s*\([^)]*\)\s*\{[^}]*(?:decrypt|decode|parse|unpack)/i,
            /window\.(\w+)\s*=\s*function\s*\([^)]*\)/i,
            /window\['(\w+)'\]\s*=\s*function\s*\([^)]*\)/i
          ];
          
          for (const pattern of patterns) {
            const match = text.match(pattern);
            if (match) {
              return { 
                found: true, 
                fnName: match[1],
                context: 'inline'
              };
            }
          }
        }
        
        return { found: false };
      });

      if (!inlineDecryptor.found) {
        return null;
      }

      this.algorithmVersion = `inline_${inlineDecryptor.fnName}`;
      
      // 返回包装器函数
      return async (encryptedData) => {
        return page.evaluate((fnName, data) => {
          // 尝试从全局作用域调用
          const fn = window[fnName];
          if (typeof fn === 'function') {
            return fn(data);
          }
          throw new Error(`Decryptor function ${fnName} not found in global scope`);
        }, inlineDecryptor.fnName, encryptedData);
      };
    } catch (error) {
      this.logger.warn('inline_script_extraction_failed', { error: error.message });
      return null;
    }
  }

  /**
   * 从全局作用域提取解密函数
   * @private
   */
  async _extractFromGlobalScope(page) {
    try {
      const globalDecryptor = await page.evaluate(() => {
        // 常见的全局解密函数名
        const commonNames = [
          'decrypt', 'decode', 'parseData', 'unpack', 'transform',
          'ai', 'process', 'handle', 'convert', '__decrypt',
          'oddsDecrypt', 'dataParser', 'responseHandler', 'deserialize',
          'decodePayload', 'decryptPayload', 'decodeResponse'
        ];
        
        for (const name of commonNames) {
          if (typeof window[name] === 'function') {
            return { found: true, fnName: name };
          }
        }
        
        // 尝试查找任何可疑的全局函数
        for (const key of Object.keys(window)) {
          if (typeof window[key] === 'function' && 
              (key.toLowerCase().includes('decrypt') ||
               key.toLowerCase().includes('decode') ||
               key.toLowerCase().includes('parse'))) {
            return { found: true, fnName: key, detected: 'heuristic' };
          }
        }
        
        return { found: false };
      });

      if (!globalDecryptor.found) {
        return null;
      }

      this.algorithmVersion = `global_${globalDecryptor.fnName}`;
      
      return async (encryptedData) => {
        return page.evaluate((fnName, data) => {
          return window[fnName](data);
        }, globalDecryptor.fnName, encryptedData);
      };
    } catch (error) {
      this.logger.warn('global_scope_extraction_failed', { error: error.message });
      return null;
    }
  }

  /**
   * 解密数据
   * @param {string} encryptedData - 加密的数据
   * @returns {Promise<Object>} 解密后的数据
   */
  async decrypt(encryptedData) {
    if (!this.decryptFn) {
      throw new Error('Decryptor not initialized. Call extractDecryptor first.');
    }

    try {
      const cleanedData = this._cleanPayload(encryptedData);
      const payloadProbe = this._probeEncryptedPayload(cleanedData);
      if (!payloadProbe.valid) {
        const invalidPayloadError = new Error(payloadProbe.reason || 'INVALID_ENCRYPTED_PAYLOAD');
        invalidPayloadError.code = 'INVALID_ENCRYPTED_PAYLOAD';
        invalidPayloadError.payloadPreview = payloadProbe.preview || '';
        throw invalidPayloadError;
      }

      const result = await this.decryptFn(cleanedData);
      return result;
    } catch (error) {
      this.logger.error('[ReconDecryptor] 解密失败', { 
        traceId: this.traceId,
        error: error.message,
        code: error.code || null,
        payloadPreview: error.payloadPreview || null,
        algorithmVersion: this.algorithmVersion 
      });
      throw error;
    }
  }

  /**
   * 清洗加密 payload (修复 atob 错误)
   * @private
   */
  _cleanPayload(rawData) {
    if (!rawData || typeof rawData !== 'string') {
      return rawData;
    }

    // 移除首尾引号、转义符等
    let cleaned = rawData
      .replace(/^"|"$/g, '')
      .replace(/\\"/g, '"')
      .replace(/\\n/g, '')
      .replace(/\\r/g, '')
      .replace(/\\t/g, '')
      .replace(/\\/g, '')
      .trim();

    // 如果数据是 JSON 字符串格式（被引号包裹），尝试解析
    if (cleaned.startsWith('"') && cleaned.endsWith('"')) {
      try {
        cleaned = JSON.parse(cleaned);
      } catch {
        // 解析失败则保留原样
      }
    }

    // 移除所有非 Base64 字符（保留 Base64 合法字符: A-Z, a-z, 0-9, +, /, =）
    // 但首先检查是否是有效的 Base64
    const base64Pattern = /^[A-Za-z0-9+/=]+$/;
    if (!base64Pattern.test(cleaned)) {
      // 尝试提取 Base64 部分
      const base64Match = cleaned.match(/([A-Za-z0-9+/]{100,}={0,2})/);
      if (base64Match) {
        cleaned = base64Match[1];
      }
    }

    return cleaned;
  }

  _probeEncryptedPayload(cleanedData) {
    if (!cleanedData || typeof cleanedData !== 'string') {
      return {
        valid: false,
        reason: 'INVALID_ENCRYPTED_PAYLOAD',
        preview: ''
      };
    }

    const preview = cleanedData.slice(0, 120);
    if (/^URL:|^Status:|<html|<!doctype|not found|forbidden/i.test(cleanedData)) {
      return {
        valid: false,
        reason: 'INVALID_ENCRYPTED_PAYLOAD',
        preview
      };
    }

    try {
      const decoded = Buffer.from(cleanedData, 'base64').toString('utf8');
      const separatorIndex = decoded.indexOf(':');
      if (separatorIndex <= 0 || separatorIndex >= decoded.length - 1) {
        return {
          valid: false,
          reason: 'INVALID_ENCRYPTED_PAYLOAD',
          preview
        };
      }

      const ivSegment = decoded.slice(separatorIndex + 1).trim();
      if (!/^[a-f0-9]+$/i.test(ivSegment) || ivSegment.length % 2 !== 0) {
        return {
          valid: false,
          reason: 'INVALID_ENCRYPTED_PAYLOAD',
          preview
        };
      }

      return {
        valid: true,
        reason: null,
        preview
      };
    } catch {
      return {
        valid: false,
        reason: 'INVALID_ENCRYPTED_PAYLOAD',
        preview
      };
    }
  }

  /**
   * 获取当前算法版本
   * @returns {string|null}
   */
  getAlgorithmVersion() {
    return this.algorithmVersion;
  }

  /**
   * 预检解密能力
   * @param {Page} page
   * @returns {Promise<boolean>}
   */
  async canDecrypt(page) {
    try {
      const fn = await this.extractDecryptor(page);
      return fn !== null;
    } catch {
      return false;
    }
  }
}

module.exports = { ReconDecryptor };
