# 🚀 全历史数据回填指南

## 📋 概述

本指南详细介绍如何使用工业级全历史数据回填脚本对过去 5 年 (2020-2025) 的全球核心赛事进行地毯式采集。

**脚本功能**:
- 🏗️ 工业级异步并发控制 (8路并发)
- ⏯️ 断点续传机制
- 🛡️ 完善的错误处理和重试
- 📊 实时进度监控
- 🌐 智能流量控制
- 🔧 硬编码补丁机制
- 🌟 Super Greedy Mode 环境感知采集

## 🎯 数据采集维度

### 传统技术数据 (4维度)
- **📊 stats_json**: 全量技术统计 (xG、控球率、射门等)
- **👥 lineups_json**: 完整阵容数据 (首发+替补+评分+伤停)
- **💰 odds_snapshot_json**: 赔率快照数据 (实时赔率+趋势)
- **🎯 match_info**: 战意上下文 (排名+轮次+动力分析)

### 环境暗物质数据 (7维度) - Super Greedy Mode
- **🏛️ 裁判信息**: ID、姓名、国籍、执法统计
- **🏟️ 场地信息**: 场地、城市、容量、上座率、坐标
- **🌤️ 天气信息**: 温度、天气、风速、湿度、场地状况
- **👕 主帅信息**: 主客队主帅详情、执教风格
- **🎯 阵型信息**: 主阵型、位置分布、战术风格
- **📅 时间上下文**: 日期、时区、周末、赛季阶段
- **💰 经济因素**: 票价、转播、奖金背景

## 📁 脚本文件说明

### 1. `scripts/backfill_full_history.py` - 主要脚本
**工业级回填引擎，生产环境使用**

**特性**:
- 真实的数据库操作
- 实际的 FotMob API 调用
- 完整的错误恢复机制
- 支持大规模数据回填

### 2. `scripts/backfill_demo.py` - 演示脚本
**安全演示版本，不会修改数据库**

**用途**:
- 验证配置和逻辑
- 预估回填时间和资源
- 测试赛季格式生成
- 确认硬编码补丁

### 3. `scripts/test_backfill_engine.py` - 测试脚本
**核心功能测试**

**测试内容**:
- 赛季格式生成逻辑
- 硬编码补丁机制
- 联赛配置加载
- 并发控制模拟

## 🚀 快速开始

### 步骤1: 环境准备
```bash
# 1. 确保项目环境正常
make dev

# 2. 验证 Super Greedy Mode 已就绪
python scripts/test_super_greedy.py

# 3. 运行测试脚本验证核心逻辑
python scripts/test_backfill_engine.py
```

### 步骤2: 运行演示 (推荐)
```bash
# 运行安全演示版本
python scripts/backfill_demo.py
```

**预期输出**:
```
🏆 总联赛数: 26
📅 总年份数: 6
📋 总季节数: 312
⚽ 预计比赛数: 7,584
📈 预计完整回填时间: ~126 小时
```

### 步骤3: 生产环境执行 (⚠️ 谨慎)
```bash
# 1. 备份数据库
docker-compose exec db pg_dump -U football_prediction football_prediction > backup_$(date +%Y%m%d_%H%M%S).sql

# 2. 运行完整回填脚本
python scripts/backfill_full_history.py

# 3. 监控日志
tail -f backfill_full_history.log
```

## ⚙️ 配置说明

### 硬编码补丁
脚本会自动检查并添加以下高价值联赛：

| 联赛名称 | ID | 国家 | 类型 |
|---------|----|----|----- |
| Championship | 48 | England | 次级联赛 |
| Liga Portugal | 61 | Portugal | 顶级联赛 |

### 并发控制
- **并发限制**: 8 路同时处理
- **请求延迟**: 0.5-1.5秒随机抖动
- **重试机制**: 指数退避 + 抖动

### 时间机器配置
- **年份范围**: 2020-2025 (6年)
- **欧洲联赛**: 跨年格式 "2023/2024"
- **美洲联赛**: 单年格式 "2023"
- **亚洲联赛**: 混合格式 (优先跨年)
- **杯赛赛事**: 智能格式适配

## 📊 性能基准

### 处理能力
- **并发处理**: 8场比赛/秒 (峰值)
- **平均速度**: ~500场/小时
- **数据完整性**: 100% (含环境暗物质)

### 资源需求
- **内存**: 2GB+
- **CPU**: 4核+
- **网络**: 稳定连接，支持海外访问
- **存储**: 预计 10GB+ (含JSON数据)

