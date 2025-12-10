#!/usr/bin/env python3
"""
L2批处理作业生产配置
L2 Batch Job Production Configuration
安全、高效的批量数据采集配置
"""

import os
from typing import Dict, Any

# 生产环境配置 - 基于FotMob API限流要求
PRODUCTION_CONFIG = {
    # 速率控制 (安全第一)
    "max_concurrent": 8,           # 并发请求数 (保守设置)
    "timeout": 45,                  # 超时时间 (45秒)
    "max_retries": 3,               # 最大重试次数

    # 延迟配置 (避免被封禁)
    "base_delay": 2.5,              # 基础延迟 (2.5秒)
    "enable_jitter": True,          # 启用随机抖动

    # 代理配置 (暂时禁用以简化)
    "enable_proxy": False,          # 禁用代理 (稳定连接)

    # 批处理配置
    "batch_size": 500,              # 每批次处理数量
    "save_interval": 50,            # 每50场比赛保存一次
    "max_daily_requests": 15000,    # 每日最大请求数限制
}

# 监控配置
MONITORING_CONFIG = {
    "log_level": "INFO",
    "progress_report_interval": 10,  # 每10场比赛报告进度
    "stats_save_interval": 100,     # 每100场比赛保存统计
}

def get_config_for_environment(env: str = "production") -> dict[str, Any]:
    """根据环境获取配置"""
    if env.lower() == "development":
        # 开发环境 - 更激进的设置
        dev_config = PRODUCTION_CONFIG.copy()
        dev_config.update({
            "max_concurrent": 5,
            "base_delay": 1.5,
            "batch_size": 100,
        })
        return dev_config

    return PRODUCTION_CONFIG

if __name__ == "__main__":
    import json
    config = get_config_for_environment(os.getenv("ENV", "production"))
    print("🔧 L2批处理配置:")
    print(json.dumps(config, indent=2, ensure_ascii=False))
