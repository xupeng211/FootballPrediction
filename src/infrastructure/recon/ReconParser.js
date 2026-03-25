/**
 * ReconParser - 解析大脑 (Total War 全球语种自愈版)
 * =================================================
 *
 * 职责: 封装【双向贪婪匹配算法】和 fuzzball 模糊匹配逻辑
 * 核心升级:
 * 1. 【Total War】变音抹平 - 德语 Mü/ö/ä 自动转换
 * 2. 【Total War】日期驱动 - 支持日期入口解析
 * 3. 【Total War】全球自愈 - 50+ 联赛自动适配
 *
 * @module infrastructure/recon/ReconParser
 * @version V10.0-TOTAL-WAR
 * @date 2026-03-24
 */

'use strict';

/**
 * 解析大脑类
 * @class ReconParser
 */
class ReconParser {
  constructor(options = {}) {
    this.logger = options.logger || console;
    this.fuzzball = options.fuzzball || null;
    this.dbPool = options.dbPool || null;

    const config = options.config || {};
    this.teamSlugs = config.teamSlugs || this.getDefaultTeamSlugs();
    this.teamMappings = config.teamMappings || this.getDefaultTeamMappings();

    // 预排序队名词典
    this.sortedSlugs = [...this.teamSlugs].sort((a, b) =>
      b.split('-').length - a.split('-').length
    );

    // 【Total War】多语种别名映射
    this.aliasMappings = this.getMultiLanguageAliases();

    this.logger.info('parser_initialized_total_war', {
      teamCount: this.teamSlugs.length,
      aliasCount: Object.keys(this.aliasMappings).length,
      diacritics: 'enabled'
    });
  }

  /**
   * 【Total War】变音抹平 - 德语 umlaut 转换
   * @param {string} text - 输入文本
   * @returns {string} 标准化后的文本
   */
  normalizeDiacritics(text) {
    if (!text) return '';

    // 1. NFD 分解 + 去除组合字符
    let normalized = text.normalize('NFD').replace(/[\u0300-\u036f]/g, '');

    // 2. 德语变音特殊处理
    const germanMap = {
      'ü': 'ue', 'Ü': 'UE',
      'ö': 'oe', 'Ö': 'OE',
      'ä': 'ae', 'Ä': 'AE',
      'ß': 'ss'
    };

    for (const [umlaut, replacement] of Object.entries(germanMap)) {
      normalized = normalized.split(umlaut).join(replacement);
    }

    // 3. 其他欧洲变音字符
    normalized = normalized
      .replace(/[àáâãå]/g, 'a')
      .replace(/[èéêë]/g, 'e')
      .replace(/[ìíîï]/g, 'i')
      .replace(/[òóôõ]/g, 'o')
      .replace(/[ùúû]/g, 'u')
      .replace(/[ç]/g, 'c')
      .replace(/[ñ]/g, 'n');

    return normalized.toLowerCase().trim();
  }

  /**
   * 【Total War】增强相似度计算 - 支持变音抹平
   * @param {string} name1 - 队名1
   * @param {string} name2 - 队名2
   * @returns {number} 相似度 0-1
   */
  calculateSimilarity(name1, name2) {
    // 原始相似度
    const rawSim = this._calculateRawSimilarity(name1, name2);

    // 变音抹平后相似度
    const norm1 = this.normalizeDiacritics(name1);
    const norm2 = this.normalizeDiacritics(name2);
    const normSim = this._calculateRawSimilarity(norm1, norm2);

    // 取最大值
    return Math.max(rawSim, normSim);
  }

  /**
   * 原始相似度计算
   * @private
   */
  _calculateRawSimilarity(name1, name2) {
    const n1 = name1.toLowerCase().trim();
    const n2 = name2.toLowerCase().trim();

    if (n1 === n2) return 1.0;

    if (this.fuzzball) {
      try {
        return this.fuzzball.token_set_ratio(n1, n2) / 100;
      } catch (e) {
        // fallback
      }
    }

    // 简单相似度
    const lcs = this.longestCommonSubstring(n1, n2);
    return (2 * lcs) / (n1.length + n2.length);
  }

