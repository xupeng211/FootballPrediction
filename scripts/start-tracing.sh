#!/bin/bash

# 分布式追踪系统启动脚本
# Football Prediction Project

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# 检查系统要求
check_requirements() {
    log_step "检查系统要求..."

    # 检查Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装，请先安装Docker"
        exit 1
    fi

    # 检查Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose未安装，请先安装Docker Compose"
        exit 1
    fi

    # 检查monitoring网络
    if ! docker network ls | grep -q monitoring; then
        log_warn "monitoring网络不存在，将创建新网络"
        docker network create monitoring
    fi

    log_info "系统要求检查通过"
}

# 创建必要的目录
create_directories() {
    log_step "创建必要的目录..."

    local dirs=(
        "monitoring/tracing"
        "monitoring/data/jaeger"
        "monitoring/data/otel-collector"
        "logs/tracing"
    )

    for dir in "${dirs[@]}"; do
        mkdir -p "$dir"
        log_info "创建目录: $dir"
    done
}

# 生成环境配置
generate_env_config() {
    log_step "生成环境配置..."

    cat > .env.tracing <<EOF
# 分布式追踪环境配置

# 服务配置
SERVICE_NAME=football-prediction
SERVICE_VERSION=1.0.0
ENVIRONMENT=production

# 追踪配置
TRACING_ENABLED=true
TRACE_SAMPLE_RATE=0.1

# Jaeger配置
JAEGER_ENABLED=true
JAEGER_ENDPOINT=http://jaeger:14268/api/traces
JAEGER_UI_ENDPOINT=http://localhost:16686

# Zipkin配置
ZIPKIN_ENABLED=false
ZIPKIN_ENDPOINT=http://zipkin:9411/api/v2/spans

# OpenTelemetry配置
OTLP_ENABLED=true
OTLP_ENDPOINT=http://otel-collector:4317

# 自动插桩配置
OTEL_INSTRUMENT_FASTAPI=true
OTEL_INSTRUMENT_SQLALCHEMY=true
OTEL_INSTRUMENT_REDIS=true
OTEL_INSTRUMENT_HTTPX=true
OTEL_INSTRUMENT_CELERY=true

# 性能监控
PERFORMANCE_WARNING_THRESHOLD=1.0

# 导出器配置
OTEL_EXPORTER_JAEGER_ENDPOINT=http://jaeger:14250
OTEL_EXPORTER_JAEGER_PROTOCOL=grpc
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
OTEL_EXPORTER_OTLP_PROTOCOL=grpc
EOF

    log_info "环境配置已生成: .env.tracing"
}

