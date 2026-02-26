# 数据同步服务运行指南

## 生产环境启动命令

```bash
PYTHONPATH=. python scripts/run_sync.py --workers 4 --debug
```

## 配置说明

- **网络弹性协议**: 默认开启指数退避重试 (Exponential Backoff)
- **速率限制**: 自动执行 3-7 秒随机交互延迟
- **并行控制**: 最大支持 4 个并发工作线程

## 参数选项

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--limit` | 限制处理的比赛数量（用于测试） | 全部 |
| `--workers` | 并发工作线程数（最大 4） | 4 |
| `--resume` | 从检查点恢复执行 | False |
| `--debug` | 启用调试日志（详细输出） | False |

## 示例命令

```bash
# 测试运行 5 场比赛
python scripts/run_sync.py --limit 5 --workers 2 --debug

# 全量收割
python scripts/run_sync.py --workers 4

# 从检查点恢复
python scripts/run_sync.py --resume
```

## 数据源映射

| ID | 名称 | 优先级 |
|----|------|--------|
| 18 | Entity_P (Pinnacle) | 1 |
| 16 | Entity_B (William Hill) | 2 |
| 7  | Entity_W (Bet365) | 3 |
| 2  | Entity_L (Ladbrokes) | 4 |
| avg | Entity_AVG (Average) | 5 |
