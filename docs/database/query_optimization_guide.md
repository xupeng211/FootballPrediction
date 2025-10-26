"""
数据库查询优化指南
生成时间: 2025-10-26 20:57:22
"""

# 查询优化最佳实践
QUERY_OPTIMIZATION_TIPS = [
    "使用索引加速查询",
    "避免N+1查询问题",
    "使用批量操作替代循环查询",
    "合理使用JOIN避免过多表连接",
    "使用EXPLAIN分析查询计划",
    "限制返回字段减少数据传输",
    "使用事务提高批量操作效率"
]

# 索引优化建议
INDEX_OPTIMIZATION = [
    "为经常查询的字段创建索引",
    "为WHERE条件中的字段创建索引",
    "为ORDER BY字段创建索引",
    "避免过多索引影响写入性能",
    "定期分析索引使用情况",
    "使用复合索引优化多条件查询"
]

# 查询示例
OPTIMIZED_QUERIES = {
    "get_user_predictions": {
        "sql": "SELECT * FROM predictions WHERE user_id = ? ORDER BY created_at DESC LIMIT 10",
        "indexes": ["user_id", "created_at"],
        "tips": "用户ID和创建时间都应有索引"
    },
    "get_team_stats": {
        "sql": "SELECT COUNT(*) as total_matches, AVG(score) as avg_score FROM matches WHERE team_id = ?",
        "indexes": ["team_id"],
        "tips": "团队ID应有索引"
    }
}
