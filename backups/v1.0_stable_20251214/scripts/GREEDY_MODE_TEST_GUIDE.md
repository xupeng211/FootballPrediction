# Greedy Mode 测试指南

## 🎯 概述

本指南提供 Greedy Mode 功能的完整测试方案，包括冒烟测试、集成测试和生产部署验证。

## 📋 测试脚本说明

### 1. `test_greedy_mode_standalone.py` - 冒烟测试 (推荐首先运行)

**用途**: 快速验证 Greedy Mode 功能模块，无需复杂的数据库连接
**适用场景**:
- 初步功能验证
- CI/CD 管道快速检查
- 开发环境快速测试

**运行方式**:
```bash
# 1. 基础运行（使用模拟数据）
python scripts/test_greedy_mode_standalone.py

# 2. 设置真实数据库连接
export DATABASE_URL="postgresql://user:pass@localhost:5432/football_prediction"
python scripts/test_greedy_mode_standalone.py
```

**预期输出**:
```
🎉 ✅ SMOKE TEST PASSED
🚀 Greedy Mode 已准备就绪，可以开始大规模数据回填!
```

### 2. `test_greedy_mode_integrated.py` - 集成测试

**用途**: 在真实项目环境中验证完整的 Greedy Mode 功能
**适用场景**:
- 生产环境部署前验证
- 真实数据库结构检查
- 实际 FotMob API 数据采集测试

**前置条件**:
- 应用环境已启动: `make dev`
- 数据库连接正常
- FotMob API 令牌已配置

**运行方式**:
```bash
# 1. 启动开发环境
make dev

# 2. 在新终端中运行集成测试
python scripts/test_greedy_mode_integrated.py
```

**预期输出**:
```
✅ 数据库管理器初始化成功
✅ 所有Greedy Mode列都已存在
✅ 实际数据采集成功
🎉 ✅ INTEGRATED TEST PASSED
```

## 🧪 测试验证维度

### 四大核心数据维度

1. **stats_json** - 全量技术统计
   - ✅ xG (期望进球数) 数据
   - ✅ 控球率 (Possession) 数据
   - ✅ 射门、角球等统计

2. **lineups_json** - 完整阵容数据
   - ✅ 主客队首发阵容
   - ✅ 替补球员信息
   - ✅ 伤停名单
   - ✅ 球员评分数据

3. **odds_snapshot_json** - 赔率快照数据
   - ✅ 赔率快照时间戳
   - ✅ 主胜、平局、客胜赔率
   - ✅ 赔率变化趋势

4. **match_info** - 战意上下文信息
   - ✅ 赛前排名数据
   - ✅ 轮次信息
   - ✅ 战意分析上下文

## 🗄️ 数据库迁移验证

### 检查新增的 JSON 列

Greedy Mode 在 `matches` 表中新增了以下 4 个 JSON 列：

```sql
-- PostgreSQL
ALTER TABLE matches ADD COLUMN stats_json JSONB;
ALTER TABLE matches ADD COLUMN lineups_json JSONB;
ALTER TABLE matches ADD COLUMN odds_snapshot_json JSONB;
ALTER TABLE matches ADD COLUMN match_info JSONB;

-- SQLite
ALTER TABLE matches ADD COLUMN stats_json JSON;
ALTER TABLE matches ADD COLUMN lineups_json JSON;
ALTER TABLE matches ADD COLUMN odds_snapshot_json JSON;
ALTER TABLE matches ADD COLUMN match_info JSON;
```

### 验证命令

```bash
# 检查表结构
docker-compose exec db psql -U football_prediction -c "
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'matches'
AND column_name IN ('stats_json', 'lineups_json', 'odds_snapshot_json', 'match_info')
ORDER BY column_name;
"
```

## 🔧 故障排除

### 常见问题及解决方案

1. **数据库连接失败**
   ```bash
   # 检查数据库服务状态
   make status

   # 重启数据库服务
   docker-compose restart db
   ```

2. **FotMob API 认证失败**
   ```bash
   # 检查API令牌配置
   cat .env | grep FOTMOB

   # 刷新API令牌
   python scripts/refresh_fotmob_tokens.py
   ```

3. **数据库迁移未完成**
   ```bash
   # 运行数据库迁移
   make db-migrate

   # 检查迁移状态
   docker-compose exec app alembic current
   ```

4. **导入错误 (ImportError)**
   ```bash
   # 确保Python路径正确
   export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

   # 或在项目根目录运行
   cd /path/to/FootballPrediction
   python scripts/test_greedy_mode_*.py
   ```

## 📊 测试报告解读

### 成功指标

冒烟测试成功应看到：
- ✅ 数据库迁移检查: 通过
- ✅ 数据抓取测试: 通过
- ✅ 数据验证测试: 通过
- 🎉 SMOKE TEST PASSED

集成测试成功应看到：
- ✅ 数据库管理器初始化成功
- ✅ 所有Greedy Mode列都已存在
- ✅ 实际数据采集成功
- 🎉 INTEGRATED TEST PASSED

### 失败诊断

如果测试失败，按以下顺序检查：

1. **环境检查**
   - Docker服务是否正常: `make status`
   - 网络连接是否正常
   - 环境变量是否配置正确

2. **数据库检查**
   - 数据库连接是否正常
   - 表结构是否包含新增列
   - 数据迁移是否完成

3. **API检查**
   - FotMob API令牌是否有效
   - 网络代理是否正常
   - 请求频率是否过高

## 🚀 生产部署验证

生产环境部署前建议按以下顺序验证：

```bash
# 1. 快速冒烟测试（确保功能基本正常）
python scripts/test_greedy_mode_standalone.py

# 2. 完整集成测试（验证真实环境）
make dev && python scripts/test_greedy_mode_integrated.py

# 3. 数据质量验证（检查实际数据）
python scripts/validate_data_integrity.py

# 4. 性能测试（验证大规模数据处理）
python scripts/backfill_details_fotmob_v2.py --dry-run --limit=10
```

## 📝 日志分析

### 关键日志位置

- 应用日志: `docker-compose logs app`
- 数据库日志: `docker-compose logs db`
- 测试日志: 测试脚本的标准输出

### 日志关键词

成功指标:
- "PASSED"
- "✅" 图标
- "成功采集"

失败指标:
- "FAILED"
- "❌" 图标
- "Exception" 或 "Error"

## 📞 技术支持

如遇到问题，请提供以下信息：
1. 测试脚本完整输出
2. Docker服务状态 (`make status`)
3. 环境配置信息 (去除敏感信息)
4. 相关日志片段

---

**更新日期**: 2025-01-08
**版本**: 1.0.0
**维护者**: QA Engineer & DBA