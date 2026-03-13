/**
 * FotMobStrategy - FotMob 数据收割策略
 * =====================================
 *
 * 专门处理 FotMob 网站的数据提取逻辑：
 * - 页面导航与请求拦截
 * - __NEXT_DATA__ 提取与 API 响应解析
 * - 数据转换与字段映射
 * - CSS 选择器定位（备用方案）
 *
 * @module infrastructure/harvesters/strategies/FotMobStrategy
 * @version V1.0.0
 */

'use strict';

const { transformToApiFormat } = require('../../../parsers/fotmob/NextDataParser');

// ============================================================================
// FotMobStrategy 类
// ============================================================================

class FotMobStrategy {
    /**
     * 创建 FotMob 收割策略
     * @param {Object} config - 配置选项
     */
    constructor(config = {}) {
        this.config = {
            verboseLogging: config.verboseLogging || false,
            ...config
        };

        // 请求拦截配置
        this.apiPatterns = [
            'matchfacts',
            'matchDetails'
        ];

        // 资源类型拦截黑名单
        this.blockedResourceTypes = ['image', 'media', 'font'];
    }

    /**
     * 获取目标 URL
     * @param {Object} match - 比赛信息
     * @param {string} match.external_id - 外部比赛 ID
     * @returns {string} 目标 URL
     */
    getTargetUrl(match) {
        const { external_id } = match;
        return `https://www.fotmob.com/match/${external_id}`;
    }

    /**
     * 检查错误是否由对象被回收导致（内存压力下的竞态条件）
     * @param {Error} error - 错误对象
     * @returns {boolean}
     * @private
     */
    _isObjectCollectedError(error) {
        if (!error || !error.message) return false;
        const msg = error.message.toLowerCase();
        return msg.includes('object collected') ||
               msg.includes('target closed') ||
               msg.includes('page closed') ||
               msg.includes('context closed') ||
               msg.includes('route is already handled') ||
               msg.includes('protocol error');
    }

    /**
     * 安全的 route 操作包装器
     * 捕获对象回收错误并抛出可重试异常
     * @param {Function} operation - route 操作函数
     * @param {string} operationName - 操作名称（用于日志）
     * @returns {Promise<void>}
     * @private
     */
    async _safeRouteOperation(operation, operationName = 'route') {
        try {
            await operation();
        } catch (error) {
            if (this._isObjectCollectedError(error)) {
                // 对象已被回收，抛出可重试错误
                const retryError = new Error(`RETRYABLE_RESOURCE_ERROR: ${operationName} failed - ${error.message}`);
                retryError.code = 'RETRYABLE_RESOURCE_ERROR';
                retryError.originalError = error;
                throw retryError;
            }
            // 其他错误继续抛出
            throw error;
        }
    }

    /**
     * 设置请求拦截
     * 拦截 API 请求并捕获响应数据
     * @param {import('playwright').Page} page - Playwright Page 对象
     * @returns {Promise<Object>} 拦截控制器
     */
    async setupRequestInterception(page) {
        const capturedData = {
            data: null,
            url: null,
            timestamp: null
        };

        await page.route('**/*', async (route) => {
            const url = route.request().url();
            const type = route.request().resourceType();

            // 拦截黑名单资源
            if (this.blockedResourceTypes.includes(type)) {
                await this._safeRouteOperation(() => route.abort(), 'abort');
                return;
            }

            // 拦截 API 请求
            const isApiRequest = this.apiPatterns.some(pattern => url.includes(pattern));

            if (isApiRequest) {
                if (this.config.verboseLogging) {
                    console.log(`[FotMobStrategy] 捕获 API 请求: ${url.slice(0, 100)}...`);
                }

                try {
                    const response = await route.fetch();
                    const body = await response.text();

                    if (this.config.verboseLogging) {
                        console.log(`[FotMobStrategy] 响应状态: ${response.status()}`);
                        console.log(`[FotMobStrategy] 响应体大小: ${body.length} 字节`);
                    }

                    try {
                        capturedData.data = JSON.parse(body);
                        capturedData.url = url;
                        capturedData.timestamp = new Date().toISOString();

                        if (this.config.verboseLogging) {
                            console.log(`[FotMobStrategy] JSON 解析成功`);
                        }
                    } catch (parseError) {
                        if (this.config.verboseLogging) {
                            console.log(`[FotMobStrategy] JSON 解析失败: ${parseError.message}`);
                        }
                    }

                    await this._safeRouteOperation(() => route.fulfill({ response }), 'fulfill');
                } catch (routeError) {
                    if (this.config.verboseLogging) {
                        console.log(`[FotMobStrategy] 请求失败: ${routeError.message}`);
                    }
                    // 如果已经是可重试错误，直接抛出
                    if (routeError.code === 'RETRYABLE_RESOURCE_ERROR') {
                        throw routeError;
                    }
                    // 否则尝试继续
                    await this._safeRouteOperation(() => route.continue(), 'continue');
                }
            } else {
                await this._safeRouteOperation(() => route.continue(), 'continue');
            }
        });

        return capturedData;
    }

