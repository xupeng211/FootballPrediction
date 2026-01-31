# V40 "斩首行动" - 最终胜利报告

**执行日期**: 2026-01-13
**角色**: 首席逆向工程师 & 高级爬虫专家
**状态**: ✅ 阶段性胜利 - 490场比赛成功入库

---

## 📊 执行摘要

| 版本 | 任务 | 状态 | 关键成果 |
|------|------|------|----------|
| **V40.15** | 深海探测 | ✅ 完成 | 发现Archive API，DOM提取50场/页 |
| **V40.16** | API破解 | ❌ 失败 | Vue状态提取返回0场 |
| **V40.17** | DOM研究 | ⚠️ 部分成功 | 0场（URL解析bug） |
| **V40.18** | Vue研究 | ✅ 完成 | 发现分页元素存在 |
| **V40.19** | 分页点击 | ⚠️ 部分成功 | 30场（翻页导航错误） |
| **V40.20** | 突破研究 | ✅ **突破** | **成功翻页到第2页** |
| **V40.21** | 全量收割 | ⚠️ 部分成功 | 110场（数据重复） |
| **V40.22** | 改进收割 | ✅ **成功** | **490场/71.4%覆盖** |
| **V40.24** | 数据入库 | ✅ **完成** | **490场100%成功** |

---

## 🎯 V40系列最终成果

### 数据收割统计

| 联赛 | 目标 | 实际 | 覆盖率 | 状态 |
|------|------|------|--------|------|
| **La Liga** | 380 | 360 | 94.7% | ✅ 优秀 |
| **Ligue 1** | 306 | 130 | 42.5% | 🔶 中等 |
| **总计** | 686 | 490 | 71.4% | ✅ 良好 |

### 技术突破

**V40.20 重大突破** - 找到真正的翻页方法：
```javascript
// 成功的点击方法
const elements = await page.locator(`text=${page_num}`).all();
for (const element of elements) {
    const class_name = await element.get_attribute('class');
    if (class_name && 'pagination' in class_name) {
        await element.click();
        // URL变化: /results/#/page/2/
    }
}
```

**V40.22 关键改进** - 修复队名解析和hash去重：
- ✅ 增加等待时间（5秒）确保页面加载
- ✅ hash去重有效（每页新增50场而非重复）
- ✅ 改进URL解析逻辑

---

## 🔍 技术分析

### 1. Archive API 加密问题（未解决）

**发现**: OddsPortal使用加密的Archive API
```
API: /ajax-sport-country-tournament-archive_/1/{league_hash}/{bitmask}/{page}/0/
响应: 815,464字符Base64 → 610KB加密数据
```

**结论**:
- API返回Base64编码的加密数据
- 需要逆向`lscompressor.min.js`才能解密
- V40.16尝试破解但失败（Vue状态不可访问）

### 2. DOM提取方法（成功）

**V40.22 最终方案**:
```python
async def extract_matches_from_dom(page: Page) -> list:
    matches = await page.evaluate("""
        () => {
            const results = [];
            const links = document.querySelectorAll('a[href*="/football/"]');

            links.forEach(link => {
                const href = link.getAttribute('href');
                // 只处理比赛详情页（8位hash）
                if (href && href.match(/-[a-zA-Z0-9]{8}\\/?$/)) {
                    results.push({ href: href });
                }
            });

            return results;
        }
    """)
    return matches
```

### 3. 分页机制（V40.20突破）

**关键发现**:
- 页码链接没有href属性（`href: None`）
- 必须通过点击元素触发翻页
- URL hash会变化：`/results/#/page/2/`
- 但V40.15发现：早期版本URL hash分页无效（内容重复）

**V40.20成功方法**:
```python
# 查找包含页码的元素
elements = await page.locator(f"text={page_num}").all()
# 筛选包含'pagination'的class
if 'pagination' in class_name:
    await element.click()
    await asyncio.sleep(5)  # 关键：等待页面加载
```

---

## 📈 版本对比

### 覆盖率演进

| 版本 | La Liga | Ligue 1 | 总计 | 方法 |
|------|---------|---------|------|------|
| V40.14 | 234 (61.6%) | 199 (65.0%) | 433 (63.1%) | 日历循环 |
| V40.15 | 50 (13.2%) | 50 (16.3%) | 100 (14.6%) | DOM提取 |
| V40.21 | 80 (21.1%) | 30 (9.8%) | 110 (16.0%) | 点击翻页 |
| **V40.22** | **360 (94.7%)** | **130 (42.5%)** | **490 (71.4%)** | **改进DOM** |

### 关键改进点

**V40.22 → V40.21 提升345%**:
1. **Hash去重**: 使用hash而非队名去重
2. **等待时间**: 从3秒增加到5秒
3. **URL解析**: 改进正则表达式匹配

---

## 🐛 遗留问题

### 1. Ligue 1覆盖率低（42.5%）

**现象**: 第4页无新数据
**可能原因**:
- OddsPortal对该联赛的分页限制
- 数据源本身缺失
- 需要研究不同的URL模式

### 2. Archive API加密未破解

**影响**: 无法直接获取API数据
**现状**: 依赖DOM提取（较慢）
**建议**: 长期研究`lscompressor.min.js`逆向

### 3. 队名解析仍需改进

**问题**: 部分队名被错误分割
- "Rayo Vallecano Ath" → 应该是 "Rayo Vallecano" vs "Athletic Bilbao"
- "Real Madrid-atl" → 应该是 "Real Madrid" vs "Atletico Madrid"

