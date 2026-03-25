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
    this.decryptFn = null;
    this.algorithmVersion = null;
  }

  /**
   * 从页面动态提取解密函数
   * @param {Page} page - Playwright Page 实例
   * @returns {Promise<Function>} 解密函数
   */
  async extractDecryptor(page) {
    if (!page) {
      throw new Error('Page instance required');
    }

    try {
      // 方法1: 尝试从 app-*.js 提取
      const decryptFn = await this._extractFromAppScript(page);
      if (decryptFn) {
        this.decryptFn = decryptFn; // V11.0 FIX: 保存解密函数
        this.logger.info('decryptor_extracted', { method: 'app_script', version: this.algorithmVersion });
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
  async _extractFromAppScript(page) {
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

      // 在页面上下文中动态导入并提取解密函数
      const decryptFn = await page.evaluate(async (url) => {
        try {
          const module = await import(url);
          
          // 动态查找解密函数（多种可能名称）
          const possibleNames = ['ai', 'decrypt', 'decode', 'parse', 'unpack', 'transform'];
          
          for (const name of possibleNames) {
            if (typeof module[name] === 'function') {
              return { found: true, name, type: 'named_export' };
            }
          }
          
          // 检查默认导出
          if (typeof module.default === 'function') {
            return { found: true, name: 'default', type: 'default_export' };
          }
          
          // 检查第一个函数导出
          for (const key of Object.keys(module)) {
            if (typeof module[key] === 'function') {
              return { found: true, name: key, type: 'auto_detected' };
            }
          }
          
          return { found: false };
        } catch (e) {
          return { found: false, error: e.message };
        }
      }, appScriptUrl);

      if (!decryptFn || !decryptFn.found) {
        return null;
      }

      this.algorithmVersion = `app_${decryptFn.name}`;
      
      // 返回实际的解密函数包装器 (V11.0 FIX: 将参数包装成对象)
      return async (encryptedData) => {
        return page.evaluate(async ({ url, fnName, data }) => {
          const mod = await import(url);
          const fn = fnName === 'default' ? mod.default : mod[fnName];
          return await fn(data);
        }, { url: appScriptUrl, fnName: decryptFn.name, data: encryptedData });
      };
    } catch (error) {
      this.logger.warn('app_script_extraction_failed', { error: error.message });
      return null;
    }
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
          'oddsDecrypt', 'dataParser', 'responseHandler'
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
      // V11.0 FIX: 清洗 payload，修复 atob 错误
      const cleanedData = this._cleanPayload(encryptedData);
      const result = await this.decryptFn(cleanedData);
      return result;
    } catch (error) {
      this.logger.error('decryption_failed', { 
        error: error.message,
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
      .trim();

    return cleaned;
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
