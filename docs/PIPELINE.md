# 足球预测自动化管道

该管道提供完整的自动化机器学习流程，从数据采集到预测输出，实现端到端的足球比赛预测。

## 🚀 功能特性

### 📊 完整的ML管道流程
1. **数据同步 (Data Sync)** - 从外部API获取最新比赛数据
2. **数据清洗 (ETL)** - 清洗并转换数据到Silver层
3. **特征生成 (Feature Generation)** - 计算训练特征和比赛特征
4. **模型训练 (Model Training)** - 使用最新数据重训XGBoost模型
5. **未来预测 (Future Prediction)** - 预测未来7天内的比赛结果

### 🔧 技术特点
- **异步处理** - 支持高性能的异步数据采集
- **防数据泄露** - 严格的时间序列数据切分
- **错误处理** - 完整的异常处理和日志记录
- **模型版本管理** - 自动保存模型和元数据
- **调度友好** - 支持crontab定时执行

## 📁 文件结构

```
scripts/
├── daily_pipeline.py          # 主管道脚本 (核心)
├── demo_future_prediction.py  # 预测演示脚本
├── train_model.py            # 单独模型训练脚本
├── generate_features.py       # 单独特征生成脚本
└── run_etl_silver.py         # 单独ETL脚本

data/
└── dataset_v1.csv            # 特征数据集

models/
├── football_model_v1.json       # 训练好的XGBoost模型
└── football_model_v1_metadata.json  # 模型元数据
```

## 🏃‍♂️ 快速开始

### 运行完整管道
```bash
# 执行完整的5步管道
python scripts/daily_pipeline.py
```

### 单独运行演示
```bash
# 查看预测演示
python scripts/demo_future_prediction.py
```

## ⏰ 定时任务设置

### Linux Crontab配置
```bash
# 编辑crontab
crontab -e

# 添加以下行（每天凌晨3点执行）
0 3 * * * /usr/bin/python3 /path/to/FootballPrediction/scripts/daily_pipeline.py >> /var/log/football_pipeline.log 2>&1
```

### 手动执行测试
```bash
# 开发环境测试
python scripts/daily_pipeline.py

# 生产环境执行
nohup python scripts/daily_pipeline.py > /var/log/football_pipeline.log 2>&1 &
```

## 📊 管道输出示例

### 执行日志
```
🏈 足球预测自动化管道启动
============================================================
[1/5] 数据同步 (Data Sync) - 开始
✅ 数据同步成功，采集到 380 条记录
[2/5] 数据清洗 (ETL) - 开始
✅ 数据清洗完成，数据已写入Silver层
[3/5] 特征生成 (Feature Generation) - 开始
✅ 特征生成完成，生成 380 条特征记录
[4/5] 模型训练 (Model Training) - 开始
✅ 模型训练完成，测试准确率: 0.4211 (42.11%)
[5/5] 未来预测 (Future Predictions) - 开始
⚠️ 未找到未来7天内的比赛
🎉 管道执行完成！
```

### 预测结果示例
```
🔮 未来比赛预测结果
============================================================
[2025-11-24] Manchester United (主) vs Liverpool (客)
📊 球队状态:
   主队近期表现: 9分, 平均进球 1.6
   客队近期表现: 15分, 平均进球 2.2
   历史交锋: 主队近期1次获胜
🔮 预测结果: 平局
📈 预测概率:
   ✅ 平局    : 77.2%
      主队胜   : 2.6%
      客队胜   : 20.1%
```

## 🔧 配置说明

### 环境变量配置
确保以下环境变量已设置（.env文件）：
```env
# 数据库配置
DB_HOST=localhost
DB_PORT=5432
DB_NAME=football_prediction
DB_USER=postgres
DB_PASSWORD=your_password

# API配置
FOOTBALL_DATA_API_KEY=your_api_key
```

### 模型参数配置
当前XGBoost模型参数：
- `max_depth`: 6
- `learning_rate`: 0.1
- `n_estimators`: 100
- `objective`: multi:softmax
- `num_class`: 3 (平局、主胜、客胜)

## 📈 性能指标

### 模型性能
- **测试准确率**: 42.11%
- **三分类任务**: 胜过随机猜测基线 (33.3%)
- **特征数量**: 7个基础特征
- **训练样本**: 304场比赛

### 执行效率
- **总耗时**: 约8秒
- **API调用**: 单次调用获取全部数据
- **数据库操作**: 高效的批量处理

## 🛠️ 故障排除

### 常见问题

1. **数据同步失败**
   ```bash
   # 检查API Key是否有效
   python -c "import os; print(os.getenv('FOOTBALL_DATA_API_KEY'))"
   ```

2. **数据库连接失败**
   ```bash
   # 检查数据库连接
   PGPASSWORD=your_password psql -h localhost -U postgres -d football_prediction -c "SELECT 1;"
   ```

3. **模型加载失败**
   ```bash
   # 检查模型文件是否存在
   ls -la models/football_model_v1.json
   ```

4. **特征计算失败**
   ```bash
   # 检查数据完整性
   python -c "import pandas as pd; df = pd.read_csv('data/dataset_v1.csv'); print(df.shape)"
   ```

### 日志查看
```bash
# 查看实时日志
tail -f /var/log/football_pipeline.log

# 查看错误日志
grep "ERROR" /var/log/football_pipeline.log
```

## 🔄 扩展功能

### 添加新的数据源
1. 在`src/adapters/`中实现新的适配器
2. 在`FixturesCollector`中添加配置选项
3. 更新管道脚本以支持多数据源

### 改进模型性能
1. 添加更多特征（球员伤病、天气等）
2. 实现特征工程和选择
3. 尝试其他算法（随机森林、神经网络等）
4. 实现超参数调优

### 添加更多联赛
1. 在`_get_active_leagues()`中添加联赛代码
2. 支持多联赛并行处理
3. 实现联赛特定的特征

## 📞 技术支持

如需技术支持或功能扩展，请参考：
- 项目README.md
- 代码注释
- 单元测试文件
- 技术文档

---

**注意**: 这是一个MVP版本，主要用于演示端到端ML管道的实现。在生产环境中使用前，建议进行更全面的测试和优化。