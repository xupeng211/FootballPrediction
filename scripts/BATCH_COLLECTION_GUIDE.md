# FotMob 批量采集使用指南

## 🎯 概述

`run_batch_collection.py` 是专业的批量数据采集脚本，用于构建历史数据库。采用 L1 + L2 双层架构，集成完整的生产级稳定性控制。

## 🏗️ 架构设计

### 双层数据采集
- **L1 层**: 基础比赛数据 (比赛列表、基本信息)
- **L2 层**: 高阶统计数据 (xG、球员评分、赔率等)

### 稳定性控制
- **频率控制**: 自适应请求频率调节
- **代理轮换**: 智能代理池管理
- **断点续传**: 支持中断后继续采集
- **错误重试**: 多层次错误处理机制

## 🚀 快速开始

### 1. 环境准备

```bash
# 确保在项目根目录
cd /home/user/projects/FootballPrediction

# 检查虚拟环境
source venv/bin/activate  # 或使用 conda

# 安装依赖 (如需要)
pip install -r requirements.txt
```

### 2. 配置检查

```bash
# 检查数据库连接
python -c "from src.database.async_manager import initialize_database; import asyncio; asyncio.run(initialize_database())"

# 检查采集器导入
python -c "from src.collectors.enhanced_fotmob_collector import EnhancedFotMobCollector; print('✅ 导入成功')"
```

### 3. 运行采集

```bash
# 基础运行
python scripts/run_batch_collection.py

# 后台运行
nohup python scripts/run_batch_collection.py > logs/batch_collection.log 2>&1 &

# 使用 tmux/screen
tmux new -s fotmob_batch
python scripts/run_batch_collection.py
```

## 📊 采集范围

### 默认配置
- **时间范围**: 过去 30 天
- **目标联赛**: 五大联赛
  - Premier League (英超)
  - La Liga (西甲)
  - Bundesliga (德甲)
  - Serie A (意甲)
  - Ligue 1 (法甲)

### 联赛 ID 对照表
```python
MAJOR_LEAGUES = {
    "Premier League": 47,      # 英超
    "La Liga": 87,             # 西甲
    "Bundesliga": 54,          # 德甲
    "Serie A": 55,             # 意甲
    "Ligue 1": 42              # 法甲
}
```

## 📁 输出结构

### 文件组织
```
data/batch_cache/
├── progress.json              # 进度跟踪文件
├── failed_matches.json        # 失败比赛列表
├── 2025-11-05/               # 按日期组织
│   ├── match_123456.json
│   ├── match_123457.json
│   └── ...
└── 2025-11-06/
    ├── match_234567.json
    └── ...

logs/batch_collection/
├── batch_collection.log       # 主日志文件
└── ...
```

### 数据格式
每场比赛的 JSON 文件包含：
```json
{
  "match_id": "123456",
  "date": "2025-11-05",
  "l1_data": {
    "基础信息": "来自L1层采集"
  },
  "l2_data": {
    "高阶统计": "来自L2层采集"
  },
  "collected_at": "2025-12-05T10:30:00",
  "collection_version": "v2.0"
}
```

## ⚙️ 高级配置

### 自定义采集范围
```python
# 修改 CollectionConfig 类中的参数
@dataclass
class CollectionConfig:
    DAYS_BACK = 60              # 采集过去60天
    BATCH_SIZE = 20            # 每批次处理20场比赛
    MAJOR_LEAGUES = {
        # 添加更多联赛
        "Premier League": 47,
        "Championship": 48,     # 英冠
        "FA Cup": 49,           # 足总杯
    }
```

### 代理配置
```bash
# 设置环境变量
export PROXY_LIST="proxy1.example.com:8080,proxy2.example.com:8080"

# 或在脚本中直接配置
mock_proxies = [
    ProxyConfig(host="your-proxy1.com", port=8080),
    ProxyConfig(host="your-proxy2.com", port=8080),
]
```

### 频率控制调整
```python
# 调整请求频率
request_config = RequestConfig(
    min_delay=0.5,      # 最小延迟0.5秒
    max_delay=5.0,      # 最大延迟5秒
    base_delay=1.5,     # 基础延迟1.5秒
    burst_limit=5,      # 突发请求限制
)
```

## 📈 监控和调试

### 实时监控
```bash
# 查看实时日志
tail -f logs/batch_collection.log

# 查看进度
cat data/batch_cache/progress.json | python -m json.tool

# 查看失败比赛
cat data/batch_cache/failed_matches.json | python -m json.tool
```

### 断点续传
脚本自动支持断点续传：
- **进度保存**: 每处理完一个日期自动保存进度
- **失败重试**: 失败的比赛会在下次运行时重新尝试
- **跳过机制**: 已成功处理的比赛会被跳过

### 手动重置
```bash
# 重置进度，重新开始采集
rm data/batch_cache/progress.json
rm data/batch_cache/failed_matches.json

# 清理缓存数据
rm -rf data/batch_cache/2025-*/
```

## 🔧 常见问题

### Q: 采集速度太慢？
A: 调整配置参数：
```python
# 增加并发，减少延迟
BATCH_SIZE = 20
DELAY_BETWEEN_MATCHES = 1.0
```

### Q: 大量请求失败？
A: 启用更保守的反爬策略：
```python
# 使用保守策略
self.l1_collector = EnhancedFotMobCollector(
    anti_scraping_level="high"  # 高反爬级别
)
```

### Q: 数据库连接失败？
A: 检查数据库配置：
```bash
# 检查环境变量
echo $DATABASE_URL

# 测试连接
python -c "
import asyncio
from src.database.async_manager import get_db_session
async def test():
    async with get_db_session() as session:
        print('✅ 数据库连接成功')
asyncio.run(test())
"
```

### Q: 内存使用过高？
A: 调整批处理大小：
```python
# 减少批处理大小，增加频率
BATCH_SIZE = 5
```

## 📊 性能指标

### 预期性能
- **处理速度**: 2-5 场比赛/分钟
- **成功率**: 85-95%
- **数据完整性**: L1层 100%，L2层 80-90%

### 监控指标
脚本会实时显示：
```
📊 进度: 85.0% (25/30 天) | ✅ 成功: 245 | ❌ 失败: 12 | ⏭️ 跳过: 33 | ⏱️ 时长: 45.2分钟
```

## 🛠️ 维护建议

### 定期维护
1. **日志轮转**: 定期清理旧日志文件
2. **数据备份**: 定期备份采集的数据
3. **代理更新**: 定期更新代理池
4. **配置调优**: 根据实际表现调整参数

### 扩展功能
1. **数据验证**: 添加数据质量检查
2. **自动重试**: 增强失败重试机制
3. **分布式**: 支持多机器并行采集
4. **实时监控**: 集成 Prometheus/Grafana

## 📞 技术支持

如遇到问题，请提供：
1. 错误日志 (`logs/batch_collection.log`)
2. 进度文件 (`data/batch_cache/progress.json`)
3. 系统环境信息
4. 具体的错误复现步骤

---

**最后更新**: 2025-12-05
**版本**: v2.0
**维护者**: Data Engineering Team