/* eslint-disable complexity, max-lines */
/**
 * @file FotMobExtractor - FotMob 网页数据提取器
 * @module infrastructure/services/FotMobExtractor
 * @version V6.7.5-EXTRACTOR
 * @description
 * 职责: 从 FotMob 网页提取比赛数据
 * 包含: __NEXT_DATA__ 提取、DOM 扫描、数据路径嗅探
 * 从 DiscoveryService 解耦，专注数据提取逻辑
 */

'use strict';

/**
 * FotMob 数据提取器
 * @class FotMobExtractor
 */
class FotMobExtractor {
  /**
   * 创建提取器实例
   * @param {Object} options - 配置选项
   * @param {Object} options.logger - 日志对象
   * @param {BrowserProvider} options.browserProvider - 浏览器提供者
   * @param {Function} options.makeStealthRequest - 隐身请求函数
   * @param {NetworkInterceptor} options.networkInterceptor - 网络拦截器
   */
  constructor(options = {}) {
    this.logger = options.logger || {
      info: () => {},
      warn: () => {},
      error: () => {}
    };
    this.browserProvider = options.browserProvider;
    this.makeStealthRequest = options.makeStealthRequest;
    this.networkInterceptor = options.networkInterceptor;
  }

  /**
   * 从网页 __NEXT_DATA__ 提取数据 (V6.7.8-DEEP-SCROLL: 强制滚动全量抽取)
   * @param {number} leagueId - 联赛 ID
   * @param {string} season - 赛季
   * @returns {Promise<Object>} 提取的数据
   */
  async extractFromWebpage(leagueId, season, options = {}) {
    this.logger.info(`[HOUND-SOUL] 🔮 启动深耕犁模式 (强制滚动全量抽取)...`);
    const expectedLeagueId = Number(options.expectedLeagueId || leagueId);
    
    // 🔥 V6.7.8: 访问 /fixtures/ 赛程专页
    const webpageUrl = `https://www.fotmob.com/leagues/${leagueId}/fixtures/${season}`;
    this.logger.info(`[HOUND-SOUL] 🌐 访问赛程专页: ${webpageUrl}`);
    
    try {
      // 导航到赛程专页
      await this.browserProvider.goto(webpageUrl, { 
        waitUntil: 'domcontentloaded', 
        timeout: 20000 
      });
      
      // 等待初始内容加载
      await this.browserProvider.sleep(2000);
      
      // 🔥 V6.7.8: 强制滚动触发懒加载
      this.logger.info(`[HOUND-SOUL] 📜 开始强制滚动，触发全量数据加载...`);
      
      let previousHeight = 0;
      let scrollAttempts = 0;
      const maxScrolls = 10;
      
      while (scrollAttempts < maxScrolls) {
        // 获取当前页面高度
        const currentHeight = await this.browserProvider.getPageHeight();
        
        // 滚动到底部
        await this.browserProvider.scroll({ to: 'bottom' });
        
        // 等待懒加载
        await this.browserProvider.sleep(800);
        
        // 检查是否有新内容加载
        const newHeight = await this.browserProvider.getPageHeight();
        
        if (newHeight === currentHeight && scrollAttempts > 3) {
          // 页面高度不再增加，认为已加载完成
          this.logger.info(`[HOUND-SOUL] ✅ 滚动完成，页面高度稳定: ${newHeight}px`);
          break;
        }
        
        scrollAttempts++;
        this.logger.info(`[HOUND-SOUL] 📜 滚动 ${scrollAttempts}/${maxScrolls} - 高度: ${currentHeight} -> ${newHeight}`);
      }
      
      // 回到顶部，确保所有数据正确渲染
      await this.browserProvider.scroll({ to: 'top' });
      await this.browserProvider.sleep(500);
      
      // 等待 __NEXT_DATA__ 元素出现
      await this.browserProvider.waitForSelector('#__NEXT_DATA__', { 
        state: 'attached', 
        timeout: 10000 
      });
      
      // 提取 JSON 数据
      const nextData = await this.browserProvider.evaluate(() => {
        const element = document.getElementById('__NEXT_DATA__');
        if (!element) return null;
        
        try {
          const jsonText = element.innerHTML || element.textContent;
          return JSON.parse(jsonText);
        } catch (e) {
          return { error: e.message };
        }
      });
      
      if (!nextData) {
        throw new Error('未找到 __NEXT_DATA__ 元素');
      }
      
      if (nextData.error) {
        throw new Error(`JSON 解析错误: ${nextData.error}`);
      }
      
      // 🔥 数据提取逻辑
      const pageProps = nextData.props?.pageProps;
      let extractedData = null;
      let matchCount = 0;
      
      // 路径 1: fallback 中的联赛数据
      const fallback = pageProps?.fallback;
      if (fallback && typeof fallback === 'object') {
        const leagueKey = Object.keys(fallback).find(key => 
          key.includes('/api/leagues') || key.includes('leagues')
        );
        
        if (leagueKey && fallback[leagueKey]) {
          extractedData = fallback[leagueKey];
          matchCount = this._countMatches(extractedData);
          this.logger.info(`[HOUND-SOUL] ✅ 从 fallback["${leagueKey}"] 提取 ${matchCount} 场数据`);
        }
      }
      
      // 路径 2: 直接从 pageProps 提取
      if (!extractedData && pageProps) {
        if (pageProps.fixtures || pageProps.allMatches) {
          extractedData = {
            fixtures: pageProps.fixtures || pageProps.allMatches,
            leagueId: leagueId,
            season: season,
            ...pageProps
          };
          matchCount = this._countMatches(extractedData);
          this.logger.info(`[HOUND-SOUL] ✅ 从 pageProps 提取 ${matchCount} 场数据`);
        }
      }
      
      // 🔥 V6.7.9: 如果数据量不足，尝试使用捕获的真实 API 端点
      if (!extractedData || matchCount < 200) {
        this.logger.warn(`[HOUND-SOUL] ⚠️  数据量不足 (${matchCount} 场)，尝试使用捕获的 API...`);
        
        // 使用 NetworkInterceptor 获取捕获的 API
        const capturedLeagueApi = this.networkInterceptor?.getFirstLeagueApi();
        
        if (capturedLeagueApi && this.makeStealthRequest) {
          this.logger.info(`[HOUND-INTERCEPT] 🎯 使用捕获的端点: ${capturedLeagueApi}`);
          try {
            const interceptedData = await this.makeStealthRequest(capturedLeagueApi, {
              expectedLeagueId
            });
            if (interceptedData && this._countMatches(interceptedData) > matchCount) {
              const interceptedCount = this._countMatches(interceptedData);
              this.logger.info(`[HOUND-INTERCEPT] ✅ 拦截端点返回 ${interceptedCount} 场数据`);
              return interceptedData;
            }
          } catch (e) {
            this.logger.warn(`[HOUND-INTERCEPT] ⚠️  拦截端点请求失败: ${e.message}`);
          }
        }
        
        // 备选: DOM 扫描
        this.logger.warn(`[HOUND-SOUL] ⚠️  尝试 DOM 扫描...`);
        const domData = await this.scanDOMForMatches();
        
        if (domData && domData.length > matchCount) {
          this.logger.info(`[HOUND-SOUL] ✅ DOM 扫描发现 ${domData.length} 场，覆盖原有数据`);
          return {
            fixtures: { allMatches: domData },
            leagueId: leagueId,
            season: season,
            _source: 'dom_scan'
          };
        }
      }
      
      if (extractedData) {
        return extractedData;
      }
      
      throw new Error('无法从 __NEXT_DATA__ 定位联赛数据');
      
    } catch (error) {
      this.logger.error(`[HOUND-SOUL] ❌ 灵魂抽取失败: ${error.message}`);
      throw error;
    }
  }

