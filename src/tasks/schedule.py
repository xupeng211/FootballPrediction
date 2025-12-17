"""
Celery Beat 调度任务配置

配置定时任务，实现模型的自动重训练和系统维护。
"""

import logging
from celery import Celery
from celery.schedules import crontab

from src.config import get_settings
from src.services.mlops.retraining_service import RetrainingService

logger = logging.getLogger(__name__)

# 获取 Celery 实例
settings = get_settings()
celery_app = Celery('football_prediction')

# Celery 配置
celery_app.conf.update(
    broker_url=settings.redis_url,
    result_backend=settings.redis_url,
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30分钟超时
    task_soft_time_limit=25 * 60,  # 25分钟软超时
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# 调度配置
celery_app.conf.beat_schedule = {
    # 模型重训练任务 - 每周一凌晨 3:00 执行
    'train-new-model': {
        'task': 'src.tasks.schedule.train_new_model',
        'schedule': crontab(
            hour=3,
            minute=0,
            day_of_week=1  # 周一
        ),
        'options': {
            'queue': 'ml_training',
            'priority': 5,
        }
    },

    # 模型性能检查任务 - 每天早上 8:00 执行
    'check-model-performance': {
        'task': 'src.tasks.schedule.check_model_performance',
        'schedule': crontab(
            hour=8,
            minute=0
        ),
        'options': {
            'queue': 'monitoring',
            'priority': 3,
        }
    },

    # 数据质量检查任务 - 每天凌晨 2:00 执行
    'check-data-quality': {
        'task': 'src.tasks.schedule.check_data_quality',
        'schedule': crontab(
            hour=2,
            minute=0
        ),
        'options': {
            'queue': 'data_quality',
            'priority': 4,
        }
    },

    # 系统健康检查任务 - 每 15 分钟执行
    'system-health-check': {
        'task': 'src.tasks.schedule.system_health_check',
        'schedule': crontab(
            minute='*/15'
        ),
        'options': {
            'queue': 'monitoring',
            'priority': 2,
        }
    },

    # 清理旧模型任务 - 每月 1 号凌晨 4:00 执行
    'cleanup-old-models': {
        'task': 'src.tasks.schedule.cleanup_old_models',
        'schedule': crontab(
            hour=4,
            minute=0,
            day_of_month=1
        ),
        'options': {
            'queue': 'maintenance',
            'priority': 1,
        }
    },
}


@celery_app.task(bind=True, name='src.tasks.schedule.train_new_model')
def train_new_model(self, description: str = "Scheduled weekly training"):
    """
    定时模型重训练任务

    Args:
        description: 训练描述
    """
    logger.info(f"🚀 开始执行定时模型重训练任务: {description}")

    try:
        # 创建重训练服务
        retraining_service = RetrainingService()

        # 执行重训练流水线
        result = retraining_service.execute_pipeline(description)

        # 记录结果
        if result["status"] == "success":
            logger.info(
                f"✅ 模型重训练成功 - 版本: {result['version']}, "
                f"准确率: {result['metrics']['accuracy']:.4f}, "
                f"性能提升: {result['improvement']:.4f}"
            )
        elif result["status"] == "trained_not_deployed":
            logger.info(
                f"📊 模型训练完成但未部署 - 版本: {result['version']}, "
                f"准确率: {result['metrics']['accuracy']:.4f}, "
                f"性能提升: {result['improvement']:.4f} (未达到阈值 {result['threshold']:.4f})"
            )
        else:
            logger.error(f"❌ 模型重训练失败: {result.get('reason', 'Unknown error')}")

        return result

    except Exception as e:
        logger.error(f"❌ 定时模型重训练任务失败: {str(e)}", exc_info=True)
        raise


@celery_app.task(bind=True, name='src.tasks.schedule.check_model_performance')
def check_model_performance(self):
    """检查模型性能任务"""
    logger.info("🔍 开始检查模型性能")

    try:
        retraining_service = RetrainingService()
        status = retraining_service.get_training_status()

        if status["current_best"]:
            current_model = status["current_best"]
            logger.info(
                f"📊 当前最佳模型: {current_model['version']}, "
                f"准确率: {current_model['accuracy']:.4f}, "
                f"LogLoss: {current_model['log_loss']:.4f}"
            )

            # 检查是否需要性能告警
            if current_model["accuracy"] < 0.55:  # 准确率低于 55%
                logger.warning(
                    f"⚠️ 模型性能告警 - 准确率 {current_model['accuracy']:.4f} 低于阈值 0.55"
                )

        logger.info(f"📈 总模型数量: {status['total_models']}")

        return status

    except Exception as e:
        logger.error(f"❌ 模型性能检查失败: {str(e)}", exc_info=True)
        raise


@celery_app.task(bind=True, name='src.tasks.schedule.check_data_quality')
def check_data_quality(self):
    """数据质量检查任务"""
    logger.info("🔍 开始检查数据质量")

    try:
        from src.ml.data.postgres_loader import PostgreSQLDataLoader

        data_loader = PostgreSQLDataLoader()

        # 检查最近 7 天的数据
        recent_data = data_loader.load_recent_matches(days=7)

        quality_report = {
            "total_matches": len(recent_data),
            "missing_data_ratio": 0.0,
            "data_quality_score": 0.0,
            "issues": []
        }

        if len(recent_data) == 0:
            quality_report["issues"].append("最近7天无数据")
            quality_report["data_quality_score"] = 0.0
        else:
            # 计算缺失值比例
            missing_ratio = recent_data.isnull().sum().sum() / (
                len(recent_data) * len(recent_data.columns)
            )
            quality_report["missing_data_ratio"] = missing_ratio

            # 计算数据质量评分
            quality_score = 1.0
            if missing_ratio > 0.1:
                quality_score -= 0.3
                quality_report["issues"].append(f"缺失值比例过高: {missing_ratio:.2%}")

            if len(recent_data) < 100:
                quality_score -= 0.2
                quality_report["issues"].append(f"数据量不足: {len(recent_data)} 条")

            quality_report["data_quality_score"] = max(0.0, quality_score)

        logger.info(
            f"📊 数据质量检查完成 - "
            f"数据量: {quality_report['total_matches']}, "
            f"缺失值比例: {quality_report['missing_data_ratio']:.2%}, "
            f"质量评分: {quality_report['data_quality_score']:.2f}"
        )

        return quality_report

    except Exception as e:
        logger.error(f"❌ 数据质量检查失败: {str(e)}", exc_info=True)
        raise


@celery_app.task(bind=True, name='src.tasks.schedule.system_health_check')
def system_health_check(self):
    """系统健康检查任务"""
    logger.info("🔍 开始系统健康检查")

    try:
        import redis
        from src.database.connection import test_database_connection

        health_status = {
            "database": False,
            "redis": False,
            "model_service": False,
            "overall": False
        }

        # 检查数据库连接
        try:
            test_database_connection()
            health_status["database"] = True
            logger.info("✅ 数据库连接正常")
        except Exception as e:
            logger.warning(f"⚠️ 数据库连接异常: {str(e)}")

        # 检查 Redis 连接
        try:
            r = redis.from_url(settings.redis_url)
            r.ping()
            health_status["redis"] = True
            logger.info("✅ Redis 连接正常")
        except Exception as e:
            logger.warning(f"⚠️ Redis 连接异常: {str(e)}")

        # 检查模型服务
        try:
            retraining_service = RetrainingService()
            current_model = retraining_service.registry.get_current_best()
            health_status["model_service"] = current_model is not None
            if current_model:
                logger.info(f"✅ 模型服务正常 - 当前模型: {current_model.version}")
            else:
                logger.warning("⚠️ 无可用模型")
        except Exception as e:
            logger.warning(f"⚠️ 模型服务异常: {str(e)}")

        # 计算整体健康状态
        health_status["overall"] = all([
            health_status["database"],
            health_status["redis"],
            health_status["model_service"]
        ])

        if health_status["overall"]:
            logger.info("✅ 系统健康检查通过")
        else:
            logger.warning("⚠️ 系统健康检查发现问题")

        return health_status

    except Exception as e:
        logger.error(f"❌ 系统健康检查失败: {str(e)}", exc_info=True)
        raise


@celery_app.task(bind=True, name='src.tasks.schedule.cleanup_old_models')
def cleanup_old_models(self, keep_last_n: int = 10):
    """
    清理旧模型任务

    Args:
        keep_last_n: 保留最近的 N 个模型
    """
    logger.info(f"🧹 开始清理旧模型，保留最近 {keep_last_n} 个模型")

    try:
        from pathlib import Path

        retraining_service = RetrainingService()
        models = retraining_service.registry.list_models()

        if len(models) <= keep_last_n:
            logger.info("📊 模型数量未超过阈值，无需清理")
            return {
                "status": "no_action",
                "total_models": len(models),
                "keep_threshold": keep_last_n
            }

        # 按创建时间排序，删除最旧的模型
        models.sort(key=lambda x: x.created_at, reverse=True)
        models_to_keep = models[:keep_last_n]
        models_to_delete = models[keep_last_n:]

        deleted_count = 0
        for model in models_to_delete:
            try:
                # 删除模型文件
                model_file = Path(model.model_path)
                if model_file.exists():
                    model_file.unlink()
                    logger.info(f"🗑️ 已删除模型文件: {model_file}")

                # 从注册表中删除
                # 注意：这里需要更新注册表逻辑，暂时只记录日志
                logger.info(f"📋 应从注册表删除模型版本: {model.version}")
                deleted_count += 1

            except Exception as e:
                logger.error(f"❌ 删除模型 {model.version} 失败: {str(e)}")

        logger.info(f"✅ 模型清理完成，删除了 {deleted_count} 个旧模型")

        return {
            "status": "success",
            "total_models": len(models),
            "deleted_models": deleted_count,
            "remaining_models": len(models_to_keep)
        }

    except Exception as e:
        logger.error(f"❌ 模型清理任务失败: {str(e)}", exc_info=True)
        raise


# 手动触发任务
@celery_app.task(name='src.tasks.schedule.manual_retrain')
def manual_retrain(description: str = "Manual retraining trigger"):
    """手动触发模型重训练"""
    return train_new_model.s(description).apply()


# 紧急回滚任务
@celery_app.task(name='src.tasks.schedule.emergency_rollback')
def emergency_rollback(target_version: str):
    """紧急回滚到指定模型版本"""
    logger.info(f"🚨 开始紧急回滚到模型版本: {target_version}")

    try:
        retraining_service = RetrainingService()
        result = retraining_service.rollback_model(target_version)

        if result["status"] == "success":
            logger.info(f"✅ 紧急回滚成功: {result['message']}")
        else:
            logger.error(f"❌ 紧急回滚失败: {result.get('reason', 'Unknown error')}")

        return result

    except Exception as e:
        logger.error(f"❌ 紧急回滚任务失败: {str(e)}", exc_info=True)
        raise


# 启动 Celery Worker 和 Beat
if __name__ == '__main__':
    celery_app.start()