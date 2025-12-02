# MLOps每日数据管道部署指南

## 🎯 概述

完全自动化的ML数据管道，每天凌晨4点自动完成：
1. **数据提取** - 采集最新比赛数据
2. **数据加载** - 入库到PostgreSQL
3. **实体解析** - 自动处理新球队映射
4. **特征工程** - 更新训练特征
5. **数据导出** - 生成最新训练集

## 🚀 快速部署

### 1. 安装Crontab
```bash
chmod +x scripts/install_crontab.sh
./scripts/install_crontab.sh
```

### 2. 验证安装
```bash
crontab -l
```

应该看到类似这样的输出：
```
0 4 * * * cd /home/user/projects/FootballPrediction && /usr/bin/python3 scripts/run_daily_pipeline.py >> logs/cron_pipeline.log 2>&1
```

## 📊 管道架构

### DAG流程图
```
每日凌晨4点触发
    ↓
[Stage 1] 数据提取
    ↓
[Stage 2] 数据加载
    ↓
[Stage 3] 自动实体解析
    ↓
[Stage 4] 特征工程
    ↓
[Stage 5] 数据导出
    ↓
✅ 最新训练集就绪
```

### 关键组件

#### AutoEntityResolver
- **高置信度匹配** (>95%): 自动映射现有球队
- **低置信度匹配** (85-95%): 自动映射但记录警告
- **新球队检测**: 自动插入新球队，标记为新实体

#### DailyPipelineOrchestrator
- 5阶段有向无环图(DAG)执行
- 容错设计：单阶段失败不中断整体流程
- 详细日志和报告生成

## 📁 输出文件

### 每日生成
- `logs/daily_pipeline.log` - 管道执行日志
- `logs/daily_pipeline_report.json` - 详细执行报告
- `data/training_sets/training_set_v1_YYYYMMDD_HHMMSS.csv` - 版本化训练集
- `data/training_sets/latest_training_set.csv` - 最新训练集软链接

### 每周生成（可选）
- `models/v1_xgboost_model.json` - 重训练的模型
- `results/feature_importance_v1.png` - 特征重要性图

## 🔧 手动执行

### 完整管道
```bash
python scripts/run_daily_pipeline.py
```

### 单独组件测试
```bash
# 测试自动实体解析器
python src/ml_ops/auto_entity_resolver.py

# 测试特征工程
python scripts/build_v1_dataset.py

# 测试模型训练
python src/models/train_v1_xgboost.py
```

## 📊 监控和维护

### 查看执行状态
```bash
# 查看今天的管道日志
tail -f logs/daily_pipeline.log

# 查看最新的执行报告
cat logs/daily_pipeline_report.json | jq .

# 查看crontab执行历史
grep "CRON" /var/log/syslog | tail -10
```

### 故障排除
```bash
# 手动运行管道
python scripts/run_daily_pipeline.py

# 检查数据库连接
docker-compose exec db psql -U postgres -d football_prediction -c "SELECT COUNT(*) FROM matches;"

# 检查磁盘空间
df -h

# 重启crontab服务
sudo service cron restart
```

## 🎯 期望效果

### 用户视角
每天早上醒来时：
- ✅ 最新比赛数据已自动采集
- ✅ 新球队已自动识别和映射
- ✅ 特征工程已更新
- ✅ 最新训练集已在 `data/training_sets/latest_training_set.csv`
- ✅ 无需任何人工干预

### 技术指标
- **执行时间**: ~5分钟（取决于数据量）
- **成功率**: >95%（自动重试机制）
- **数据质量**: 实体解析准确率 >95%
- **维护成本**: 接近零

## 🔐 安全考虑

- 所有数据库操作使用只读权限进行检测
- 新球队插入使用最小权限
- 详细审计日志记录所有操作
- 自动备份机制（可配置）

## 📈 扩展性

### 添加新Stage
1. 在 `DailyPipelineOrchestrator` 中添加新方法
2. 更新 `run_pipeline()` 中的stages列表
3. 添加相应的错误处理和报告

### 支持多数据源
- 扩展 `AutoEntityResolver` 支持更多映射规则
- 添加配置文件支持不同的数据源策略
- 实现数据质量检查和告警

## 📞 联系支持

如遇问题，请检查：
1. `logs/daily_pipeline.log` - 管道执行日志
2. `logs/cron_pipeline.log` - Crontab执行日志
3. `logs/daily_pipeline_report.json` - 详细执行报告

---

**构建者**: MLOps首席架构师
**最后更新**: 2025-12-02
**版本**: v1.0