  /**
   * 统计数据结构中的比赛数量
   * @private
   */
  _countMatches(data) {
    if (!data) return 0;
    
    // 检查各种可能的数据结构
    if (data.fixtures?.allMatches && Array.isArray(data.fixtures.allMatches)) {
      return data.fixtures.allMatches.length;
    }
    if (Array.isArray(data.fixtures)) {
      return data.fixtures.length;
    }
    if (data.allMatches && Array.isArray(data.allMatches)) {
      return data.allMatches.length;
    }
    if (data.matches && Array.isArray(data.matches)) {
      return data.matches.length;
    }
    if (data.weeksWithMatches && Array.isArray(data.weeksWithMatches)) {
      return data.weeksWithMatches.reduce((sum, w) => sum + (w.matches?.length || 0), 0);
    }
    
    return 0;
  }

  /**
   * DOM 扫描：从页面直接提取比赛数据 (V6.7.8 备选方案)
   * @returns {Promise<Array>} 比赛数据数组
   */
  async scanDOMForMatches() {
    this.logger.info(`[HOUND-SOUL] 🔍 启动 DOM 扫描...`);
    
    try {
      const matches = await this.browserProvider.evaluate(() => {
        const results = [];
        const seenIds = new Set();
        
        // 扫描所有可能包含比赛数据的元素
        // FotMob 通常使用 data-match-id 属性或特定类名
        const selectors = [
          '[data-match-id]',
          '[data-id]',
          'a[href*="/matches/"]',
          'a[href*="/match/"]'
        ];
        
        for (const selector of selectors) {
          const elements = document.querySelectorAll(selector);
          
          elements.forEach(el => {
            // 提取 match ID
            const matchId = el.getAttribute('data-match-id') || 
                           el.getAttribute('data-id') ||
                           el.href?.match(/\/match(?:es)?\/(\d+)/)?.[1];
            
            if (!matchId || seenIds.has(matchId)) return;
            seenIds.add(matchId);
            
            // 提取球队信息
            const text = el.innerText || el.textContent || '';
            const teamNames = text.match(/([\u4e00-\u9fa5a-zA-Z\s]+)/g) || [];
            
            if (teamNames.length >= 2) {
              results.push({
                id: parseInt(matchId),
                home: { name: teamNames[0].trim() },
                away: { name: teamNames[1].trim() },
                status: { utcTime: null }
              });
            }
          });
        }
        
        return results;
      });
      
      this.logger.info(`[HOUND-SOUL] ✅ DOM 扫描完成，发现 ${matches.length} 场比赛`);
      return matches;

    } catch (error) {
      this.logger.error(`[HOUND-SOUL] ❌ DOM 扫描失败: ${error.message}`);
      return [];
    }
  }

