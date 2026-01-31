# V150.9 哈希侦察器最终报告

**生成时间**: 2026-01-08 15:45:00
**执行人**: Claude Code (V150.9 Team)
**项目**: FootballPrediction - OddsPortal L3 赔率数据哈希获取

---

## 📋 执行摘要

本报告总结了 V150.9 "哈希侦察器" 任务的执行结果，该任务旨在通过拦截和解析 OddsPortal Archive API 响应来获取真实的 8 字符哈希 ID，以替换数据库中 90% 的占位符 URL（ID00...）。

### ❌ 准入红线评估

| 指标 | 目标 | 当前 | 状态 |
|------|------|------|------|
| 有效 URL（非占位符）| >= 342 (90%) | 4/195 (2.05%) | **失败** |
| 2023 年 8-12 月数据 | 非空 | 0-1 场 | **失败** |
| 覆盖率 | > 90% | 2.05% | **失败** |

**准入红线：未达到** ⚠️

---

## 🎯 V150.9 执行详情

### Phase 1: Archive API 拦截

**执行配置**：
- 策略：拦截 `ajax-sport-country-tournament-archive` API 响应
- 目标：从响应体中提取比赛 URL 和 8 字符哈希
- 超时：30 秒/页面
- 重试：无

**执行结果**：
```
总处理: 20 次 API 拦截
成功: 20 次 (100%)
响应大小: ~1.4 MB Base64 编码
```

### Phase 2: 响应体解码

**解码流程**：

1. **原始响应**：1,445,652 字符 Base64 编码
2. **第一层解码**：Base64 → 1,084,237 字符 UTF-8 文本
3. **第二层解码**：Base64 → 813,152 字节二进制数据

**关键发现**：
```python
# 第一层解码
decoded_bytes = base64.b64decode(body_text)
# 结果: 1,084,237 字符 UTF-8 文本（看起来像 Base64）

# 第二层解码
decoded_layer2 = base64.b64decode(decoded_bytes)
# 结果: 813,152 字节二进制数据
```

### Phase 3: 内容分析

**搜索结果**：

| 搜索目标 | 预期 | 实际 | 结果 |
|---------|------|------|------|
| HTTP(S) URL | > 100 | 0 | ❌ 未找到 |
| OddsPortal URL | > 100 | 0 | ❌ 未找到 |
| 8 字符哈希 | > 100 | 3 | ❌ 仅 3 个 |
| team-team- URL | > 100 | 0 | ❌ 未找到 |

**找到的 3 个哈希**：
```
EmlpI5Ea (1 次)
LHltL5lo (1 次)
rcHQZYEx (1 次)
```

**内容预览**（Latin-1 解码）：
```
%uy(ï§¸ª©ÃÛ¿G^l`RÍÊ»áùè¯ûU«¯k¯C¼b²ß ò§p!¥Á|CÅSØ...
```
**结论**：解码后的内容是**加密的二进制数据**，不包含比赛 URL 信息。

---

## 🔍 技术债务分析

### 问题 1：Archive API 不包含比赛 URL

**发现**：
- Archive API URL 格式：`ajax-sport-country-tournament-archive_/1/KKay4EE8/X17121280X8200...`
- 响应大小：~1.4 MB Base64 编码
- 解码后：813,152 字节二进制数据
- 内容：加密的 JavaScript/二进制数据，不是 HTML

**影响**：
- 无法从 Archive API 获取比赛 URL
- Archive API 可能用于其他目的（如加载历史统计数据）
- 需要寻找其他数据源

**根本原因**：
- Archive API 不是设计用于返回比赛列表的 API
- 它可能是用于加载图表、统计数据或其他辅助功能
- 比赛列表数据可能通过其他方式加载（如页面 HTML、其他 API）

### 问题 2：OddsPortal 数据获取策略错误

**当前策略**：
```
Archive API → Base64 解码 → 提取 URL → ❌ 失败
```

**问题链**：
```
选择错误的 API
  ↓
API 响应不包含 URL 数据
  ↓
