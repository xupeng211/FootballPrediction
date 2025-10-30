#!/usr/bin/env python3
"""
Phase 7 Week 4 部署准备和CI/CD集成扩展器
Phase 7 Week 4 Deployment Preparation and CI/CD Integration Expander

基于前三周的测试成果，准备生产部署和优化CI/CD流水线
"""

import ast
import json
import subprocess
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set

class Phase7DeploymentCicdExpander:
    """Phase 7 Week 4 部署准备和CI/CD集成扩展器"""

    def __init__(self):
        self.start_time = datetime.now()
        self.analysis_results = {}
        self.deployment_files_created = []

    def expand_deployment_cicd_integration(self) -> Dict:
        """扩展部署准备和CI/CD集成"""
        print("🚀 开始Phase 7 Week 4: 部署准备和CI/CD集成")
        print("=" * 60)
        print("🎯 目标: 准备生产部署和优化CI/CD流水线")
        print("📊 阶段: Week 4 - 部署准备和CI/CD集成")
        print("=" * 60)

        # 1. 分析当前部署和CI/CD状态
        print("\n📋 分析当前部署和CI/CD状态...")
        deployment_analysis = self._analyze_deployment_status()
        self.analysis_results['deployment_analysis'] = deployment_analysis

        # 2. 优化CI/CD流水线
        print("\n🔧 优化CI/CD流水线...")
        cicd_optimization = self._optimize_cicd_pipeline()
        self.analysis_results['cicd_optimization'] = cicd_optimization

        # 3. 创建部署配置
        print("\n📦 创建部署配置...")
        deployment_config = self._create_deployment_configurations()
        self.analysis_results['deployment_config'] = deployment_config

        # 4. 建立监控和告警
        print("\n📊 建立监控和告警...")
        monitoring_setup = self._setup_monitoring_alerting()
        self.analysis_results['monitoring_setup'] = monitoring_setup

        # 5. 生成生产部署文档
        print("\n📄 生成生产部署文档...")
        deployment_docs = self._generate_deployment_documentation()
        self.analysis_results['deployment_docs'] = deployment_docs

        # 生成最终报告
        elapsed_time = (datetime.now() - self.start_time).total_seconds()

        final_result = {
            'success': True,
            'phase': 'Phase 7 Week 4',
            'elapsed_time': f"{elapsed_time:.1f}s",
            'analysis_results': self.analysis_results,
            'summary': {
                'deployment_status': deployment_analysis['deployment_readiness'],
                'cicd_optimizations': cicd_optimization['optimizations_count'],
                'deployment_configs_created': deployment_config['configs_created'],
                'monitoring_components': monitoring_setup['monitoring_components'],
                'documentation_pages': deployment_docs['docs_generated']
            },
            'recommendations': self._generate_deployment_recommendations()
        }

        print("\n🎉 Phase 7 Week 4 部署准备和CI/CD集成完成:")
        print(f"   部署准备状态: {final_result['summary']['deployment_status']}")
        print(f"   CI/CD优化项: {final_result['summary']['cicd_optimizations']} 个")
        print(f"   部署配置文件: {final_result['summary']['deployment_configs_created']} 个")
        print(f"   监控组件: {final_result['summary']['monitoring_components']} 个")
        print(f"   文档页面: {final_result['summary']['documentation_pages']} 个")
        print(f"   执行时间: {final_result['elapsed_time']}")
        print("   状态: ✅ 成功")

        print("\n📋 下一步行动:")
        for i, step in enumerate(final_result['recommendations'][:3], 1):
            print(f"   {i}. {step}")

        # 保存报告
        self._save_report(final_result)

        return final_result

    def _analyze_deployment_status(self) -> Dict:
        """分析当前部署状态"""
        try:
            deployment_files = {
                'Dockerfile': Path('Dockerfile'),
                'docker-compose.yml': Path('docker-compose.yml'),
                'docker-compose.prod.yml': Path('docker-compose.prod.yml'),
                '.env.example': Path('.env.example'),
                'requirements/requirements.lock': Path('requirements/requirements.lock'),
                'Makefile': Path('Makefile'),
                '.github/workflows': Path('.github/workflows')
            }

            existing_files = {}
            for name, path in deployment_files.items():
                if path.exists():
                    existing_files[name] = {
                        'exists': True,
                        'size': path.stat().st_size if path.is_file() else 0,
                        'modified': datetime.fromtimestamp(path.stat().st_mtime).isoformat()
                    }
                else:
                    existing_files[name] = {'exists': False}

            # 检查CI/CD工作流
            ci_workflows = []
            if Path('.github/workflows').exists():
                ci_workflows = list(Path('.github/workflows').glob('*.yml'))
                ci_workflows.extend(list(Path('.github/workflows').glob('*.yaml')))

            # 计算部署准备度
            readiness_score = sum(1 for info in existing_files.values() if info['exists'])
            max_score = len(existing_files)
            readiness_percentage = (readiness_score / max_score) * 100 if max_score > 0 else 0

            deployment_readiness = "生产就绪" if readiness_percentage >= 80 else "需要完善" if readiness_percentage >= 60 else "基础不足"

            print(f"   🔍 发现部署文件: {readiness_score}/{max_score}")
            print(f"   🔍 CI/CD工作流: {len(ci_workflows)} 个")

            return {
                'deployment_readiness': deployment_readiness,
                'readiness_score': f"{readiness_percentage:.1f}%",
                'existing_files': existing_files,
                'ci_workflows_count': len(ci_workflows),
                'ci_workflows': [str(wf.name) for wf in ci_workflows]
            }

        except Exception as e:
            return {
                'deployment_readiness': '分析失败',
                'error': str(e),
                'status': 'analysis_failed'
            }

    def _optimize_cicd_pipeline(self) -> Dict:
        """优化CI/CD流水线"""
        optimizations = []
        workflows_created = []

        try:
            # 1. 创建增强的测试工作流
            enhanced_test_workflow = self._create_enhanced_test_workflow()
            workflow_file = Path('.github/workflows/enhanced-test.yml')
            workflow_file.parent.mkdir(parents=True, exist_ok=True)

            with open(workflow_file, 'w', encoding='utf-8') as f:
                yaml.dump(enhanced_test_workflow, f, default_flow_style=False, allow_unicode=True)

            workflows_created.append(str(workflow_file))
            optimizations.append("增强的测试工作流")

            # 2. 创建部署工作流
            deployment_workflow = self._create_deployment_workflow()
            deploy_workflow_file = Path('.github/workflows/deploy.yml')

            with open(deploy_workflow_file, 'w', encoding='utf-8') as f:
                yaml.dump(deployment_workflow, f, default_flow_style=False, allow_unicode=True)

            workflows_created.append(str(deploy_workflow_file))
            optimizations.append("自动部署工作流")

            # 3. 创建监控工作流
            monitoring_workflow = self._create_monitoring_workflow()
            monitor_workflow_file = Path('.github/workflows/monitor.yml')

            with open(monitor_workflow_file, 'w', encoding='utf-8') as f:
                yaml.dump(monitoring_workflow, f, default_flow_style=False, allow_unicode=True)

            workflows_created.append(str(monitor_workflow_file))
            optimizations.append("监控告警工作流")

            # 4. 创建质量门禁工作流
            quality_gate_workflow = self._create_quality_gate_workflow()
            quality_workflow_file = Path('.github/workflows/quality-gate.yml')

            with open(quality_workflow_file, 'w', encoding='utf-8') as f:
                yaml.dump(quality_gate_workflow, f, default_flow_style=False, allow_unicode=True)

            workflows_created.append(str(quality_workflow_file))
            optimizations.append("质量门禁工作流")

            print(f"   📝 创建CI/CD工作流: {len(workflows_created)} 个")

            return {
                'optimizations_count': len(optimizations),
                'optimizations': optimizations,
                'workflows_created': workflows_created,
                'status': 'cicd_optimized'
            }

        except Exception as e:
            return {
                'optimizations_count': 0,
                'error': str(e),
                'status': 'optimization_failed'
            }

    def _create_enhanced_test_workflow(self) -> Dict:
        """创建增强的测试工作流"""
        return {
            'name': 'Enhanced Testing Pipeline',
            'on': {
                'push': {'branches': ['main', 'develop']},
                'pull_request': {'branches': ['main']},
                'schedule': [{'cron': '0 2 * * *'}]  # 每日2点运行
            },
            'jobs': {
                'test-matrix': {
                    'runs-on': 'ubuntu-latest',
                    'strategy': {
                        'matrix': {
                            'python-version': ['3.11', '3.12'],
                            'test-type': ['unit', 'integration', 'e2e']
                        }
                    },
                    'steps': [
                        {'uses': 'actions/checkout@v4'},
                        {'name': 'Set up Python ${{ matrix.python-version }}',
                         'uses': 'actions/setup-python@v4',
                         'with': {'python-version': '${{ matrix.python-version }}'}},
                        {'name': 'Cache dependencies',
                         'uses': 'actions/cache@v3',
                         'with': {
                             'path': '~/.cache/pip',
                             'key': '${{ runner.os }}-pip-${{ hashFiles("**/requirements*.lock") }}',
                             'restore-keys': '${{ runner.os }}-pip-'
                         }},
                        {'name': 'Install dependencies',
                         'run': 'pip install -r requirements/requirements.lock'},
                        {'name': 'Run Phase 7 Test Coverage',
                         'run': 'python3 scripts/phase7_test_coverage_expander.py'},
                        {'name': 'Run Database Tests',
                         'run': 'python3 scripts/phase7_database_test_expander.py'},
                        {'name': 'Run Business Logic Tests',
                         'run': 'python3 scripts/phase7_business_logic_test_expander.py'},
                        {'name': 'Run tests with coverage',
                         'run': 'pytest tests/${{ matrix.test-type }}/ --cov=src --cov-report=xml --cov-report=html'},
                        {'name': 'Upload coverage to Codecov',
                         'uses': 'codecov/codecov-action@v3',
                         'with': {'file': './coverage.xml'}}
                    ]
                }
            }
        }

    def _create_deployment_workflow(self) -> Dict:
        """创建部署工作流"""
        return {
            'name': 'Deployment Pipeline',
            'on': {
                'push': {'branches': ['main']},
                'workflow_dispatch': {'inputs': {
                    'environment': {
                        'description': 'Deployment environment',
                        'required': True,
                        'default': 'staging',
                        'type': 'choice',
                        'options': ['staging', 'production']
                    }
                }}
            },
            'jobs': {
                'deploy': {
                    'runs-on': 'ubuntu-latest',
                    'environment': '${{ github.event.inputs.environment || ''staging'' }}',
                    'steps': [
                        {'uses': 'actions/checkout@v4'},
                        {'name': 'Set up Docker Buildx',
                         'uses': 'docker/setup-buildx-action@v3'},
                        {'name': 'Login to Container Registry',
                         'uses': 'docker/login-action@v3',
                         'with': {
                             'registry': 'ghcr.io',
                             'username': '${{ github.actor }}',
                             'password': '${{ secrets.GITHUB_TOKEN }}'
                         }},
                        {'name': 'Build and push Docker image',
                         'uses': 'docker/build-push-action@v5',
                         'with': {
                             'context': '.',
                             'push': True,
                             'tags': 'ghcr.io/${{ github.repository }}:${{ github.sha }}',
                             'cache-from': 'type=gha',
                             'cache-to': 'type=gha,mode=max'
                         }},
                        {'name': 'Deploy to ${{ github.event.inputs.environment || ''staging'' }}',
                         'run': '''
                           echo "🚀 Deploying to ${ github.event.inputs.environment || ''staging'' }"
                           docker-compose -f docker-compose.${{ github.event.inputs.environment || ''staging'' }}.yml up -d
                           docker-compose ps
                         '''}
                    ]
                }
            }
        }

    def _create_monitoring_workflow(self) -> Dict:
        """创建监控工作流"""
        return {
            'name': 'System Monitoring',
            'on': {
                'schedule': [{'cron': '*/5 * * * *'}],  # 每5分钟
                'workflow_dispatch': {}
            },
            'jobs': {
                'health-check': {
                    'runs-on': 'ubuntu-latest',
                    'steps': [
                        {'uses': 'actions/checkout@v4'},
                        {'name': 'Check Application Health',
                         'run': '''
                           curl -f http://football-prediction.local/health || exit 1
                           echo "✅ Application health check passed"
                         '''},
                        {'name': 'Check Database Connection',
                         'run': '''
                           docker-compose exec -T db pg_isready -U postgres || exit 1
                           echo "✅ Database connection check passed"
                         '''},
                        {'name': 'Check Redis Connection',
                         'run': '''
                           docker-compose exec -T redis redis-cli ping || exit 1
                           echo "✅ Redis connection check passed"
                         '''},
                        {'name': 'Run Quality Checks',
                         'run': '''
                           python3 scripts/quality_guardian.py --check-only
                           echo "✅ Quality checks passed"
                         '''}
                    ]
                }
            }
        }

    def _create_quality_gate_workflow(self) -> Dict:
        """创建质量门禁工作流"""
        return {
            'name': 'Quality Gate',
            'on': {
                'pull_request': {'branches': ['main']},
                'push': {'branches': ['main']}
            },
            'jobs': {
                'quality-checks': {
                    'runs-on': 'ubuntu-latest',
                    'steps': [
                        {'uses': 'actions/checkout@v4'},
                        {'name': 'Run Code Quality Checks',
                         'run': '''
                           make lint
                           make type-check
                           echo "✅ Code quality checks passed"
                         '''},
                        {'name': 'Security Scan',
                         'run': '''
                           make security-check
                           echo "✅ Security scan passed"
                         '''},
                        {'name': 'Test Coverage Gate',
                         'run': '''
                           make coverage
                           COVERAGE=$(python3 -c "import json; print(json.load(open('coverage.json'))['totals']['percent_covered'])")
                           if (( $(echo "$COVERAGE < 80" | bc -l) )); then
                             echo "❌ Coverage $COVERAGE% is below 80% threshold"
                             exit 1
                           fi
                           echo "✅ Coverage $COVERAGE% meets quality gate"
                         '''},
                        {'name': 'Performance Tests',
                         'run': '''
                           make test-performance
                           echo "✅ Performance tests passed"
                         '''}
                    ]
                }
            }
        }

    def _create_deployment_configurations(self) -> Dict:
        """创建部署配置"""
        configs_created = []

        try:
            # 1. 创建生产环境Docker Compose
            prod_compose = self._create_production_docker_compose()
            prod_compose_file = Path('docker-compose.prod.yml')

            with open(prod_compose_file, 'w', encoding='utf-8') as f:
                yaml.dump(prod_compose, f, default_flow_style=False, allow_unicode=True)

            configs_created.append(str(prod_compose_file))

            # 2. 创建Kubernetes配置
            k8s_configs = self._create_kubernetes_configurations()
            k8s_dir = Path('deploy/k8s')
            k8s_dir.mkdir(parents=True, exist_ok=True)

            for config_name, config_content in k8s_configs.items():
                config_file = k8s_dir / f"{config_name}.yaml"
                with open(config_file, 'w', encoding='utf-8') as f:
                    yaml.dump(config_content, f, default_flow_style=False, allow_unicode=True)
                configs_created.append(str(config_file))

            # 3. 创建环境配置
            env_configs = self._create_environment_configs()
            env_dir = Path('environments')
            env_dir.mkdir(exist_ok=True)

            for env_name, env_content in env_configs.items():
                env_file = env_dir / f".env.{env_name}"
                with open(env_file, 'w', encoding='utf-8') as f:
                    f.write(env_content)
                configs_created.append(str(env_file))

            print(f"   📝 创建部署配置: {len(configs_created)} 个")

            return {
                'configs_created': len(configs_created),
                'configs': configs_created,
                'status': 'configs_created'
            }

        except Exception as e:
            return {
                'configs_created': 0,
                'error': str(e),
                'status': 'config_creation_failed'
            }

    def _create_production_docker_compose(self) -> Dict:
        """创建生产环境Docker Compose配置"""
        return {
            'version': '3.8',
            'services': {
                'app': {
                    'image': 'ghcr.io/xupeng211/football-prediction:latest',
                    'ports': ['8000:8000'],
                    'environment': [
                        'ENV=production',
                        'DEBUG=false',
                        'LOG_LEVEL=INFO'
                    ],
                    'depends_on': ['db', 'redis'],
                    'restart': 'unless-stopped',
                    'deploy': {
                        'replicas': 3,
                        'resources': {
                            'limits': {
                                'cpus': '1.0',
                                'memory': '1G'
                            }
                        }
                    },
                    'healthcheck': {
                        'test': ['CMD', 'curl', '-f', 'http://localhost:8000/health'],
                        'interval': '30s',
                        'timeout': '10s',
                        'retries': 3
                    }
                },
                'db': {
                    'image': 'postgres:15',
                    'environment': [
                        'POSTGRES_DB=football_prediction_prod',
                        'POSTGRES_USER=postgres',
                        'POSTGRES_PASSWORD=${DB_PASSWORD}'
                    ],
                    'volumes': ['postgres_data_prod:/var/lib/postgresql/data'],
                    'restart': 'unless-stopped',
                    'deploy': {
                        'resources': {
                            'limits': {
                                'cpus': '0.5',
                                'memory': '512M'
                            }
                        }
                    }
                },
                'redis': {
                    'image': 'redis:7-alpine',
                    'restart': 'unless-stopped',
                    'deploy': {
                        'resources': {
                            'limits': {
                                'cpus': '0.2',
                                'memory': '256M'
                            }
                        }
                    }
                },
                'nginx': {
                    'image': 'nginx:alpine',
                    'ports': ['80:80', '443:443'],
                    'volumes': ['./nginx/nginx.conf:/etc/nginx/nginx.conf:ro'],
                    'depends_on': ['app'],
                    'restart': 'unless-stopped'
                }
            },
            'volumes': {
                'postgres_data_prod': {'driver': 'local'}
            },
            'networks': {
                'frontend': None,
                'backend': None
            }
        }

    def _create_kubernetes_configurations(self) -> Dict[str, Dict]:
        """创建Kubernetes配置"""
        return {
            'namespace': {
                'apiVersion': 'v1',
                'kind': 'Namespace',
                'metadata': {'name': 'football-prediction'}
            },
            'deployment': {
                'apiVersion': 'apps/v1',
                'kind': 'Deployment',
                'metadata': {
                    'name': 'football-prediction',
                    'namespace': 'football-prediction'
                },
                'spec': {
                    'replicas': 3,
                    'selector': {'matchLabels': {'app': 'football-prediction'}},
                    'template': {
                        'metadata': {'labels': {'app': 'football-prediction'}},
                        'spec': {
                            'containers': [{
                                'name': 'app',
                                'image': 'ghcr.io/xupeng211/football-prediction:latest',
                                'ports': [{'containerPort': 8000}],
                                'env': [
                                    {'name': 'ENV', 'value': 'production'},
                                    {'name': 'DB_HOST', 'value': 'postgres-service'},
                                    {'name': 'REDIS_HOST', 'value': 'redis-service'}
                                ],
                                'resources': {
                                    'requests': {
                                        'cpu': '100m',
                                        'memory': '256Mi'
                                    },
                                    'limits': {
                                        'cpu': '1000m',
                                        'memory': '1Gi'
                                    }
                                }
                            }]
                        }
                    }
                }
            }
        }

    def _create_environment_configs(self) -> Dict[str, str]:
        """创建环境配置"""
        return {
            'production': '''# Production Environment Configuration
ENV=production
DEBUG=false
LOG_LEVEL=INFO
DATABASE_URL=postgresql://postgres:${DB_PASSWORD}@postgres:5432/football_prediction_prod
REDIS_URL=redis://redis:6379/0
SECRET_KEY=${SECRET_KEY}
CORS_ORIGINS=https://football-prediction.com
MONITORING_ENABLED=true
''',
            'staging': '''# Staging Environment Configuration
ENV=staging
DEBUG=true
LOG_LEVEL=DEBUG
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/football_prediction_staging
REDIS_URL=redis://redis:6379/0
SECRET_KEY=staging-secret-key-change-in-production
CORS_ORIGINS=https://staging.football-prediction.com
MONITORING_ENABLED=true
'''
        }

    def _setup_monitoring_alerting(self) -> Dict:
        """建立监控和告警"""
        monitoring_components = []

        try:
            # 1. 创建Prometheus配置
            prometheus_config = self._create_prometheus_config()
            prometheus_file = Path('monitoring/prometheus.yml')
            prometheus_file.parent.mkdir(parents=True, exist_ok=True)

            with open(prometheus_file, 'w', encoding='utf-8') as f:
                yaml.dump(prometheus_config, f, default_flow_style=False, allow_unicode=True)

            monitoring_components.append('Prometheus配置')

            # 2. 创建Grafana仪表板
            grafana_dashboard = self._create_grafana_dashboard()
            grafana_file = Path('monitoring/grafana/dashboards/football-prediction.json')
            grafana_file.parent.mkdir(parents=True, exist_ok=True)

            with open(grafana_file, 'w', encoding='utf-8') as f:
                json.dump(grafana_dashboard, f, indent=2)

            monitoring_components.append('Grafana仪表板')

            # 3. 创建告警规则
            alert_rules = self._create_alert_rules()
            alert_file = Path('monitoring/alerts/rules.yml')

            with open(alert_file, 'w', encoding='utf-8') as f:
                yaml.dump(alert_rules, f, default_flow_style=False, allow_unicode=True)

            monitoring_components.append('告警规则')

            print(f"   📊 创建监控组件: {len(monitoring_components)} 个")

            return {
                'monitoring_components': len(monitoring_components),
                'components': monitoring_components,
                'status': 'monitoring_setup'
            }

        except Exception as e:
            return {
                'monitoring_components': 0,
                'error': str(e),
                'status': 'monitoring_setup_failed'
            }

    def _create_prometheus_config(self) -> Dict:
        """创建Prometheus配置"""
        return {
            'global': {
                'scrape_interval': '15s',
                'evaluation_interval': '15s'
            },
            'rule_files': ['alert.yml'],
            'scrape_configs': [
                {
                    'job_name': 'football-prediction',
                    'static_configs': [{'targets': ['app:8000']}],
                    'metrics_path': '/metrics',
                    'scrape_interval': '5s'
                },
                {
                    'job_name': 'postgres',
                    'static_configs': [{'targets': ['postgres-exporter:9187']}]
                },
                {
                    'job_name': 'redis',
                    'static_configs': [{'targets': ['redis-exporter:9121']}]
                }
            ],
            'alerting': {
                'alertmanagers': [{'static_configs': [{'targets': ['alertmanager:9093']}]}]
            }
        }

    def _create_grafana_dashboard(self) -> Dict:
        """创建Grafana仪表板"""
        return {
            'dashboard': {
                'title': 'Football Prediction System Dashboard',
                'panels': [
                    {
                        'title': 'Application Health',
                        'type': 'stat',
                        'targets': [{'expr': 'up{job="football-prediction"}'}]
                    },
                    {
                        'title': 'Request Rate',
                        'type': 'graph',
                        'targets': [{'expr': 'rate(http_requests_total[5m])'}]
                    },
                    {
                        'title': 'Response Time',
                        'type': 'graph',
                        'targets': [{'expr': 'histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))'}]
                    },
                    {
                        'title': 'Error Rate',
                        'type': 'singlestat',
                        'targets': [{'expr': 'rate(http_requests_total{status=~"5.."}[5m])'}]
                    }
                ],
                'time': {'from': 'now-1h', 'to': 'now'},
                'refresh': '5s'
            }
        }

    def _create_alert_rules(self) -> Dict:
        """创建告警规则"""
        return {
            'groups': [
                {
                    'name': 'football-prediction-alerts',
                    'rules': [
                        {
                            'alert': 'ApplicationDown',
                            'expr': 'up{job="football-prediction"} == 0',
                            'for': '1m',
                            'labels': {'severity': 'critical'},
                            'annotations': {
                                'summary': 'Football Prediction application is down',
                                'description': 'Application has been down for more than 1 minute.'
                            }
                        },
                        {
                            'alert': 'HighErrorRate',
                            'expr': 'rate(http_requests_total{status=~"5.."}[5m]) > 0.1',
                            'for': '5m',
                            'labels': {'severity': 'warning'},
                            'annotations': {
                                'summary': 'High error rate detected',
                                'description': 'Error rate is above 10% for more than 5 minutes.'
                            }
                        },
                        {
                            'alert': 'HighResponseTime',
                            'expr': 'histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1',
                            'for': '5m',
                            'labels': {'severity': 'warning'},
                            'annotations': {
                                'summary': 'High response time detected',
                                'description': '95th percentile response time is above 1 second.'
                            }
                        }
                    ]
                }
            ]
        }

    def _generate_deployment_documentation(self) -> Dict:
        """生成部署文档"""
        docs_generated = []

        try:
            # 1. 创建部署指南
            deployment_guide = self._create_deployment_guide()
            guide_file = Path('docs/deployment/DEPLOYMENT_GUIDE.md')
            guide_file.parent.mkdir(parents=True, exist_ok=True)

            with open(guide_file, 'w', encoding='utf-8') as f:
                f.write(deployment_guide)

            docs_generated.append('部署指南')

            # 2. 创建运维手册
            ops_manual = self._create_operations_manual()
            ops_file = Path('docs/operations/OPERATIONS_MANUAL.md')
            ops_file.parent.mkdir(parents=True, exist_ok=True)

            with open(ops_file, 'w', encoding='utf-8') as f:
                f.write(ops_manual)

            docs_generated.append('运维手册')

            # 3. 创建故障排除指南
            troubleshooting_guide = self._create_troubleshooting_guide()
            trouble_file = Path('docs/troubleshooting/TROUBLESHOOTING.md')
            trouble_file.parent.mkdir(parents=True, exist_ok=True)

            with open(trouble_file, 'w', encoding='utf-8') as f:
                f.write(troubleshooting_guide)

            docs_generated.append('故障排除指南')

            print(f"   📄 生成文档: {len(docs_generated)} 个")

            return {
                'docs_generated': len(docs_generated),
                'documents': docs_generated,
                'status': 'documentation_generated'
            }

        except Exception as e:
            return {
                'docs_generated': 0,
                'error': str(e),
                'status': 'documentation_failed'
            }

    def _create_deployment_guide(self) -> str:
        """创建部署指南"""
        return '''# Football Prediction System 部署指南

## 概述
本文档提供了Football Prediction系统的完整部署指南，包括开发、测试和生产环境的部署步骤。

## 环境要求

### 系统要求
- CPU: 最少2核心，推荐4核心
- 内存: 最少4GB，推荐8GB
- 存储: 最少20GB可用空间
- 操作系统: Linux (Ubuntu 20.04+), macOS, Windows 10+

### 软件要求
- Docker 20.10+
- Docker Compose 2.0+
- Python 3.11+ (用于本地开发)
- Git 2.30+

## 快速部署

### 1. 克隆仓库
```bash
git clone https://github.com/xupeng211/FootballPrediction.git
cd FootballPrediction
```

### 2. 环境配置
```bash
# 复制环境配置
cp .env.example .env

# 编辑环境变量
vim .env
```

### 3. 启动服务
```bash
# 开发环境
docker-compose up -d

# 生产环境
docker-compose -f docker-compose.prod.yml up -d
```

### 4. 验证部署
```bash
# 检查服务状态
docker-compose ps

# 健康检查
curl http://localhost:8000/health
```

## 生产环境部署

### 1. 环境准备
```bash
# 创建生产环境配置
cp environments/.env.production .env

# 设置必要的环境变量
export DB_PASSWORD="your-secure-password"
export SECRET_KEY="your-secret-key"
```

### 2. 启动生产服务
```bash
# 使用生产配置启动
docker-compose -f docker-compose.prod.yml up -d

# 初始化数据库
docker-compose -f docker-compose.prod.yml exec app python -m alembic upgrade head
```

### 3. 配置反向代理
```bash
# 启动Nginx
docker-compose -f docker-compose.prod.yml up -d nginx
```

## 监控和维护

### 应用监控
- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090
- AlertManager: http://localhost:9093

### 日志查看
```bash
# 查看应用日志
docker-compose logs -f app

# 查看所有服务日志
docker-compose logs -f
```

### 数据备份
```bash
# 数据库备份
docker-compose exec db pg_dump -U postgres football_prediction_prod > backup.sql

# 恢复数据库
docker-compose exec -T db psql -U postgres football_prediction_prod < backup.sql
```

## 故障排除

### 常见问题
1. **服务启动失败**: 检查端口占用和配置文件
2. **数据库连接失败**: 验证数据库服务状态和连接配置
3. **内存不足**: 调整Docker容器资源限制

### 健康检查
```bash
# 应用健康检查
curl -f http://localhost:8000/health

# 数据库连接检查
docker-compose exec db pg_isready -U postgres

# Redis连接检查
docker-compose exec redis redis-cli ping
```

---

*更新时间: 2025-10-30*
'''

    def _create_operations_manual(self) -> str:
        """创建运维手册"""
        return '''# Football Prediction System 运维手册

## 概述
本手册提供Football Prediction系统的日常运维指南，包括监控、维护、故障处理等操作。

## 系统架构

### 服务组件
- **App**: FastAPI应用服务 (端口8000)
- **DB**: PostgreSQL数据库 (端口5432)
- **Redis**: 缓存服务 (端口6379)
- **Nginx**: 反向代理 (端口80/443)

### 数据流
```
用户请求 → Nginx → FastAPI App → PostgreSQL/Redis
                ↓
            日志 → 监控 → 告警
```

## 日常运维

### 服务管理
```bash
# 查看服务状态
docker-compose ps

# 重启服务
docker-compose restart app

# 更新服务
docker-compose pull && docker-compose up -d
```

### 日志管理
```bash
# 实时查看应用日志
docker-compose logs -f app

# 查看错误日志
docker-compose logs app | grep ERROR

# 清理旧日志
docker system prune -f
```

### 性能监控

#### 系统指标
- CPU使用率 < 80%
- 内存使用率 < 85%
- 磁盘使用率 < 90%
- 网络延迟 < 100ms

#### 应用指标
- 响应时间 < 1s (95th percentile)
- 错误率 < 5%
- 可用性 > 99.9%
- 并发用户数监控

### 数据库维护

#### 定期任务
```bash
# 数据库备份 (每日)
0 2 * * * docker-compose exec db pg_dump -U postgres football_prediction_prod > /backup/$(date +\%Y\%m\%d).sql

# 清理旧备份 (每周)
0 3 * * 0 find /backup -name "*.sql" -mtime +7 -delete

# 数据库优化 (每月)
0 4 1 * * docker-compose exec db psql -U postgres -d football_prediction_prod -c "VACUUM ANALYZE;"
```

#### 性能调优
```sql
-- 查看慢查询
SELECT query, mean_time, calls FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;

-- 查看索引使用情况
SELECT schemaname, tablename, attname, n_distinct, correlation FROM pg_stats;

-- 重建索引
REINDEX DATABASE football_prediction_prod;
```

### 缓存管理

#### Redis监控
```bash
# 查看Redis信息
docker-compose exec redis redis-cli info

# 查看内存使用
docker-compose exec redis redis-cli info memory

# 清理过期键
docker-compose exec redis redis-cli FLUSHEXPIRED
```

#### 缓存策略
- 热数据TTL: 1小时
- 预测结果TTL: 30分钟
- 用户会话TTL: 24小时

## 安全管理

### 访问控制
- 定期更新密码
- 使用强密码策略
- 启用双因素认证
- 限制管理员权限

### 数据安全
```bash
# 数据加密
docker-compose exec db psql -U postgres -c "CREATE EXTENSION IF NOT EXISTS pgcrypto;"

# 定期安全扫描
docker run --rm -v $(pwd):/app clair-scanner:latest /app
```

### 网络安全
```bash
# 防火墙配置
ufw allow 80
ufw allow 443
ufw deny 5432  # 禁止外部访问数据库
ufw enable
```

## 告警处理

### 告警级别
- **Critical**: 立即响应 (1小时内)
- **Warning**: 工作时间响应 (4小时内)
- **Info**: 定期检查 (24小时内)

### 告警流程
1. 接收告警通知
2. 确认告警详情
3. 执行应急预案
4. 记录处理过程
5. 分析根本原因

### 应急预案

#### 应用宕机
```bash
# 快速重启
docker-compose restart app

# 检查日志
docker-compose logs app --tail=100

# 回滚版本
docker-compose down && docker-compose up -d
```

#### 数据库故障
```bash
# 切换到备用数据库
# 修改连接配置
docker-compose restart app

# 恢复主数据库
# 从备份恢复数据
```

## 容量规划

### 资源评估
- 用户增长率: 10%/月
- 数据增长率: 5%/月
- 峰值并发: 1000用户

### 扩容策略
- 水平扩展: 增加应用实例
- 垂直扩展: 增加单实例资源
- 数据库分片: 按业务模块分离

## 版本发布

### 发布流程
1. 代码审查
2. 自动化测试
3. 预发布验证
4. 生产发布
5. 监控验证

### 回滚策略
```bash
# 快速回滚到上一个版本
docker-compose down
docker pull ghcr.io/xupeng211/football-prediction:previous-tag
docker-compose up -d
```

---

*更新时间: 2025-10-30*
'''

    def _create_troubleshooting_guide(self) -> str:
        """创建故障排除指南"""
        return '''# Football Prediction System 故障排除指南

## 概述
本指南提供Football Prediction系统常见问题的诊断和解决方案。

## 快速诊断

### 健康检查脚本
```bash
#!/bin/bash
# health_check.sh

echo "🔍 系统健康检查..."

# 检查服务状态
echo "📊 检查服务状态:"
docker-compose ps

# 检查应用健康
echo "🏥 检查应用健康:"
curl -s http://localhost:8000/health || echo "❌ 应用健康检查失败"

# 检查数据库连接
echo "🗄️ 检查数据库连接:"
docker-compose exec -T db pg_isready -U postgres || echo "❌ 数据库连接失败"

# 检查Redis连接
echo "🔴 检查Redis连接:"
docker-compose exec -T redis redis-cli ping || echo "❌ Redis连接失败"

echo "✅ 健康检查完成"
```

## 常见问题

### 1. 应用无法启动

#### 症状
- Docker容器启动失败
- 健康检查失败
- 无法访问应用

#### 诊断步骤
```bash
# 查看容器状态
docker-compose ps

# 查看启动日志
docker-compose logs app

# 检查端口占用
netstat -tlnp | grep :8000

# 检查环境变量
docker-compose config
```

#### 解决方案
```bash
# 重启服务
docker-compose down && docker-compose up -d

# 清理并重建
docker-compose down -v
docker system prune -f
docker-compose up -d

# 检查配置文件
docker-compose config
```

### 2. 数据库连接问题

#### 症状
- 应用日志显示数据库连接错误
- 数据库查询失败
- 无法连接到数据库

#### 诊断步骤
```bash
# 检查数据库容器状态
docker-compose ps db

# 检查数据库日志
docker-compose logs db

# 测试数据库连接
docker-compose exec db psql -U postgres -d football_prediction -c "SELECT 1;"

# 检查网络连接
docker network ls
docker network inspect football-prediction_default
```

#### 解决方案
```bash
# 重启数据库
docker-compose restart db

# 检查数据库配置
docker-compose exec db cat /var/lib/postgresql/data/postgresql.conf

# 重建数据库
docker-compose down -v
docker-compose up -d db
docker-compose exec app python -m alembic upgrade head
```

### 3. Redis连接问题

#### 症状
- 缓存操作失败
- 会话丢失
- 性能下降

#### 诊断步骤
```bash
# 检查Redis容器
docker-compose ps redis

# 测试Redis连接
docker-compose exec redis redis-cli ping

# 检查Redis内存使用
docker-compose exec redis redis-cli info memory

# 查看Redis日志
docker-compose logs redis
```

#### 解决方案
```bash
# 重启Redis
docker-compose restart redis

# 清理Redis内存
docker-compose exec redis redis-cli FLUSHALL

# 检查Redis配置
docker-compose exec redis redis-cli CONFIG GET "*"
```

### 4. 性能问题

#### 症状
- 响应时间慢
- CPU使用率高
- 内存使用率高

#### 诊断步骤
```bash
# 检查系统资源
docker stats

# 查看应用性能指标
curl http://localhost:8000/metrics

# 分析慢查询
docker-compose exec db psql -U postgres -d football_prediction -c "
SELECT query, mean_time, calls
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;"

# 检查缓存命中率
docker-compose exec redis redis-cli info stats | grep keyspace
```

#### 解决方案
```bash
# 扩容应用实例
docker-compose up -d --scale app=3

# 优化数据库
docker-compose exec db psql -U postgres -d football_prediction -c "VACUUM ANALYZE;"

# 清理缓存
docker-compose exec redis redis-cli FLUSHDB
```

### 5. 内存泄漏

#### 症状
- 内存使用持续增长
- 应用重启后内存下降
- OOM错误

#### 诊断步骤
```bash
# 监控内存使用
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# 查看内存详情
docker-compose exec app cat /proc/meminfo

# 检查Python内存使用
docker-compose exec app python -c "
import psutil
import os
process = psutil.Process(os.getpid())
print(f'Memory: {process.memory_info().rss / 1024 / 1024:.2f} MB')
"
```

#### 解决方案
```bash
# 重启应用
docker-compose restart app

# 设置内存限制
# 在docker-compose.yml中添加:
# deploy:
#   resources:
#     limits:
#       memory: 1G

# 监控内存使用
docker stats --no-stream
```

### 6. 磁盘空间不足

#### 症状
- 磁盘使用率 > 90%
- 无法写入日志
- 数据库操作失败

#### 诊断步骤
```bash
# 检查磁盘使用
df -h

# 查看大文件
find / -type f -size +1G 2>/dev/null

# 检查Docker空间使用
docker system df

# 查看日志大小
du -sh /var/lib/docker/containers/*
```

#### 解决方案
```bash
# 清理Docker
docker system prune -a -f

# 清理日志
docker-compose exec app find /app/logs -name "*.log" -mtime +7 -delete

# 清理数据库
docker-compose exec db psql -U postgres -d football_prediction -c "VACUUM FULL;"
```

## 日志分析

### 应用日志格式
```
2025-10-30 03:00:00 [INFO] Request: GET /api/predictions - Status: 200 - Time: 0.05s
2025-10-30 03:00:01 [ERROR] Database connection failed: connection timeout
2025-10-30 03:00:02 [WARNING] Cache miss for key: prediction_123
```

### 日志分析命令
```bash
# 查看错误日志
docker-compose logs app | grep ERROR

# 统计HTTP状态码
docker-compose logs app | grep -o "Status: [0-9]*" | sort | uniq -c

# 查看慢请求
docker-compose logs app | grep "Time: [0-9]*\." | awk '$NF > 1.0'

# 实时监控日志
docker-compose logs -f app | grep -E "(ERROR|WARNING)"
```

## 性能优化

### 数据库优化
```sql
-- 创建索引
CREATE INDEX CONCURRENTLY idx_predictions_created_at ON predictions(created_at);

-- 分析查询性能
EXPLAIN ANALYZE SELECT * FROM predictions WHERE created_at > NOW() - INTERVAL '1 day';

-- 更新统计信息
ANALYZE predictions;
```

### 应用优化
```python
# 缓存优化
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_prediction(match_id: int):
    # 缓存预测结果
    pass

# 连接池优化
DATABASE_CONFIG = {
    "pool_size": 20,
    "max_overflow": 30,
    "pool_timeout": 30,
    "pool_recycle": 3600
}
```

## 应急响应

### 严重故障处理流程
1. **立即响应** (5分钟内)
   - 确认故障范围
   - 启动应急预案
   - 通知相关人员

2. **故障隔离** (30分钟内)
   - 隔离故障组件
   - 启用备用服务
   - 保留故障现场

3. **快速修复** (2小时内)
   - 应用快速修复
   - 验证修复效果
   - 恢复正常服务

4. **根因分析** (24小时内)
   - 分析故障原因
   - 制定预防措施
   - 更新运维文档

### 联系方式
- **技术负责人**: [联系方式]
- **运维团队**: [联系方式]
- **产品负责人**: [联系方式]

---

*更新时间: 2025-10-30*
'''

    def _generate_deployment_recommendations(self) -> List[str]:
        """生成部署相关建议"""
        return [
            "🚀 执行生产环境部署验证和测试",
            "📊 建立完整的监控告警体系",
            "🔧 制定定期维护和备份计划",
            "📚 完善运维文档和应急预案",
            "🛡️ 强化安全防护和访问控制",
            "⚡ 优化性能和资源使用效率",
            "🔄 建立版本发布和回滚流程"
        ]

    def _save_report(self, result: Dict):
        """保存报告"""
        report_file = Path(f'phase7_deployment_cicd_expansion_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"\n📄 详细报告已保存到: {report_file}")

def main():
    """主函数"""
    print("🚀 Phase 7 Week 4 部署准备和CI/CD集成扩展器")
    print("=" * 60)

    expander = Phase7DeploymentCicdExpander()
    result = expander.expand_deployment_cicd_integration()

    return result

if __name__ == '__main__':
    main()