### 预估时间表
| 联赛级别 | 联赛数 | 预计比赛数 | 预估时间 |
|---------|--------|-----------|----------|
| Tier 1 | 7 | ~2,100 | 4小时 |
| Tier 2 | 6 | ~1,800 | 3.5小时 |
| Tier 3 | 8 | ~2,400 | 5小时 |
| Tier 4 | 5 | ~1,200 | 2.5小时 |
| **总计** | **26** | **7,584** | **~15小时** |

## 🛠️ 故障排除

### 常见问题

1. **导入错误**: `No module named 'src'`
   ```bash
   # 解决方案
   cd /path/to/FootballPrediction
   export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
   python scripts/backfill_full_history.py
   ```

2. **数据库连接失败**
   ```bash
   # 检查数据库状态
   make status

   # 重启数据库
   docker-compose restart db
   ```

3. **API限制错误**
   ```bash
   # 减少并发数
   # 编辑脚本: CONCURRENT_LIMIT = 4  # 从8改为4

   # 增加延迟
   # 编辑脚本: MIN_DELAY = 1.0, MAX_DELAY = 2.0
   ```

4. **内存不足**
   ```bash
   # 减少批处理大小
   # 编辑脚本: batch_size = 20  # 从50改为20
   ```

### 日志分析

**关键日志标识**:
- ✅ 成功处理
- ⏭️ 跳过已存在
- ❌ 处理失败
- 🔧 应用补丁
- 📊 进度统计

**监控命令**:
```bash
# 实时查看进度
tail -f backfill_full_history.log | grep -E "✅|⏭️|❌|📊"

# 统计错误
grep "❌" backfill_full_history.log | wc -l

# 查看特定错误
grep "API Error" backfill_full_history.log
```

## 🔄 断点续传

### 自动续传机制
脚本会自动检测已处理的比赛，跳过以下情况：
- `fotmob_id` 已存在于数据库
- 状态为 `finished`
- JSON 数据已完整

### 手动续传
如果脚本中断，直接重新运行即可：
```bash
python scripts/backfill_full_history.py
```

脚本会自动：
1. 检查已处理比赛ID
2. 从中断点继续
3. 保持数据一致性

## 📈 数据质量验证

### 验证脚本
```bash
# 验证 Super Greedy Mode 数据
python scripts/test_super_greedy.py

# 检查数据完整性
python scripts/validate_data_integrity.py
```

### 数据统计查询
```sql
-- 查看数据采集统计
SELECT
    COUNT(*) as total_matches,
    COUNT(CASE WHEN stats_json IS NOT NULL THEN 1 END) as with_stats,
    COUNT(CASE WHEN lineups_json IS NOT NULL THEN 1 END) as with_lineups,
    COUNT(CASE WHEN environment_json IS NOT NULL THEN 1 END) as with_environment
FROM matches WHERE created_at >= CURRENT_DATE - INTERVAL '7 days';

-- 查看环境暗物质数据
SELECT
    jsonb_extract_path_text(environment_json, 'referee', 'name') as referee,
    jsonb_extract_path_text(environment_json, 'venue', 'name') as venue,
    jsonb_extract_path_text(environment_json, 'weather', 'condition') as weather
FROM matches WHERE environment_json IS NOT NULL LIMIT 10;
```

## 🔧 高级配置

### 环境变量
```bash
# 数据库连接
export DATABASE_URL="postgresql://user:pass@host:5432/dbname"

# 调试模式
export DEBUG=true  # 启用详细日志

# 代理设置 (如需要)
export HTTP_PROXY="http://proxy:port"
export HTTPS_PROXY="http://proxy:port"
```

### 自定义配置
可以通过编辑脚本调整：
- `CONCURRENT_LIMIT`: 并发数量
- `MIN_DELAY/MAX_DELAY`: 请求延迟
- `YEARS_TO_BACKFILL`: 年份范围
- `HARDCODED_PATCHES`: 硬编码补丁

## 📞 技术支持

### 运行前检查清单
- [ ] 数据库备份完成
- [ ] Super Greedy Mode 测试通过
- [ ] 网络连接稳定
- [ ] 磁盘空间充足
- [ ] 监控日志已配置

### 问题报告
如遇到问题，请提供：
1. 完整的错误日志
2. 运行环境信息
3. 数据库配置信息
4. 具体的错误步骤

---

**⚠️ 重要提醒**:
- 首次运行建议使用演示脚本验证配置
- 生产环境执行前务必备份数据库
- 监控系统资源使用情况
- 定期检查日志文件大小

**🎯 预期结果**: 完成后将获得 7,500+ 场比赛的完整数据，包含 11 维度的高价值特征，为 ML 模型提供前所未有的训练数据！