# 更新应用配置
update_app_config() {
    log_step "更新应用配置..."

    # 更新主docker-compose.yml添加追踪环境变量
    if [[ -f docker-compose.yml ]]; then
        # 备份原文件
        cp docker-compose.yml docker-compose.yml.backup

        # 添加追踪环境变量
        cat > tmp-env.yml <<EOF
# 追踪环境变量
x-tracing-env: &tracing-env
  SERVICE_NAME: football-prediction
  SERVICE_VERSION: \${SERVICE_VERSION:-1.0.0}
  ENVIRONMENT: \${ENVIRONMENT:-production}
  TRACING_ENABLED: \${TRACING_ENABLED:-true}
  TRACE_SAMPLE_RATE: \${TRACE_SAMPLE_RATE:-0.1}
  JAEGER_ENDPOINT: \${JAEGER_ENDPOINT:-http://jaeger:14268/api/traces}
  ZIPKIN_ENDPOINT: \${ZIPKIN_ENDPOINT:-http://zipkin:9411/api/v2/spans}
  OTLP_ENDPOINT: \${OTLP_ENDPOINT:-http://otel-collector:4317}
  OTEL_INSTRUMENT_FASTAPI: \${OTEL_INSTRUMENT_FASTAPI:-true}
  OTEL_INSTRUMENT_SQLALCHEMY: \${OTEL_INSTRUMENT_SQLALCHEMY:-true}
  OTEL_INSTRUMENT_REDIS: \${OTEL_INSTRUMENT_REDIS:-true}
  OTEL_INSTRUMENT_HTTPX: \${OTEL_INSTRUMENT_HTTPX:-true}
  OTEL_INSTRUMENT_CELERY: \${OTEL_INSTRUMENT_CELERY:-true}
  OTEL_EXPORTER_JAEGER_ENDPOINT: \${OTEL_EXPORTER_JAEGER_ENDPOINT:-http://jaeger:14250}
  OTEL_EXPORTER_OTLP_ENDPOINT: \${OTEL_EXPORTER_OTLP_ENDPOINT:-http://otel-collector:4317}
EOF

        log_info "应用配置模板已创建"
    else
        log_warn "未找到docker-compose.yml文件"
    fi
}

# 启动服务
start_services() {
    log_step "启动分布式追踪服务..."

    # 加载环境变量
    if [[ -f .env.tracing ]]; then
        export $(cat .env.tracing | grep -v '^#' | xargs)
    fi

    # 使用docker-compose启动服务
    if command -v docker-compose &> /dev/null; then
        COMPOSE_CMD="docker-compose"
    else
        COMPOSE_CMD="docker compose"
    fi

    # 启动追踪服务
    $COMPOSE_CMD -f docker-compose.tracing.yml up -d

    log_info "等待服务启动..."
    sleep 20
}

# 检查服务状态
check_services() {
    log_step "检查服务状态..."

    local services=(
        "jaeger:16686"
        "otel-collector:4317"
        "zipkin:9411"
    )

    for service in "${services[@]}"; do
        local name=$(echo "$service" | cut -d: -f1)
        local port=$(echo "$service" | cut -d: -f2)

        if curl -s "http://localhost:$port" > /dev/null; then
            log_info "✓ $name 服务运行正常 (端口: $port)"
        else
            log_error "✗ $name 服务启动失败 (端口: $port)"
        fi
    done
}

# 配置Grafana追踪仪表板
configure_grafana() {
    log_step "配置Grafana追踪仪表板..."

    # 创建Jaeger数据源配置
    cat > monitoring/grafana/provisioning/datasources/jaeger.yaml <<EOF
apiVersion: 1

datasources:
  - name: Jaeger
    type: jaeger
    access: proxy
    url: http://jaeger:16686
    editable: true
    jsonData:
      tracesToLogs:
        datasourceUid: 'loki'
        tags: ['job', 'instance', 'pod', 'namespace']
        mappedTags: [
          { key: 'service.name', value: 'service' }
        ]
        mapTagNamesEnabled: false
        spanStartTimeShift: '1h'
        spanEndTimeShift: '1h'
        filterByTraceID: false
        filterBySpanID: false
EOF

    # 创建Tempo数据源配置（如果使用Tempo）
    cat > monitoring/grafana/provisioning/datasources/tempo.yaml <<EOF
apiVersion: 1

datasources:
  - name: Tempo
    type: tempo
    access: proxy
    url: http://tempo:3200
    editable: true
EOF

    log_info "Grafana追踪数据源配置已更新"
}

# 创建追踪仪表板
create_tracing_dashboard() {
    log_step "创建追踪仪表板..."

    cat > monitoring/grafana/dashboards/tracing-overview.json <<'EOF'
{
  "annotations": {
    "list": [
      {
        "builtIn": 1,
        "datasource": "-- Grafana --",
        "enable": true,
        "hide": true,
        "iconColor": "rgba(0, 211, 255, 1)",
        "name": "Annotations & Alerts",
        "type": "dashboard"
      }
    ]
  },
  "editable": true,
  "gnetId": null,
  "graphTooltip": 0,
  "id": null,
  "links": [],
  "panels": [
    {
      "datasource": "Jaeger",
      "fieldConfig": {
        "defaults": {
          "custom": {
            "linkType": "explorer"
          },
          "mappings": []
        },
        "overrides": []
      },
      "gridPos": {
        "h": 16,
        "w": 24,
        "x": 0,
        "y": 0
      },
      "id": 1,
      "options": {
        "legend": false,
        "query": "",
        "service": "",
        "tags": []
      },
      "targets": [
        {
          "refId": "A",
          "datasource": {
            "type": "jaeger",
            "uid": "jaeger"
          }
        }
      ],
      "title": "Distributed Traces",
      "type": "tracing"
    },
    {
      "datasource": "Prometheus",
      "fieldConfig": {
        "defaults": {
          "color": {
            "mode": "palette-classic"
          },
          "custom": {
            "axisLabel": "",
            "axisPlacement": "auto",
            "barAlignment": 0,
            "drawStyle": "line",
            "fillOpacity": 10,
            "gradientMode": "none",
            "hideFrom": {
              "legend": false,
              "tooltip": false,
              "vis": false
            },
            "lineInterpolation": "linear",
            "lineWidth": 1,
            "pointSize": 5,
            "scaleDistribution": {
              "type": "linear"
            },
            "showPoints": "never",
            "spanNulls": false,
            "stacking": {
              "group": "A",
              "mode": "none"
            },
            "thresholdsStyle": {
              "mode": "off"
            }
          },
          "mappings": [],
          "thresholds": {
            "mode": "absolute",
            "steps": [
              {
                "color": "green",
                "value": null
              },
              {
                "color": "red",
                "value": 80
              }
            ]
          },
          "unit": "reqps"
        },
        "overrides": []
      },
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 0,
        "y": 16
      },
      "id": 2,
      "options": {
        "legend": {
          "calcs": [],
          "displayMode": "list",
          "placement": "bottom"
        },
        "tooltip": {
          "mode": "single"
        }
      },
      "targets": [
        {
          "expr": "rate(span_duration_seconds_sum[5m])",
          "interval": "",
          "legendFormat": "{{service_name}}",
          "refId": "A"
        }
      ],
      "title": "Request Rate",
      "type": "timeseries"
    },
    {
      "datasource": "Prometheus",
      "fieldConfig": {
        "defaults": {
          "color": {
            "mode": "palette-classic"
          },
          "custom": {
            "axisLabel": "",
            "axisPlacement": "auto",
            "barAlignment": 0,
            "drawStyle": "line",
            "fillOpacity": 10,
            "gradientMode": "none",
            "hideFrom": {
              "legend": false,
              "tooltip": false,
              "vis": false
            },
            "lineInterpolation": "linear",
            "lineWidth": 1,
            "pointSize": 5,
            "scaleDistribution": {
              "type": "linear"
            },
            "showPoints": "never",
            "spanNulls": false,
            "stacking": {
              "group": "A",
              "mode": "none"
            },
            "thresholdsStyle": {
              "mode": "line"
            }
          },
          "mappings": [],
          "thresholds": {
            "mode": "absolute",
            "steps": [
              {
                "color": "green",
                "value": null
              },
              {
                "color": "red",
                "value": 80
              }
            ]
          },
          "unit": "s"
        },
        "overrides": []
      },
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 12,
        "y": 16
      },
      "id": 3,
      "options": {
        "legend": {
          "calcs": [],
          "displayMode": "list",
          "placement": "bottom"
        },
        "tooltip": {
          "mode": "single"
        }
      },
      "targets": [
        {
          "expr": "histogram_quantile(0.95, rate(span_duration_seconds_bucket[5m]))",
          "interval": "",
          "legendFormat": "95th percentile - {{service_name}}",
          "refId": "A"
        }
      ],
      "title": "Response Time (95th percentile)",
      "type": "timeseries"
    }
  ],
  "schemaVersion": 27,
  "style": "dark",
  "tags": [
    "tracing",
    "distributed-tracing"
  ],
  "templating": {
    "list": []
  },
  "time": {
    "from": "now-1h",
    "to": "now"
  },
  "timepicker": {},
  "timezone": "",
  "title": "Distributed Tracing Overview",
  "uid": "tracing-overview",
  "version": 1
}
EOF

    log_info "追踪仪表板已创建"
}

# 显示访问信息
show_access_info() {
    log_step "显示访问信息..."

    echo ""
    echo "==========================================="
    echo "分布式追踪系统已成功启动！"
    echo "==========================================="
    echo ""
    echo "访问地址："
    echo "  • Jaeger UI:   http://localhost:16686"
    echo "  • Zipkin UI:   http://localhost:9411"
    echo "  • Grafana:     http://localhost:3000"
    echo ""
    echo "查看追踪："
    echo "  1. 访问Jaeger UI"
    echo "  2. 选择服务名称"
    echo "  3. 点击'Find Traces'查看追踪"
    echo ""
    echo "集成到应用："
    echo "  1. 安装依赖: pip install opentelemetry-api opentelemetry-sdk"
    echo "  2. 在应用中初始化: from src.core.tracing import init_tracing; init_tracing()"
    echo "  3. 使用装饰器: @trace_span('operation_name')"
    echo ""
    echo "管理命令："
    echo "  • 查看日志: docker-compose -f docker-compose.tracing.yml logs -f [service]"
    echo "  • 停止服务: docker-compose -f docker-compose.tracing.yml down"
    echo "  • 重启服务: docker-compose -f docker-compose.tracing.yml restart [service]"
    echo ""
}

# 创建Python依赖文件
create_requirements() {
    log_step "创建Python依赖文件..."

    cat > requirements/tracing.txt <<EOF
# OpenTelemetry核心库
opentelemetry-api==1.21.0
opentelemetry-sdk==1.21.0
opentelemetry-instrumentation==0.42b0

# 导出器
opentelemetry-exporter-jaeger==1.21.0
opentelemetry-exporter-zipkin==1.21.0
opentelemetry-exporter-otlp==1.21.0

# 自动插桩
opentelemetry-instrumentation-fastapi==0.42b0
opentelemetry-instrumentation-sqlalchemy==0.42b0
opentelemetry-instrumentation-redis==0.42b0
opentelemetry-instrumentation-httpx==0.42b0
opentelemetry-instrumentation-celery==0.42b0

# 支持库
opentelemetry-semantic-conventions==0.42b0
opentelemetry-propagator-b3==1.21.0
opentelemetry-propagator-jaeger==1.21.0
EOF

    log_info "追踪依赖文件已创建: requirements/tracing.txt"
}

# 主函数
main() {
    echo ""
    echo "==========================================="
    echo "Football Prediction - 分布式追踪启动脚本"
    echo "==========================================="
    echo ""

    # 检查是否为root用户
    if [[ $EUID -eq 0 ]]; then
        log_error "请不要以root用户运行此脚本"
        exit 1
    fi

    # 执行步骤
    check_requirements
    create_directories
    generate_env_config
    update_app_config
    start_services
    check_services
    configure_grafana
    create_tracing_dashboard
    create_requirements
    show_access_info

    log_info "分布式追踪系统启动完成！"
}

# 处理命令行参数
case "${1:-start}" in
    start)
        main
        ;;
    stop)
        log_step "停止分布式追踪服务..."
        docker-compose -f docker-compose.tracing.yml down
        log_info "服务已停止"
        ;;
    restart)
        log_step "重启分布式追踪服务..."
        docker-compose -f docker-compose.tracing.yml restart
        log_info "服务已重启"
        ;;
    logs)
        docker-compose -f docker-compose.tracing.yml logs -f "${2:-}"
        ;;
    status)
        check_services
        ;;
    test)
        log_step "测试追踪功能..."
        curl -X POST http://localhost:14268/api/traces -H "Content-Type: application/json" -d '{}'
        log_info "测试追踪已发送"
        ;;
    *)
        echo "用法: $0 {start|stop|restart|logs|status|test}"
        echo ""
        echo "命令说明："
        echo "  start   - 启动分布式追踪系统"
        echo "  stop    - 停止分布式追踪系统"
        echo "  restart - 重启分布式追踪系统"
        echo "  logs    - 查看服务日志"
        echo "  status  - 检查服务状态"
        echo "  test    - 发送测试追踪"
        exit 1
        ;;
esac
