"""
任务队列配置
生成时间：2025-10-26 20:57:22
"""

# Celery配置
CELERY_CONFIG = {
    "broker_url": "redis://localhost:6379/0",
    "result_backend": "redis://localhost:6379/1",
    "task_serializer": "json",
    "accept_content": ["json"],
    "result_serializer": "json",
    "timezone": "UTC",
    "enable_utc": True,
    "task_routes": {
        "predictions.tasks.*": {"queue": "prediction"},
        "data.collection.*": {"queue": "data_collection"},
        "monitoring.*": {"queue": "monitoring"},
        "notifications.*": {"queue": "notifications"}
    },
    "task_queues": {
        "prediction": {
            "exchange": "prediction",
            "routing_key": "prediction.task",
            "queue_arguments": {
                "x-max-retries": 3,
                "x-dead-letter-exchange": "celery",
                "x-message-ttl": 3600
            }
        },
        "data_collection": {
            "exchange": "data_collection",
            "routing_key": "data_collection.task",
            "queue_arguments": {
                "x-max-retries": 5,
                "x-dead-letter-exchange": "celery",
                "x-message-ttl": 7200
            }
        },
        "monitoring": {
            "exchange": "monitoring",
            "routing_key": "monitoring.task",
            "queue_arguments": {
                "x-max-retries": 1,
                "x-dead-letter-exchange": "celery",
                "x-message-ttl": 1800
            }
        },
        "notifications": {
            "exchange": "notifications",
            "routing_key": "notifications.task",
            "queue_arguments": {
                "x-max-retries": 2,
                "x-dead-letter-exchange": "celery",
                "x-message-ttl": 900
            }
        }
    },
    "worker_concurrency": 4,
    "worker_prefetch_multiplier": 1,
    "task_acks_late": True,
    "worker_max_tasks_per_child": 1000,
    "worker_max_memory_per_child": 10000
}

# 工作进程配置
WORKER_CONFIG = {
    "concurrency": 4,
    "prefetch_multiplier": 1,
    "max_tasks_per_child": 1000,
    "max_memory_per_child": 10000,
    "soft_time_limit": 300,
    "hard_time_limit": 600,
    "enable_utc": True,
    "optimize": False
}