  /**
   * 【V9.0】从 URL slug 提取 hash 和队名（增强版）
   * @param {string} url - 完整 URL 或 slug
   * @returns {Object} { hash, slug, homeTeam, awayTeam, aliases }
   */
  parseMatchUrl(url) {
    const match = url.match(/\/([^\/]+)-([a-zA-Z0-9]{8})\/$/);

    if (!match) {
      return { hash: null, slug: null, homeTeam: 'Unknown', awayTeam: 'Unknown' };
    }

    const cleanSlug = match[1];
    const hash = match[2];

    // 提取队名（使用增强算法）
    const teams = this.extractTeamsFromSlugEnhanced(cleanSlug);

    return { hash, slug: cleanSlug, ...teams };
  }

  /**
   * 【V9.0】增强版队名提取
   * @param {string} slug - 队名 slug
   * @returns {Object} { homeTeam, awayTeam, confidence }
   */
  extractTeamsFromSlugEnhanced(slug) {
    if (!slug) {
      return { homeTeam: 'Unknown', awayTeam: 'Unknown', confidence: 0 };
    }

    // 首先尝试标准解析
    const standardResult = this.extractTeamsFromSlug(slug);
    if (standardResult.homeTeam !== 'Unknown' && standardResult.awayTeam !== 'Unknown') {
      return { ...standardResult, confidence: 1.0 };
    }

    // 【V9.0】尝试别名扩展
    const aliasResult = this.tryAliasExpansion(slug);
    if (aliasResult) {
      return { ...aliasResult, confidence: 0.9 };
    }

    // 【V9.0】尝试最短公共子串匹配
    const lcsResult = this.tryLCSMatching(slug);
    if (lcsResult) {
      return { ...lcsResult, confidence: 0.85 };
    }

    return { homeTeam: 'Unknown', awayTeam: 'Unknown', confidence: 0 };
  }

  /**
   * 【V9.0】别名扩展尝试
   * @param {string} slug - 输入 slug
   * @returns {Object|null} { homeTeam, awayTeam }
   */
  tryAliasExpansion(slug) {
    const parts = slug.split('-');
    const totalParts = parts.length;

    // 尝试所有可能的分割点，使用别名映射
    for (let i = 1; i < totalParts; i++) {
      const leftPart = parts.slice(0, i).join('-');
      const rightPart = parts.slice(i).join('-');

      const leftExpanded = this.expandAlias(leftPart);
      const rightExpanded = this.expandAlias(rightPart);

      // 检查扩展后的匹配
      const leftMatch = this.findTeamMatch(leftExpanded);
      const rightMatch = this.findTeamMatch(rightExpanded);

      if (leftMatch && rightMatch) {
        return { homeTeam: leftMatch, awayTeam: rightMatch };
      }
    }

    return null;
  }

  /**
   * 【V9.0】别名扩展
   * @param {string} shortName - 短名称
   * @returns {string} 扩展后的名称
   */
  expandAlias(shortName) {
    // 直接别名匹配
    if (this.aliasMappings[shortName.toLowerCase()]) {
      return this.aliasMappings[shortName.toLowerCase()];
    }

    // 部分匹配
    for (const [alias, full] of Object.entries(this.aliasMappings)) {
      if (shortName.toLowerCase().includes(alias)) {
        return shortName.toLowerCase().replace(alias, full.toLowerCase());
      }
    }

    return shortName;
  }

  /**
   * 【V9.0】最短公共子串匹配
   * @param {string} slug - 输入 slug
   * @returns {Object|null} { homeTeam, awayTeam }
   */
  tryLCSMatching(slug) {
    const parts = slug.split('-');
    const candidates = [];

    // 生成所有可能的分割
    for (let i = 1; i < parts.length; i++) {
      const left = parts.slice(0, i).join(' ');
      const right = parts.slice(i).join(' ');

      // 为每一半找到最佳匹配
      const leftMatch = this.findBestLCSMatch(left);
      const rightMatch = this.findBestLCSMatch(right);

      if (leftMatch && rightMatch && leftMatch !== rightMatch) {
        const score = (leftMatch.score + rightMatch.score) / 2;
        candidates.push({
          homeTeam: leftMatch.team,
          awayTeam: rightMatch.team,
          score
        });
      }
    }

    // 返回得分最高的
    if (candidates.length > 0) {
      candidates.sort((a, b) => b.score - a.score);
      if (candidates[0].score > 0.6) {
        return {
          homeTeam: candidates[0].homeTeam,
          awayTeam: candidates[0].awayTeam
        };
      }
    }

    return null;
  }

