# V150.4.2 Archive API 拦截器 - 使用指南

## 概述

V150.4.2 是一个外科手术式的数据打捞工具，利用 OddsPortal Archive API 端点精准获取英超 2023/2024 赛季的 380 场比赛 ID。

## 核心特性

- **静默拦截**：使用 Playwright response 监听器拦截 Archive API 响应
- **零日志溢出**：严禁打印 API 原始 Body，直接保存到文件
- **离线解析**：独立的解析逻辑，提取 380 个比赛 ID
- **TDD 验收**：断言数量必须等于 380
- **数据库更新**：批量更新 matches_mapping 表

## 快速开始

### 1. 干跑模式（推荐首次使用）

```bash
python scripts/ops/v150_4_2_archive_interceptor.py \
  --season "2023/2024" \
  --dry-run
```

### 2. 实际运行（更新数据库）

```bash
python scripts/ops/v150_4_2_archive_interceptor.py \
  --season "2023/2024"
```

### 3. 禁用代理（调试用）

```bash
python scripts/ops/v150_4_2_archive_interceptor.py \
  --season "2023/2024" \
  --no-proxy
```

## 命令行参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--season` | `2023/2024` | 目标赛季（如 2023/2024） |
| `--no-proxy` | `False` | 禁用代理 |
| `--dry-run` | `False` | 干跑模式（不更新数据库） |

## TDD 断言

### 断言 A：唯一 ID 数量
- **目标**：380 个唯一 ID
- **验证**：解析的比赛数量必须等于 380

### 断言 B：排除降级队
- **目标**：不含 2023/2024 赛季前的降级队
- **降级队列表**：
  - Leeds United
  - Leicester City
  - Southampton

## 输出文件

### 1. Archive API 原始数据
- **路径**：`data/raw/archive_2023_2024.json`
- **格式**：JSON
- **内容**：拦截的 Archive API 完整响应

### 2. 解析结果报告
- **路径**：`logs/map_recovery/V150_4_2_recovery_report_*.json`
- **格式**：JSON
- **内容**：
  - 时间戳
  - 赛季信息
  - 统计数据（总数、成功数、失败数）
  - TDD 断言结果

## 数据库更新

### 更新目标表
```sql
-- matches_mapping 表
UPDATE matches_mapping
SET oddsportal_url = %s,
    updated_at = CURRENT_TIMESTAMP
WHERE fotmob_id = %s
```

### SQL 战报示例
```
📊 SQL 战报: Updated matches count: 380 / 380
```

## 单元测试

### 运行全部测试
```bash
pytest tests/ops/test_v150_4_2_archive_interceptor.py -v
```

### 测试覆盖
- ✅ 队名标准化测试
- ✅ URL 解析测试
- ✅ 字段提取测试
- ✅ 批量解析测试
- ✅ 球队验证测试
- ✅ API 模式匹配测试
- ✅ 数据库更新测试
- ✅ TDD 断言 A（380 场）
- ✅ TDD 断言 B（无降级队）

## 工作流程

### 步骤 1：Archive API 拦截
```
访问 OddsPortal results 页面
  ↓
设置 response 监听器
  ↓
模拟点击赛季选择器（2023/2024）
  ↓
捕获 Archive API 响应
  ↓
静默保存到 data/raw/archive_2023_2024.json
```

### 步骤 2：离线解析
```
加载 JSON 文件
  ↓
解析比赛链接（正则匹配）
  ↓
提取队名和 hash ID
  ↓
标准化队名格式
```

### 步骤 3：TDD 验收
```
断言 A：数量 = 380
  ↓
断言 B：无降级队
  ↓
生成验证报告
```

### 步骤 4：数据库更新
```
通过队名匹配数据库记录
  ↓
批量更新 oddsportal_url
  ↓
生成 SQL 战报
```

## 技术架构

### ArchiveAPIInterceptor
- **功能**：拦截 Archive API 响应
- **关键方法**：
  - `intercept_archive_api()`: 主拦截逻辑
  - `on_response()`: 响应处理回调

### ArchiveDataParser
- **功能**：离线解析 JSON 数据
- **关键方法**：
  - `load_and_parse()`: 加载并解析 JSON
  - `_extract_matches()`: 提取比赛列表
  - `_parse_row()`: 解析单行数据
  - `validate_team_count()`: 验证球队数量

### DatabaseUpdater
- **功能**：批量更新数据库
- **关键方法**：
  - `batch_update_urls()`: 批量更新 URL

## URL 格式规范

### 标准 URL 格式
```
/football/england/premier-league/{team1}-{team2}-{hash}/
```

### 示例
```
/football/england/premier-league/manchester-united-liverpool-1A2B3C4D/
/football/england/premier-league/arsenal-chelsea-E5F6A7B8/
```

### 正则表达式
```python
r'/premier-league/([a-z0-9-]+)-([a-z0-9-]+)-([A-Fa-f0-9]{8})/?$'
```

**说明**：
- `team1`: 小写字母、数字、连字符
- `team2`: 小写字母、数字、连字符
- `hash`: 8 位十六进制字符（0-9, A-F）

## 故障排除

### 问题 1：未捕获到 Archive API 响应
**原因**：Archive API 可能使用不同的端点
**解决方案**：
1. 检查网络请求（浏览器开发者工具）
2. 更新 `api_pattern` 正则表达式
3. 尝试手动触发 API

### 问题 2：解析数量不足 380
**原因**：JSON 结构不符合预期
**解决方案**：
1. 检查 `data/raw/archive_2023_2024.json` 内容
2. 调整 `_extract_matches()` 方法
3. 添加新的 JSON 结构支持

### 问题 3：数据库匹配失败
**原因**：队名格式不一致
**解决方案**：
1. 检查队名标准化逻辑
2. 扩展特殊队名映射
3. 使用模糊匹配替代精确匹配

## 性能指标

- **API 拦截时间**：< 30 秒
- **JSON 解析时间**：< 5 秒
- **数据库更新时间**：< 60 秒
- **总执行时间**：< 2 分钟

## 版本历史

| 版本 | 日期 | 核心变更 |
|------|------|---------|
| V150.4.2 | 2026-01-08 | Archive API 拦截器初始版本 |

## 相关文档

- [V150.4.1 Deep Pagination Scout](./V150_4_1_DEEP_PAGINATION_SCOUT.md)
- [V150.4 Map Refresher](./V150_4_MAP_REFRESHER.md)
- [V26.7 EPL Data Quality Audit](./V26_7_EPL_DATA_QUALITY_AUDIT_REPORT.md)

---

**准入红线**：只有当 `data/raw/archive_2023_2024.json` 生成且包含 380 场合规数据时，才批准重启全量收割。

**Author**: 高级爬虫架构师 & API 协议分析专家
**Version**: V150.4.2
**Date**: 2026-01-08