  /**
   * 通过 DOM 交互模拟搜索框输入 (V6.7.6-FINAL: 从 titan_discovery.js 迁移)
   * @param {string} term - 搜索关键词
   * @returns {Promise<Object>} 搜索结果 { leagues: [], teams: [] }
   */
  async searchViaDOM(term) {
    this.logger.info(`[Extractor] 🔮 尝试 DOM 交互搜索: "${term}"`);

    // 确保浏览器已初始化
    if (!this.browserProvider.isInitialized()) {
      await this.browserProvider.initialize();
    }

    const page = await this.browserProvider.getPage();

    // 访问首页
    await this.browserProvider.goto('https://www.fotmob.com/', {
      waitUntil: 'domcontentloaded',
      timeout: 20000
    });

    // 等待搜索框出现
    await page.waitForSelector('input[type="search"], input[placeholder*="search" i], input[placeholder*="搜索" i]', {
      timeout: 10000
    });

    // 聚焦并输入搜索词
    const searchInput = await page.$('input[type="search"], input[placeholder*="search" i], input[placeholder*="搜索" i]');
    if (!searchInput) {
      throw new Error('未找到搜索框元素');
    }

    await searchInput.click();
    await searchInput.fill(term);

    this.logger.info(`[Extractor] ⌨️  已输入搜索词: "${term}"`);

    // 等待下拉结果出现
    await page.waitForTimeout(1500);

    // 提取搜索结果
    const results = await page.evaluate(() => {
      const data = { leagues: [], teams: [] };

      // 查找所有可能的搜索结果链接
      const links = document.querySelectorAll('a[href*="/leagues/"], a[href*="/teams/"]');

      links.forEach(link => {
        const href = link.getAttribute('href') || '';
        const text = link.innerText || link.textContent || '';
        const id = href.match(/\/(?:leagues|teams)\/(\d+)/)?.[1];

        if (!id) return;

        // 提取国家/地区信息
        const parent = link.closest('div, li, a');
        const countryText = parent?.innerText?.replace(text, '').trim() || '';

        if (href.includes('/leagues/')) {
          data.leagues.push({
            id: parseInt(id),
            name: text.trim(),
            country: countryText || 'Unknown',
            pageUrl: href
          });
        } else if (href.includes('/teams/')) {
          data.teams.push({
            id: parseInt(id),
            name: text.trim(),
            country: countryText || 'Unknown',
            pageUrl: href
          });
        }
      });

      return data;
    });

    // 去重
    const uniqueLeagues = [];
    const seenLeagues = new Set();
    results.leagues.forEach(l => {
      if (!seenLeagues.has(l.id)) {
        seenLeagues.add(l.id);
        uniqueLeagues.push(l);
      }
    });

    const uniqueTeams = [];
    const seenTeams = new Set();
    results.teams.forEach(t => {
      if (!seenTeams.has(t.id)) {
        seenTeams.add(t.id);
        uniqueTeams.push(t);
      }
    });

    if (uniqueLeagues.length === 0 && uniqueTeams.length === 0) {
      throw new Error('DOM 搜索未返回结果');
    }

    this.logger.info(`[Extractor] ✅ DOM 搜索成功: ${uniqueLeagues.length} 联赛, ${uniqueTeams.length} 球队`);

    return { leagues: uniqueLeagues, teams: uniqueTeams };
  }
}

module.exports = { FotMobExtractor };