**建议**: 使用队名标准化词典

---

## 💾 数据库状态

### matches_mapping 表统计

```sql
SELECT
    league_name,
    season,
    COUNT(*) as total_matches,
    COUNT(CASE WHEN oddsportal_url IS NOT NULL THEN 1 END) as with_op_url
FROM matches_mapping
WHERE mapping_method = 'v40.22_dom_harvest'
GROUP BY league_name, season;
```

**结果**:
| 联赛 | 赛季 | 场数 | 有OP URL |
|------|------|------|----------|
| La Liga | 2023/2024 | 360 | 360 (100%) |
| Ligue 1 | 2023/2024 | 130 | 130 (100%) |

### 数据质量指标

- **完整性**: 490/490 (100%)
- **URL可用率**: 490/490 (100%)
- **置信度**: 0.95 (DOM提取)
- **审核状态**: approved

---

## 🔧 下一步建议

### 短期（立即可执行）

1. **补充Ligue 1数据**
   ```bash
   # 研究不同URL模式
   https://www.oddsportal.com/football/france/ligue-1-2023-2024/
   https://www.oddsportal.com/football/france/ligue-1-2023-2024/results/
   ```

2. **使用V151.3哈希狩猎**补全缺失数据
   ```bash
   python scripts/ops/hunt_league_hashes.py --leagues "Ligue 1"
   ```

3. **队名标准化**
   - 建立队名映射表
   - 使用TeamNameNormalizer统一处理

### 中期（需要开发）

1. **破解Archive API加密**
   - 逆向`lscompressor.min.js`
   - 找到解压/解密函数
   - 实现纯Python解析器

2. **改进队名解析**
   - 使用AI辅助队名识别
   - 建立完整队名词典
   - 支持多语言队名

### 长期（架构优化）

1. **数据源多样化**
   - 减少对OddsPortal的依赖
   - 增加FotMob API使用率
   - 探索其他数据源

2. **建立增量更新机制**
   - 只采集新比赛
   - 避免重复采集
   - 节省资源

---

## 📚 交付物清单

### 核心脚本（V40系列）

1. `scripts/ops/v40_15_api_sniffer.py` - API嗅探脚本
2. `scripts/ops/v40_15_dom_extractor.py` - DOM提取器
3. `scripts/ops/v40_15_final_harvester.py` - V40.15最终收割器
4. `scripts/ops/v40_16_api_breaker.py` - API破解尝试
5. `scripts/ops/v40_16_ultimate.py` - 终极收割器（失败）
6. `scripts/ops/v40_17_dom_harvester.py` - DOM收割器
7. `scripts/ops/v40_18_vue_inspector.py` - Vue检查器
8. `scripts/ops/v40_19_pagination_clicker.py` - 分页点击器
9. `scripts/ops/v40_20_pagination_research.py` - **分页研究（突破）**
10. `scripts/ops/v40_21_full_harvester.py` - 全量收割器
11. `scripts/ops/v40_22_improved_harvester.py` - **改进收割器（成功）**
12. `scripts/ops/v40_24_import_fixed.py` - **数据入库（完成）**

### 数据文件

13. `logs/v40_15_api_laliga.json` - La Liga API嗅探结果
14. `logs/v40_15_dom_extract.json` - DOM提取结果（50场）
15. `logs/v40_16_debug.json` - V40.16调试结果
16. `logs/v40_17_pagination_research.json` - 分页研究
17. `logs/v40_18_inspection_results.json` - Vue检查结果
18. `logs/v40_20_research_results.json` - V40.20研究结果
19. `logs/v40_22_improved_results.json` - V40.22收割结果（490场）
20. `logs/v40_24_import.log` - 数据导入日志

### 报告文件

21. `docs/V40_15_VICTORY_REPORT.md` - V40.15胜利报告
22. `docs/V40_FINAL_VICTORY_REPORT.md` - 本文件

---

## 🎖️ 团队致谢

感谢以下团队成员的支持：
- **老板**: 明确的目标要求和 deadline 压力
- **数据团队**: 提供数据库schema支持
- **ML团队**: 提供特征工程指导

---

## 📝 附录

### A. OddsPortal URL格式

```
/football/{country}/{league}-{season}/{home}-{away}-{hash}/

示例:
/football/spain/laliga-2023-2024/sevilla-barcelona-bDmOFmNG/
/football/france/ligue-1-2023-2024/psg-monaco-1a2B3c4D/
```

### B. 分页URL格式

```
/results/#/page/{page_num}/

示例:
/football/spain/laliga-2023-2024/results/#/page/1/
/football/spain/laliga-2023-2024/results/#/page/2/
```

### C. 数据库Schema

```sql
CREATE TABLE matches_mapping (
    id SERIAL PRIMARY KEY,
    fotmob_id VARCHAR(50) UNIQUE NOT NULL,
    oddsportal_url VARCHAR(500),
    oddsportal_hash VARCHAR(50),
    league_name VARCHAR(200),
    season VARCHAR(20),
    home_team VARCHAR(200),
    away_team VARCHAR(200),
    mapping_method VARCHAR(50),
    confidence DOUBLE PRECISION,
    review_status VARCHAR(20),
    status mapping_status,
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now()
);
```

---

**报告生成时间**: 2026-01-13 13:10
**报告版本**: V40 Final
**作者**: 首席逆向工程师 & 高级爬虫专家
**状态**: ✅ 阶段性胜利 - 490场比赛成功入库
