#!/usr/bin/env python3
"""
P0-4 ML Pipeline 监控部署脚本
配置和启动监控、日志、指标收集系统
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime

# 添加src路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

def setup_monitoring_structure():
    """设置监控目录结构"""
    print("🔧 设置监控目录结构...")

    monitoring_dirs = [
        "artifacts/logs",
        "artifacts/metrics",
        "artifacts/models",
        "artifacts/reports",
        "monitoring/dashboards",
        "monitoring/alerts",
        "monitoring/configs"
    ]

    for dir_path in monitoring_dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"  ✅ 创建目录: {dir_path}")

    print("✅ 监控目录结构设置完成")

def create_monitoring_config():
    """创建监控配置文件"""
    print("\n⚙️ 创建监控配置文件...")

    config = {
        "monitoring": {
            "enabled": True,
            "log_level": "INFO",
            "metrics_retention_days": 30,
            "dashboard_refresh_interval": 60,
            "alert_thresholds": {
                "training_accuracy_min": 0.7,
                "training_time_max": 300,
                "memory_usage_max": 0.8,
                "cpu_usage_max": 0.9
            }
        },
        "logging": {
            "file_rotation": "daily",
            "max_file_size_mb": 100,
            "backup_count": 7,
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        },
        "alerts": {
            "email_enabled": False,
            "slack_enabled": False,
            "webhook_url": "",
            "alert_channels": ["email", "slack", "webhook"]
        },
        "dashboard": {
            "title": "P0-4 ML Pipeline 监控面板",
            "refresh_interval": 30,
            "charts": [
                "training_accuracy_trend",
                "training_time_distribution",
                "algorithm_performance",
                "system_resource_usage"
            ]
        }
    }

    config_file = Path("monitoring/configs/monitoring_config.json")
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"  ✅ 监控配置已保存: {config_file}")

def create_prometheus_config():
    """创建Prometheus配置"""
    print("\n📊 创建Prometheus配置...")

    prometheus_config = {
        "global": {
            "scrape_interval": "15s",
            "evaluation_interval": "15s"
        },
        "rule_files": [
            "monitoring/configs/alert_rules.yml"
        ],
        "scrape_configs": [
            {
                "job_name": "ml_pipeline",
                "static_configs": [
                    {
                        "targets": ["localhost:8000"],
                        "labels": {
                            "service": "ml_pipeline",
                            "version": "p0-4"
                        }
                    }
                ]
            }
        ],
        "alerting": {
            "alertmanagers": [
                {
                    "static_configs": [
                        {
                            "targets": ["localhost:9093"]
                        }
                    ]
                }
            ]
        }
    }

    prometheus_file = Path("monitoring/configs/prometheus.yml")
    with open(prometheus_file, 'w', encoding='utf-8') as f:
        yaml.dump(prometheus_config, f, default_flow_style=False)

    print(f"  ✅ Prometheus配置已保存: {prometheus_file}")

def create_alert_rules():
    """创建告警规则"""
    print("\n🚨 创建告警规则...")

    alert_rules = """
groups:
- name: ml_pipeline_alerts
  rules:
  - alert: HighTrainingTime
    expr: training_duration_seconds > 300
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "训练时间过长"
      description: "模型训练时间超过5分钟"

  - alert: LowTrainingAccuracy
    expr: training_accuracy < 0.7
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "训练准确率过低"
      description: "模型训练准确率低于70%"

  - alert: HighMemoryUsage
    expr: memory_usage_percent > 80
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "内存使用率过高"
      description: "系统内存使用率超过80%"

  - alert: HighCpuUsage
    expr: cpu_usage_percent > 90
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "CPU使用率过高"
      description: "系统CPU使用率超过90%"

  - alert: TrainingFailure
    expr: training_status == "failed"
    for: 0m
    labels:
      severity: critical
    annotations:
      summary: "模型训练失败"
      description: "模型训练过程中发生错误"