    /**
     * 从页面提取数据
     * 优先从 API 拦截获取，失败则从 __NEXT_DATA__ 提取
     * @param {import('playwright').Page} page - Playwright Page 对象
     * @param {Object} match - 比赛信息
     * @param {Object} [interceptionData] - 请求拦截捕获的数据
     * @returns {Promise<Object>} 提取的比赛数据
     */
    async extractData(page, match, interceptionData = null) {
        // 优先使用拦截数据
        if (interceptionData && interceptionData.data) {
            if (this.config.verboseLogging) {
                console.log(`[FotMobStrategy] 使用 API 拦截数据`);
            }
            return this._normalizeData(interceptionData.data);
        }

        // 备用方案：从 __NEXT_DATA__ 提取
        if (this.config.verboseLogging) {
            console.log(`[FotMobStrategy] 尝试从 __NEXT_DATA__ 提取数据...`);
        }

        const nextData = await page.evaluate(() => {
            const script = document.getElementById('__NEXT_DATA__');
            return script ? JSON.parse(script.textContent) : null;
        });

        if (this.config.verboseLogging) {
            console.log(`[FotMobStrategy] nextData 存在: ${!!nextData}`);
            console.log(`[FotMobStrategy] nextData.props 存在: ${!!nextData?.props}`);
            console.log(`[FotMobStrategy] nextData.props.pageProps 存在: ${!!nextData?.props?.pageProps}`);
        }

        // V4.51.2: 备用方案 B - 从 DOM 提取基础数据
        if (!nextData) {
            console.log('[FotMobStrategy] __NEXT_DATA__ 缺失，尝试 DOM 提取...');

            const basicData = await page.evaluate(() => {
                // 尝试多种选择器提取比赛信息
                const title = document.querySelector('h1')?.textContent ||
                             document.querySelector('[data-testid="match-title"]')?.textContent ||
                             document.title || '';

                // 尝试提取队伍名称
                const homeTeam = document.querySelector('.home-team, [data-testid="home-team"]')?.textContent?.trim();
                const awayTeam = document.querySelector('.away-team, [data-testid="away-team"]')?.textContent?.trim();

                // 尝试从 title 解析 (格式: "Team A vs Team B - FotMob")
                let teams = [];
                if (title.includes(' vs ')) {
                    teams = title.split(' vs ').map(t => t.trim());
                } else if (title.includes(' - ')) {
                    const matchPart = title.split(' - ')[0];
                    if (matchPart.includes(' vs ')) {
                        teams = matchPart.split(' vs ').map(t => t.trim());
                    }
                }

                if ((homeTeam && awayTeam) || teams.length === 2) {
                    return {
                        general: {
                            homeTeam: { name: homeTeam || teams[0] },
                            awayTeam: { name: awayTeam || teams[1] },
                            matchStatus: 'UNKNOWN'
                        },
                        content: {
                            // 标记为 DOM 提取的基础数据
                            _domExtracted: true,
                            _extractionMethod: 'dom_fallback'
                        },
                        header: {
                            title: title
                        },
                        _source: 'fotmob_dom_fallback',
                        _extractedAt: new Date().toISOString()
                    };
                }

                return null;
            });

            if (basicData) {
                console.log('[FotMobStrategy] ✅ DOM 提取成功，返回基础数据');
                return this._normalizeData(basicData);
            }

            // 所有方案都失败，才抛出 NO_DATA
            throw new Error('NO_DATA:无法从页面提取数据');
        }

        const transformedData = transformToApiFormat(nextData);

        if (this.config.verboseLogging) {
            console.log(`[FotMobStrategy] transformedData 存在: ${!!transformedData}`);
            if (transformedData) {
                console.log(`[FotMobStrategy] capturedData keys: ${Object.keys(transformedData).join(', ')}`);
            }
        }

        return this._normalizeData(transformedData);
    }

    /**
     * 标准化数据格式
     * 确保返回的数据符合统一的 API 格式
     * @param {Object} data - 原始数据
     * @returns {Object} 标准化后的数据
     * @private
     */
    _normalizeData(data) {
        if (!data) {
            return null;
        }

        // 确保 content 字段存在
        if (!data.content) {
            data.content = {};
        }

        // 确保 general 字段存在
        if (!data.general) {
            data.general = {};
        }

        // 确保 header 字段存在
        if (!data.header) {
            data.header = {};
        }

        // 添加来源标记
        data._source = 'fotmob';
        data._extractedAt = new Date().toISOString();

        return data;
    }