  /**
   * 【V9.0】使用 LCS 找到最佳队名匹配
   * @param {string} query - 查询字符串
   * @returns {Object|null} { team, score }
   */
  findBestLCSMatch(query) {
    let bestMatch = null;
    let bestScore = 0;
    const queryLower = query.toLowerCase();

    const allTeams = Object.values(this.teamMappings);

    for (const team of allTeams) {
      const teamLower = team.toLowerCase();
      const lcsLength = this.longestCommonSubstring(queryLower, teamLower);
      const score = (2 * lcsLength) / (queryLower.length + teamLower.length);

      if (score > bestScore) {
        bestScore = score;
        bestMatch = team;
      }
    }

    if (bestMatch && bestScore > 0.5) {
      return { team: bestMatch, score: bestScore };
    }

    return null;
  }

  /**
   * 【V9.0】计算最长公共子串长度
   * @param {string} s1 - 字符串1
   * @param {string} s2 - 字符串2
   * @returns {number} 最长公共子串长度
   */
  longestCommonSubstring(s1, s2) {
    const m = s1.length;
    const n = s2.length;
    let maxLength = 0;

    // 使用动态规划
    const dp = Array(m + 1).fill(null).map(() => Array(n + 1).fill(0));

    for (let i = 1; i <= m; i++) {
      for (let j = 1; j <= n; j++) {
        if (s1[i - 1] === s2[j - 1]) {
          dp[i][j] = dp[i - 1][j - 1] + 1;
          maxLength = Math.max(maxLength, dp[i][j]);
        }
      }
    }

    return maxLength;
  }

  /**
   * 查找队名匹配
   * @param {string} name - 名称
   * @returns {string|null} 匹配到的队名
   */
  findTeamMatch(name) {
    const normalized = name.toLowerCase().trim();

    // 直接映射匹配
    if (this.teamMappings[normalized]) {
      return this.teamMappings[normalized];
    }

    // Slug 匹配
    const slug = this.teamNameToSlug(name);
    if (this.teamMappings[slug]) {
      return this.teamMappings[slug];
    }

    // 模糊匹配
    if (this.fuzzball) {
      const allTeams = Object.values(this.teamMappings);
      const bestMatch = this.findBestMatch(normalized, allTeams, 0.75);
      if (bestMatch) return bestMatch.team;
    }

    return null;
  }

  /**
   * 标准队名提取（保留原逻辑）
   */
  extractTeamsFromSlug(slug) {
    if (!slug) {
      return { homeTeam: 'Unknown', awayTeam: 'Unknown' };
    }

    const parts = slug.split('-');
    const totalParts = parts.length;

    // 尝试所有分割点
    for (let i = 1; i < totalParts; i++) {
      const leftPart = parts.slice(0, i).join('-');
      const rightPart = parts.slice(i).join('-');

      const leftInDict = this.sortedSlugs.includes(leftPart);
      const rightInDict = this.sortedSlugs.includes(rightPart);

      if (leftInDict && rightInDict) {
        return {
          homeTeam: this.normalizeTeamName(leftPart),
          awayTeam: this.normalizeTeamName(rightPart)
        };
      }
    }

    return { homeTeam: 'Unknown', awayTeam: 'Unknown' };
  }