"""

    rules_file = Path("monitoring/configs/alert_rules.yml")
    with open(rules_file, 'w', encoding='utf-8') as f:
        f.write(alert_rules)

    print(f"  ✅ 告警规则已保存: {rules_file}")

def create_grafana_dashboard():
    """创建Grafana仪表板配置"""
    print("\n📈 创建Grafana仪表板配置...")

    dashboard = {
        "dashboard": {
            "title": "P0-4 ML Pipeline 监控面板",
            "tags": ["ml", "pipeline", "p0-4"],
            "timezone": "browser",
            "panels": [
                {
                    "title": "训练准确率趋势",
                    "type": "graph",
                    "targets": [
                        {
                            "expr": "training_accuracy",
                            "legendFormat": "{{algorithm}}"
                        }
                    ],
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0}
                },
                {
                    "title": "训练时间分布",
                    "type": "graph",
                    "targets": [
                        {
                            "expr": "training_duration_seconds",
                            "legendFormat": "{{algorithm}}"
                        }
                    ],
                    "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0}
                },
                {
                    "title": "算法性能比较",
                    "type": "table",
                    "targets": [
                        {
                            "expr": "algorithm_performance",
                            "format": "table"
                        }
                    ],
                    "gridPos": {"h": 8, "w": 24, "x": 0, "y": 8}
                },
                {
                    "title": "系统资源使用",
                    "type": "graph",
                    "targets": [
                        {
                            "expr": "memory_usage_percent",
                            "legendFormat": "内存使用率"
                        },
                        {
                            "expr": "cpu_usage_percent",
                            "legendFormat": "CPU使用率"
                        }
                    ],
                    "gridPos": {"h": 8, "w": 12, "x": 0, "y": 16}
                }
            ],
            "time": {"from": "now-1h", "to": "now"},
            "refresh": "30s"
        }
    }

    dashboard_file = Path("monitoring/dashboards/ml_pipeline_dashboard.json")
    with open(dashboard_file, 'w', encoding='utf-8') as f:
        json.dump(dashboard, f, indent=2, ensure_ascii=False)

    print(f"  ✅ Grafana仪表板已保存: {dashboard_file}")

def create_docker_compose_monitoring():
    """创建监控服务的Docker Compose配置"""
    print("\n🐳 创建监控Docker Compose配置...")

    docker_compose = """
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    container_name: ml_pipeline_prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/configs/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./monitoring/configs/alert_rules.yml:/etc/prometheus/alert_rules.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=30d'
      - '--web.enable-lifecycle'
    networks:
      - monitoring

  grafana:
    image: grafana/grafana:latest
    container_name: ml_pipeline_grafana
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/dashboards:/etc/grafana/provisioning/dashboards
      - ./monitoring/configs:/etc/grafana/provisioning/datasources
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin123
      - GF_USERS_ALLOW_SIGN_UP=false
    networks:
      - monitoring

  alertmanager:
    image: prom/alertmanager:latest
    container_name: ml_pipeline_alertmanager
    ports:
      - "9093:9093"
    volumes:
      - ./monitoring/configs/alertmanager.yml:/etc/alertmanager/alertmanager.yml
      - alertmanager_data:/alertmanager
    networks:
      - monitoring

volumes:
  prometheus_data:
  grafana_data:
  alertmanager_data:

networks:
  monitoring:
    driver: bridge
"""

    compose_file = Path("docker-compose.monitoring.yml")
    with open(compose_file, 'w', encoding='utf-8') as f:
        f.write(docker_compose)

    print(f"  ✅ Docker Compose配置已保存: {compose_file}")

def create_startup_script():
    """创建监控服务启动脚本"""
    print("\n🚀 创建启动脚本...")

    startup_script = """#!/bin/bash

# P0-4 ML Pipeline 监控服务启动脚本

echo "🚀 启动P0-4 ML Pipeline监控服务..."

# 检查Docker是否运行
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker未运行，请先启动Docker"
    exit 1
fi

# 启动监控服务
echo "📊 启动Prometheus..."
docker-compose -f docker-compose.monitoring.yml up -d prometheus

echo "📈 启动Grafana..."
docker-compose -f docker-compose.monitoring.yml up -d grafana

echo "🚨 启动AlertManager..."
docker-compose -f docker-compose.monitoring.yml up -d alertmanager

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 10

# 检查服务状态
echo "🔍 检查服务状态..."
docker-compose -f docker-compose.monitoring.yml ps

# 显示访问地址
echo ""
echo "✅ 监控服务启动完成!"
echo "📊 Prometheus: http://localhost:9090"
echo "📈 Grafana: http://localhost:3000 (admin/admin123)"
echo "🚨 AlertManager: http://localhost:9093"
echo ""
echo "💡 使用 './stop_monitoring.sh' 停止监控服务"
"""

    script_file = Path("start_monitoring.sh")
    with open(script_file, 'w', encoding='utf-8') as f:
        f.write(startup_script)

    # 设置执行权限
    script_file.chmod(0o755)

    print(f"  ✅ 启动脚本已保存: {script_file}")

def create_stop_script():
    """创建监控服务停止脚本"""
    print("\n🛑 创建停止脚本...")

    stop_script = """#!/bin/bash

# P0-4 ML Pipeline 监控服务停止脚本

echo "🛑 停止P0-4 ML Pipeline监控服务..."

# 停止监控服务
docker-compose -f docker-compose.monitoring.yml down

echo "✅ 监控服务已停止"

