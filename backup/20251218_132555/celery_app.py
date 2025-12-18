#!/usr/bin/env python3
"""
Celery 应用入口

用于启动 Celery Worker 和 Beat 调度器。
"""

from src.tasks.schedule import celery_app

if __name__ == '__main__':
    celery_app.start()