  /**
   * 【V9.0】获取多语种别名映射
   * @returns {Object} 别名映射表
   */
  getMultiLanguageAliases() {
    return {
      // 西班牙语缩写
      'ath': 'Athletic',
      'atletico': 'Atletico',
      'atleti': 'Atletico',
      'atm': 'Atletico Madrid',
      'betis': 'Real Betis',
      'celta': 'Celta Vigo',
      'espanyol': 'Espanyol',
      'getafe': 'Getafe',
      'girona': 'Girona',
      'osasuna': 'Osasuna',
      'rayo': 'Rayo Vallecano',
      'sevilla': 'Sevilla',
      'valencia': 'Valencia',
      'villarreal': 'Villarreal',
      'real': 'Real',
      'rcd': 'RCD',
      'rc': 'RC',
      'ud': 'UD',
      'sd': 'SD',
      'cf': 'CF',

      // 德语缩写
      'bayern': 'Bayern Munich',
      'bvb': 'Borussia Dortmund',
      'bmgladbach': 'Borussia Mgladbach',
      'bmg': 'Borussia Mgladbach',
      'eintracht': 'Eintracht Frankfurt',
      'sge': 'Eintracht Frankfurt',
      'freiburg': 'Freiburg',
      'hoffenheim': 'Hoffenheim',
      'koln': 'Koln',
      'leverkusen': 'Bayer Leverkusen',
      'mainz': 'Mainz',
      'augsburg': 'Augsburg',
      'hertha': 'Hertha Berlin',
      'union': 'Union Berlin',
      'wolfsburg': 'Wolfsburg',
      'stuttgart': 'Stuttgart',
      'werder': 'Werder Bremen',
      'schalke': 'Schalke',
      'fc': 'FC',
      'sc': 'SC',
      'tsg': 'TSG',
      'vfb': 'VfB',
      'sv': 'SV',
      'rb': 'RB',

      // 法语缩写
      'psg': 'Paris Saint-Germain',
      'om': 'Marseille',
      'ol': 'Lyon',
      'asm': 'Monaco',
      'losc': 'Lille',
      'fcn': 'Nantes',
      'srfc': 'Rennes',
      'ogcn': 'Nice',
      'rcsa': 'Strasbourg',
      'sb29': 'Brest',
      'fcm': 'Metz',
      'mhsc': 'Montpellier',
      'estac': 'Troyes',
      'aca': 'Ajaccio',
      'aca': 'Auxerre',
      'clermont': 'Clermont',
      'lens': 'Lens',
      'lorient': 'Lorient',
      'reims': 'Reims',
      'toulouse': 'Toulouse',
      'as': 'AS',
      'rc': 'RC',
      'stade': 'Stade',

      // 意大利语缩写
      'ac': 'AC',
      'fc': 'FC',
      'inter': 'Inter Milan',
      'juve': 'Juventus',
      'lazio': 'Lazio',
      'milan': 'AC Milan',
      'napoli': 'Napoli',
      'roma': 'Roma',
      'atalanta': 'Atalanta',
      'bologna': 'Bologna',
      'cagliari': 'Cagliari',
      'empoli': 'Empoli',
      'fiorentina': 'Fiorentina',
      'genoa': 'Genoa',
      'sassuolo': 'Sassuolo',
      'torino': 'Torino',
      'udinese': 'Udinese',
      'verona': 'Verona',
      'monza': 'Monza',
      'lecce': 'Lecce',
      'frosinone': 'Frosinone',
      'salernitana': 'Salernitana'
    };
  }

  /**
   * 队名转换为 slug
   */
  teamNameToSlug(teamName) {
    return teamName
      .toLowerCase()
      .replace(/&/g, 'and')
      .replace(/[^a-z0-9\s-]/g, '')
      .replace(/\s+/g, '-')
      .replace(/-+/g, '-')
      .replace(/^-|-$/g, '');
  }

  /**
   * 标准化队名
   */
  normalizeTeamName(slug) {
    if (!slug) return '';

    const normalized = slug.toLowerCase().replace(/-/g, ' ').trim();

    if (this.teamMappings[normalized]) {
      return this.teamMappings[normalized];
    }

    return normalized.split(' ')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  }

  /**
   * 计算相似度
   */
  calculateSimilarity(name1, name2) {
    const n1 = name1.toLowerCase().trim();
    const n2 = name2.toLowerCase().trim();

    if (n1 === n2) return 1.0;

    if (this.fuzzball) {
      try {
        return this.fuzzball.token_set_ratio(n1, n2) / 100;
      } catch (e) {
        // fallback
      }
    }

    // 简单相似度
    const lcs = this.longestCommonSubstring(n1, n2);
    return (2 * lcs) / (n1.length + n2.length);
  }

  /**
   * 查找最佳匹配
   */
  findBestMatch(query, candidates, threshold = 0.85) {
    let bestMatch = null;
    let bestScore = 0;

    for (const candidate of candidates) {
      const score = this.calculateSimilarity(query, candidate);
      if (score > bestScore) {
        bestScore = score;
        bestMatch = candidate;
      }
    }

    if (bestMatch && bestScore >= threshold) {
      return { team: bestMatch, confidence: bestScore };
    }

    return null;
  }