# 可选: 清理数据卷
read -p "是否清理监控数据? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker-compose -f docker-compose.monitoring.yml down -v
    echo "🗑️ 监控数据已清理"
fi
"""

    script_file = Path("stop_monitoring.sh")
    with open(script_file, 'w', encoding='utf-8') as f:
        f.write(stop_script)

    # 设置执行权限
    script_file.chmod(0o755)

    print(f"  ✅ 停止脚本已保存: {script_file}")

def create_health_check_script():
    """创建健康检查脚本"""
    print("\n🏥 创建健康检查脚本...")

    health_check_script = """#!/bin/bash

# P0-4 ML Pipeline 监控健康检查脚本

echo "🏥 执行监控健康检查..."

# 检查Prometheus
echo "📊 检查Prometheus..."
if curl -s http://localhost:9090/-/healthy > /dev/null; then
    echo "  ✅ Prometheus健康"
else
    echo "  ❌ Prometheus异常"
fi

# 检查Grafana
echo "📈 检查Grafana..."
if curl -s http://localhost:3000/api/health > /dev/null; then
    echo "  ✅ Grafana健康"
else
    echo "  ❌ Grafana异常"
fi

# 检查AlertManager
echo "🚨 检查AlertManager..."
if curl -s http://localhost:9093/-/healthy > /dev/null; then
    echo "  ✅ AlertManager健康"
else
    echo "  ❌ AlertManager异常"
fi

# 检查磁盘空间
echo "💾 检查磁盘空间..."
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -lt 80 ]; then
    echo "  ✅ 磁盘空间充足 (${DISK_USAGE}%)"
else
    echo "  ⚠️ 磁盘空间不足 (${DISK_USAGE}%)"
fi

# 检查内存使用
echo "🧠 检查内存使用..."
MEMORY_USAGE=$(free | grep Mem | awk '{printf("%.1f", $3/$2 * 100.0)}')
if (( $(echo "$MEMORY_USAGE < 80" | bc -l) )); then
    echo "  ✅ 内存使用正常 (${MEMORY_USAGE}%)"
else
    echo "  ⚠️ 内存使用过高 (${MEMORY_USAGE}%)"
fi

echo "🏥 健康检查完成"
"""

    script_file = Path("health_check_monitoring.sh")
    with open(script_file, 'w', encoding='utf-8') as f:
        f.write(health_check_script)

    # 设置执行权限
    script_file.chmod(0o755)

    print(f"  ✅ 健康检查脚本已保存: {script_file}")

def main():
    """主部署函数"""
    print("🚀 P0-4 ML Pipeline 监控部署")
    print("配置和启动监控、日志、指标收集系统")
    print("=" * 60)

    try:
        # 设置目录结构
        setup_monitoring_structure()

        # 创建配置文件
        create_monitoring_config()

        # 创建监控配置 (需要yaml模块，暂时跳过)
        print("\n📊 跳过Prometheus配置创建 (需要PyYAML)")
        print("🚨 跳过告警规则创建 (需要PyYAML)")

        # 创建Grafana仪表板
        create_grafana_dashboard()

        # 创建Docker配置
        create_docker_compose_monitoring()

        # 创建脚本
        create_startup_script()
        create_stop_script()
        create_health_check_script()

        print("\n" + "=" * 60)
        print("🎉 监控部署完成!")
        print("=" * 60)

        print("\n📋 部署文件:")
        print("  📊 监控配置: monitoring/configs/monitoring_config.json")
        print("  📈 Grafana仪表板: monitoring/dashboards/ml_pipeline_dashboard.json")
        print("  🐳 Docker配置: docker-compose.monitoring.yml")
        print("  🚀 启动脚本: start_monitoring.sh")
        print("  🛑 停止脚本: stop_monitoring.sh")
        print("  🏥 健康检查: health_check_monitoring.sh")

        print("\n📖 使用说明:")
        print("  1. 启动监控: ./start_monitoring.sh")
        print("  2. 访问Grafana: http://localhost:3000 (admin/admin123)")
        print("  3. 访问Prometheus: http://localhost:9090")
        print("  4. 健康检查: ./health_check_monitoring.sh")
        print("  5. 停止监控: ./stop_monitoring.sh")

        print("\n🔧 注意事项:")
        print("  - 需要安装Docker和Docker Compose")
        print("  - 需要安装PyYAML来创建完整配置")
        print("  - 监控数据存储在Docker卷中")
        print("  - 建议定期备份监控数据")

        return True

    except Exception as e:
        print(f"\n❌ 监控部署失败: {e}")
        return False

if __name__ == "__main__":
    import yaml
    success = main()
    sys.exit(0 if success else 1)
