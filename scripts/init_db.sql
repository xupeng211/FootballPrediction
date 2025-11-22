-- 足球预测系统数据库初始化脚本
-- 只创建必要的扩展，数据表由应用通过SQLAlchemy自动创建

-- 启用 UUID 生成扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 启用查询统计扩展（用于性能监控）
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- 注意：实际的表结构由 FastAPI 应用在启动时通过 SQLAlchemy 的 Base.metadata.create_all() 自动创建
-- 数据插入由应用的 entrypoint.sh 脚本处理