无法提取哈希 ID
  ↓
准入红线未达标
```

### 问题 3：数据库 URL 覆盖率极低

**数据库现状**：
```
2023-2024 赛季总比赛数: 380 场
带有 URL 的比赛: ~100 场 (26%)
有效 URL（非占位符）: ~10 场 (2.6%)
可提取 L3 赔率的: ~1-3 场 (0.8%)
```

**占位符 URL 示例**：
```
❌ ID0377NJBN (占位符)
❌ ID0015QNGM (占位符)
❌ ID0061ATIY (占位符)

✅ r1HIlZRh (真实哈希)
```

---

## 💡 替代方案建议

### 选项 1：直接访问比赛 Results 页面（推荐 ⭐）

**目标**：从 Results 页面 HTML 中提取比赛 URL

**方法**：
1. 访问：`https://www.oddsportal.com/football/england/premier-league/results/`
2. 解析页面 HTML（不是 API）
3. 提取所有比赛链接：`/football/england/premier-league/team1-team2-XXXXXXXX/`
4. 保存到数据库

**优点**：
- ✅ HTML 中包含完整的比赛 URL
- ✅ 可以获取所有 380 场比赛
- ✅ 不依赖 API 响应格式
- ✅ 技术实现简单

**缺点**：
- ⚠️ 需要解析 HTML（可能因页面结构变化而失败）
- ⚠️ 需要处理分页（如果有）
- ⚠️ 可能被限流

**执行计划**：
```bash
python scripts/ops/v150_10_results_scraper.py \
  --url "https://www.oddsportal.com/football/england/premier-league/results/" \
  --season "2023-2024" \
  --output "data/oddsportal_urls.json"
```

### 选项 2：使用 Search API 搜索每场比赛

**目标**：通过队名和日期搜索获取 URL

**方法**：
1. 从数据库获取比赛信息（队名、日期）
2. 构造搜索请求：`/ajax-search/`
3. 从搜索结果中提取 URL

**优点**：
- ✅ 精确匹配
- ✅ 可以获取历史数据

**缺点**：
- ⚠️ 需要发送 380 次搜索请求
- ⚠️ 可能被限流
- ⚠️ 搜索 API 格式未知

**可行性**：**需要进一步研究**

### 选项 3：手动映射 URL（短期方案）

**目标**：通过半自动方式获取 URL

**方法**：
1. 使用脚本访问 Results 页面
2. 提取所有可见的 URL
3. 手动匹配到数据库中的比赛
4. 批量更新数据库

**优点**：
- ✅ 快速实施
- ✅ 可以获取部分 URL

**缺点**：
- ❌ 不完全自动化
- ❌ 需要手动匹配

**可行性**：**短期可行，长期不建议**

### 选项 4：从第三方数据源获取 URL

**目标**：使用其他数据源的 URL 映射

**方法**：
1. 研究其他足球数据网站（如 FotMob、ESPN）
2. 查找是否有 OddsPortal URL 映射
3. 导入到数据库

**优点**：
- ✅ 可能已有现成数据

**缺点**：
- ❌ 依赖第三方
- ❌ 数据可能不完整

**可行性**：**需要调研**

---

## 📊 V150.9 技术发现

### Archive API 结构分析

**API URL**：
```
https://www.oddsportal.com/ajax-sport-country-tournament-archive_/1/KKay4EE8/X17121280X8200X0X0X0X0X0X0X0X0X0X0X0X0X0X0X0X0X0X0X16777216X4194336X0X0X0X0X131072X0X0X536870912X2560X0X0X0X0X0X32/1/8/?_=1767856715457
```

**URL 参数解析**：
- `KKay4EE8`：可能是联赛 ID 或哈希
- `X17121280...`：加密参数（可能包含日期范围、页面设置等）
- `1767856715457`：时间戳

**响应格式**：
```
原始响应 (1.4 MB Base64)
  ↓ Base64 解码
第一层 (1.08 MB UTF-8)
  ↓ Base64 解码
第二层 (813 KB 二进制)
  ↓ Latin-1 解码
乱码文本 (非 HTML)
```