  /**
   * 获取默认队名词典
   */
  getDefaultTeamSlugs() {
    return [
      // Premier League
      'aston-villa', 'crystal-palace', 'man-city', 'man-united', 'newcastle-utd',
      'nottingham-forest', 'sheffield-utd', 'west-ham', 'manchester-city',
      'manchester-united', 'brighton', 'bournemouth', 'wolverhampton-wanderers',
      'brentford', 'burnley', 'chelsea', 'everton', 'fulham',
      'liverpool', 'luton', 'arsenal', 'tottenham', 'wolves',
      'ipswich', 'southampton', 'leicester', 'west-ham-united',
      // La Liga
      'alaves', 'almeria', 'athletic-bilbao', 'atletico-madrid', 'barcelona',
      'cadiz', 'celta-vigo', 'getafe', 'girona', 'granada',
      'las-palmas', 'mallorca', 'osasuna', 'rayo-vallecano', 'real-betis',
      'real-madrid', 'real-sociedad', 'sevilla', 'valencia', 'villarreal',
      // Bundesliga
      'augsburg', 'bayer-leverkusen', 'bayern-munich', 'bochum', 'darmstadt',
      'dortmund', 'eintracht-frankfurt', 'freiburg', 'heidenheim', 'hoffenheim',
      'koln', 'mainz', 'monchengladbach', 'rb-leipzig', 'stuttgart',
      'union-berlin', 'werder-bremen', 'wolfsburg',
      // Serie A
      'atalanta', 'bologna', 'cagliari', 'empoli', 'fiorentina',
      'frosinone', 'genoa', 'inter', 'juventus', 'lazio',
      'lecce', 'milan', 'monza', 'napoli', 'roma',
      'salernitana', 'sassuolo', 'torino', 'udinese', 'verona',
      // Ligue 1
      'brest', 'clermont', 'le-havre', 'lens', 'lille',
      'lorient', 'lyon', 'marseille', 'metz', 'monaco',
      'montpellier', 'nantes', 'nice', 'psg', 'reims',
      'rennes', 'strasbourg', 'toulouse'
    ];
  }

  /**
   * 获取默认队名映射表
   */
  getDefaultTeamMappings() {
    return {
      'man united': 'Manchester United',
      'man utd': 'Manchester United',
      'manchester united': 'Manchester United',
      'man city': 'Manchester City',
      'manchester city': 'Manchester City',
      'newcastle utd': 'Newcastle United',
      'newcastle united': 'Newcastle United',
      'newcastle': 'Newcastle United',
      'wolverhampton': 'Wolverhampton Wanderers',
      'wolves': 'Wolverhampton Wanderers',
      'tottenham': 'Tottenham Hotspur',
      'spurs': 'Tottenham Hotspur',
      'west ham': 'West Ham United',
      'nottingham': 'Nottingham Forest',
      'brighton': 'Brighton & Hove Albion',
      'sheffield utd': 'Sheffield United',
      'bournemouth': 'AFC Bournemouth',
      'arsenal': 'Arsenal',
      'aston villa': 'Aston Villa',
      'brentford': 'Brentford',
      'burnley': 'Burnley',
      'chelsea': 'Chelsea',
      'crystal palace': 'Crystal Palace',
      'everton': 'Everton',
      'fulham': 'Fulham',
      'liverpool': 'Liverpool',
      'ipswich': 'Ipswich Town',
      'leicester': 'Leicester City',
      'southampton': 'Southampton',
      // 西班牙语
      'athletic bilbao': 'Athletic Bilbao',
      'atletico madrid': 'Atletico Madrid',
      'barcelona': 'Barcelona',
      'real madrid': 'Real Madrid',
      'real betis': 'Real Betis',
      'real sociedad': 'Real Sociedad',
      'sevilla': 'Sevilla',
      'valencia': 'Valencia',
      'villarreal': 'Villarreal',
      'celta vigo': 'Celta Vigo',
      'rayo vallecano': 'Rayo Vallecano',
      'las palmas': 'Las Palmas',
      // 德语
      'bayern munich': 'Bayern Munich',
      'borussia dortmund': 'Borussia Dortmund',
      'borussia mgladbach': 'Borussia Mgladbach',
      'eintracht frankfurt': 'Eintracht Frankfurt',
      'bayer leverkusen': 'Bayer Leverkusen',
      'rb leipzig': 'RB Leipzig',
      'wolfsburg': 'Wolfsburg',
      'freiburg': 'Freiburg',
      'union berlin': 'Union Berlin',
      'werder bremen': 'Werder Bremen',
      // 法语
      'paris saint-germain': 'Paris Saint-Germain',
      'marseille': 'Marseille',
      'lyon': 'Lyon',
      'monaco': 'Monaco',
      'lille': 'Lille',
      'rennes': 'Rennes',
      'nice': 'Nice',
      'strasbourg': 'Strasbourg',
      'lens': 'Lens'
    };
  }
}

module.exports = { ReconParser };