    /**
     * 验证数据完整性
     * @param {Object} data - 提取的数据
     * @returns {Object} 验证结果 { valid: boolean, reason?: string, size: number }
     */
    validateData(data) {
        if (!data) {
            return { valid: false, reason: 'NULL_DATA', size: 0 };
        }

        const jsonStr = JSON.stringify(data);
        const size = jsonStr.length;

        // 检查数据体积
        const minSize = 1000;
        if (size < minSize) {
            return { valid: false, reason: 'SIZE_TOO_SMALL', size };
        }

        // 检查必需字段
        const hasContent = data.content !== undefined;
        const hasGeneral = data.general !== undefined;

        if (!hasContent) {
            return { valid: false, reason: 'MISSING_CONTENT', size };
        }

        return { valid: true, size, hasGeneral };
    }

    /**
     * 获取数据质量报告
     * @param {Object} data - 提取的数据
     * @returns {Object} 质量报告
     */
    getDataQualityReport(data) {
        if (!data) {
            return { score: 0, issues: ['无数据'] };
        }

        const issues = [];
        let score = 100;

        // 检查 content 结构
        if (!data.content) {
            issues.push('缺少 content 字段');
            score -= 30;
        } else {
            // 检查 lineup 数据
            if (!data.content.lineup) {
                issues.push('缺少 lineup 数据');
                score -= 20;
            }

            // 检查 stats 数据
            if (!data.content.stats) {
                issues.push('缺少 stats 数据');
                score -= 15;
            }
        }

        // 检查 general 信息
        if (!data.general) {
            issues.push('缺少 general 字段');
            score -= 10;
        }

        // 检查 header
        if (!data.header) {
            issues.push('缺少 header 字段');
            score -= 10;
        }

        return { score: Math.max(0, score), issues };
    }

    /**
     * 提取特定字段（便捷方法）
     * @param {Object} data - 完整数据
     * @param {string} fieldPath - 字段路径，如 'content.lineup.homeTeam'
     * @returns {any} 字段值
     */
    getField(data, fieldPath) {
        if (!data || !fieldPath) {
            return undefined;
        }

        const parts = fieldPath.split('.');
        let current = data;

        for (const part of parts) {
            if (current === null || current === undefined) {
                return undefined;
            }
            current = current[part];
        }

        return current;
    }

    /**
     * 提取比赛统计信息
     * @param {Object} data - 比赛数据
     * @returns {Object} 统计信息摘要
     */
    extractMatchStats(data) {
        const stats = {
            homeTeam: null,
            awayTeam: null,
            score: null,
            events: [],
            statistics: null
        };

        if (!data || !data.content) {
            return stats;
        }

        const { content, general, header } = data;

        // 球队信息
        if (content.lineup) {
            stats.homeTeam = content.lineup.homeTeam;
            stats.awayTeam = content.lineup.awayTeam;
        }

        // 比分
        if (header) {
            stats.score = {
                home: header.homeScore,
                away: header.awayScore
            };
        }

        // 事件
        if (content.events) {
            stats.events = content.events;
        }

        // 统计数据
        if (content.stats) {
            stats.statistics = content.stats;
        }

        return stats;
    }

    /**
     * 提取阵容与身价信息
     * @param {Object} data - 比赛数据
     * @returns {Object} 阵容信息
     */
    extractLineupInfo(data) {
        const lineup = {
            home: {
                formation: null,
                starters: [],
                subs: [],
                totalMarketValue: 0,
                coach: null
            },
            away: {
                formation: null,
                starters: [],
                subs: [],
                totalMarketValue: 0,
                coach: null
            }
        };

        if (!data || !data.content || !data.content.lineup) {
            return lineup;
        }

        const lineupData = data.content.lineup;

        // 主队阵容
        if (lineupData.homeTeam) {
            const home = lineupData.homeTeam;
            lineup.home.formation = home.formation;
            lineup.home.starters = home.starters || [];
            lineup.home.subs = home.subs || [];
            lineup.home.totalMarketValue = home.totalStarterMarketValue || 0;
            lineup.home.coach = home.coach;
        }

        // 客队阵容
        if (lineupData.awayTeam) {
            const away = lineupData.awayTeam;
            lineup.away.formation = away.formation;
            lineup.away.starters = away.starters || [];
            lineup.away.subs = away.subs || [];
            lineup.away.totalMarketValue = away.totalStarterMarketValue || 0;
            lineup.away.coach = away.coach;
        }

        return lineup;
    }
}

module.exports = { FotMobStrategy };
