# 采集器 Dry-Run 测试报告

## 测试概览
- **数据源**: fotmob
- **测试时长**: 0.00秒
- **测试开始**: 2025-12-06 06:29:21 UTC

## 采集结果
- **赛程数据采集**: 0 场
- **比赛详情采集**: 0 场
- **球队信息采集**: 0 个
- **健康检查次数**: 1 次

## 监控统计

## 错误信息
1. 赛程采集失败: Failed to collect fixtures: Resource not found: https://www.fotmob.com/api/matches
2. 比赛详情采集失败: Failed to collect fixtures: Resource not found: https://www.fotmob.com/api/matches
3. 并发测试失败: Failed to register provider fotmob: Failed to get FotMob token: Network error while fetching FotMob homepage: Cannot connect to host www.fotmob.com:443 ssl:default [None]

## 测试配置
- **数据源**: fotmob
- **最大赛程数**: 2
- **最大比赛数**: 10
- **健康检查**: 启用
- **速率限制测试**: 禁用
- **代理使用**: 禁用
- **详细输出**: 禁用
