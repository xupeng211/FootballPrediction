# 深度项目清理报告

**清理时间**: 2025-10-04 00:58:38
**清理工具**: scripts/deep_cleanup.py

## 清理统计

| 类别 | 数量 |
|------|------|
| 临时文件 | 324 |
| 缓存目录 | 6 |
| 报告文件 | 6 |
| 日志文件 | 0 |
| 杂项文件 | 0 |
| **总计** | **336** |

## 空间优化

- 节省空间: 92.73 MB
- 归档位置: `.cleanup_archive/`

## 错误列表

- 删除缓存失败 /home/user/projects/FootballPrediction/.coverage: [Errno 20] Not a directory: PosixPath('/home/user/projects/FootballPrediction/.coverage')

## 建议

1. 定期运行 `python scripts/deep_cleanup.py` 清理项目
2. 使用 `python scripts/deep_cleanup.py --dry-run` 预览将要删除的文件
3. 检查 `.cleanup_archive/` 目录确认归档内容