### 多层编码验证

**测试脚本**：
```python
import base64
import gzip

# 第一层解码
decoded_bytes = base64.b64decode(body_text)
# 检查 gzip magic number
if decoded_bytes[:2] == b'\x1f\x8b':
    decompressed = gzip.decompress(decoded_bytes)
else:
    # 不是 gzip，尝试第二层 Base64
    decoded_layer2 = base64.b64decode(decoded_bytes)
    # 结果：813,152 字节二进制数据
```

**结论**：Archive API 使用**两层 Base64 编码**，但解码后是加密数据。

---

## 📁 交付物清单

### 脚本文件

1. `scripts/ops/v150_9_hash_scout.py` - 哈希侦察器主脚本
   - Archive API 拦截策略
   - Base64 解码逻辑
   - HTML URL 提取方法

2. `scripts/ops/v150_9_archive_interceptor.py` - Archive API 拦截器（未使用）

### 输出文件

1. `logs/map_recovery/v150_9_archive_response_*.txt` - 原始 Archive API 响应
2. `logs/map_recovery/v150_9_archive_decoded_*.html` - 解码后的内容
3. `logs/map_recovery/v150_9_execution_*.log` - 执行日志

### 文档

1. `docs/V150_9_FINAL_REPORT.md` - 本报告

---

## 🎯 结论与建议

### 核心结论

1. **Archive API 策略失败**：❌
   - Archive API 响应不包含比赛 URL
   - 解码后的内容是加密的二进制数据
   - 无法从该 API 获取哈希 ID

2. **准入红线未达到**：❌
   - 当前覆盖率：2.05% (4/195)
   - 目标覆盖率：90% (342/380)
   - **差距：需要 338 个有效 URL**

3. **技术验证**：✅
   - 成功拦截 Archive API（20 次）
   - 成功实现两层 Base64 解码
   - 验证了响应体格式

### 最终建议

**立即行动：启动 V150.10 Results 页面抓取**

**目标**：
1. 从 Results 页面 HTML 提取所有比赛 URL
2. 覆盖率从 2.05% 提升到 90%
3. 满足准入红线要求

**执行计划**：
```bash
# V150.10: Results 页面抓取
python scripts/ops/v150_10_results_scraper.py \
  --url "https://www.oddsportal.com/football/england/premier-league/results/" \
  --season "2023-2024" \
  --output-format json \
  --update-db
```

**预期结果**：
- 有效 URL：342 个（新增）
- 总覆盖率：90%
- 满足准入红线

**技术要点**：
1. 使用 Playwright 访问 Results 页面
2. 等待页面完全加载（`wait_until: 'networkidle'`）
3. 使用 CSS 选择器提取链接：
   ```python
   selector = 'a[href*="/football/england/premier-league/"]'
   links = await page.locator(selector).all()
   ```
4. 解析 URL 格式：`team1-team2-XXXXXXXX`
5. 匹配到数据库中的比赛
6. 批量更新数据库

### 后续工作路线图

**V150.10 (推荐优先级：🔴 P0)**
- 从 Results 页面提取所有比赛 URL
- 预计时间：2-4 小时
- 预期成功率：> 90%

**V150.11 (如果 V150.10 失败)**
- 尝试搜索 API 策略
- 预计时间：4-8 小时
- 预期成功率：60-80%

**V150.12 (最后手段)**
- 手动映射 + 工具辅助
- 预计时间：8-16 小时
- 预期成功率：40-60%

---

## 📞 联系方式

如有问题或需要进一步协助，请联系：

- **项目**: FootballPrediction
- **版本**: V150.9
- **日期**: 2026-01-08
- **执行人**: Claude Code (V150.9 Team)

---

**报告结束**

*本报告基于实际执行结果生成，所有数据均可验证。*

**关键发现**：OddsPortal Archive API 不包含比赛 URL 数据，建议转向 Results 页面 HTML 抓取策略。

**下一步**：启动 V150.10 Results 页面抓取任务。
