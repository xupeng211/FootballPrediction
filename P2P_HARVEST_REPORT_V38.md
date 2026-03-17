# V38.3 点对点真实收割技术报告
## Point-to-Point Harvesting Technical Report

**日期**: 2026-03-17  
**版本**: V38.3-P2P-API  
**状态**: 技术验证阶段 - 发现数据访问限制

---

## ✅ 已完成工作

### 1. URL动态拼接引擎 (URL Builder)
- **实现文件**: `scripts/ops/p2p_harvest_v38.js`
- **功能**: 
  - 3场2023/24赛季真实英超比赛URL硬编码
    - Fulham vs Burnley (2024-05-11)
    - Brentford vs Wolves (2024-05-11)
    - Bournemouth vs Manchester United (2024-05-19)
  - URL哈希映射: `8EamNN8b`, `0jR7cwU6`, `QZ5U62OH`
  - 支持从数据库字段动态构建URL的扩展接口

### 2. Playwright API拦截引擎
- **技术栈**: Playwright + Chromium + 代理(172.25.16.1:7890)
- **功能**:
  - XHR/Fetch API请求拦截
  - 路由监听: `/odds`, `/feed`, `/ajax`, `/api`
  - JSON响应解析与博彩公司数据提取
  - DOM备选提取策略

### 3. 内存存储与查询系统
- **实现**: 内存存储替代PostgreSQL (psycopg2未安装)
- **Schema**: 
  ```sql
  match_odds (
    match_id, provider,
    odds_home_open, odds_draw_open, odds_away_open,
    odds_home_close, odds_draw_close, odds_away_close,
    odds_drop_home, odds_drop_draw, odds_drop_away,
    extracted_at
  )
  ```

---

## ⚠️ 发现的技术瓶颈

### 瓶颈1: OddsPortal历史数据访问限制
**现象**: 
- 页面HTTP 200成功加载 (HTML ~350KB)
- API请求成功拦截 (match-event, postmatch-score等)
- 但响应中**不包含赔率数据**

**根因分析**:
```
OddsPortal历史比赛页面需要以下条件才能显示完整赔率:
1. 用户登录状态 (Cookie/Session)
2. 特定地区IP (Geo-restriction)
3. 点击"Odds" Tab触发赔率API加载
```

**验证证据**:
- `pageVar` 变量包含博彩公司ID映射 (941, 911等)
- `match-event` API返回比赛事件数据，不含赔率
- HTML中无Bet365/Pinnacle文本内容

### 瓶颈2: 动态加载时序
**现象**:
- 初始页面加载后，赔率数据通过独立AJAX请求获取
- 需要用户交互(点击Odds Tab)触发赔率API
- API端点模式: `https://www.oddsportal.com/match-odds/...` (未触发)

---

## 🔧 技术实现细节

### 成功拦截的API端点
```
✅ /ajax-all-events/topEvents
✅ /feed/postmatch-score/1-{hash}-y...
✅ /ajax-event-match-facts/{hash}/K...
✅ /match-event/1-1-{hash}-1-2-3a44...
```

### 未能拦截的API端点
```
❌ /match-odds/*  (需要点击触发)
❌ /odds-history/* (需要认证)
```

---

## 🎯 解决方案建议

### 方案A: 登录状态模拟 (推荐)
```javascript
// 添加Cookie/LocalStorage登录凭证
await context.addCookies([{
  name: 'session_id',
  value: '...',
  domain: '.oddsportal.com'
}]);
```

### 方案B: 点击触发赔率加载
```javascript
// 自动点击Odds Tab
await page.click('[data-tab="odds"]');
await page.waitForTimeout(3000);
```

### 方案C: 直接API端点访问
```javascript
// 构造直接赔率API URL
const oddsApiUrl = `https://www.oddsportal.com/match-odds/1/1/${hash}/1/2/`;
```

### 方案D: 使用项目已有的precision_strike_v6
```bash
node scripts/ops/precision_strike_v6.js
```

---

## 📊 当前执行结果

```
======================================================================
🚀 V38.3 Playwright点对点真实收割 (API拦截版)
======================================================================

📋 待收割比赛列表:
   1. Fulham vs Burnley (2024-05-11)
   2. Brentford vs Wolves (2024-05-11)
   3. Bournemouth vs Manchester United (2024-05-19)

[1/3] 🔍 [47_20232024_4813679] Fulham vs Burnley
   ✅ 页面加载成功 (373KB)
   ✅ API拦截成功 (15+ endpoints)
   ⚠️  未找到Bet365数据 (需登录/点击)
   ⚠️  未找到Pinnacle数据 (需登录/点击)

[2/3] 🔍 [47_20232024_4813666] Brentford vs Wolves
   ✅ 页面加载成功 (267KB)
   ⚠️  未找到赔率数据

[3/3] 🔍 [47_20232024_4813675] Bournemouth vs Manchester United
   ✅ 页面加载成功 (371KB)
   ⚠️  未找到赔率数据

======================================================================
📊 数据库查询结果 - SELECT * FROM match_odds
======================================================================

⚠️  暂无数据 (历史比赛需登录访问赔率)
======================================================================
```

---

## 📁 交付文件

| 文件 | 说明 |
|------|------|
| `scripts/ops/p2p_harvest_v38.js` | 点对点收割主脚本 |
| `scripts/ops/p2p_harvest_playwright_v38.py` | Python版(Playwright) |
| `debug_*.html` | 页面HTML快照 (3个比赛) |
| `p2p_harvest_v383_*.json` | 执行结果JSON |
| `P2P_HARVEST_REPORT_V38.md` | 本报告 |

---

## 🚀 下一步行动

1. **短期**: 使用项目中已有的`precision_strike_v6.js`（已验证可用）
2. **中期**: 实现登录状态模拟
3. **长期**: 开发专用赔率API端点直接访问

---

**结论**: URL Builder和API拦截框架已就绪，历史比赛赔率提取受限于OddsPortal访问控制，需登录凭证或特定触发机制。
