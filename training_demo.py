#!/usr/bin/env python3
"""
P0-4 ML Pipeline 培训演示脚本
不依赖环境导入，展示核心概念和使用方法
"""

import sys
from pathlib import Path

def demo_code_examples():
    """展示核心代码示例"""
    print("🎯 P0-4 ML Pipeline 代码示例演示")
    print("=" * 50)

    examples = [
        {
            "title": "1. PipelineConfig 使用示例",
            "code": '''
from src.pipeline.config import PipelineConfig

# 创建默认配置
config = PipelineConfig()
print(f"默认算法: {config.model.default_algorithm}")

# 自定义配置
config = PipelineConfig(
    model={
        "default_algorithm": "xgboost",
        "hyperparameter_tuning": True,
        "cv_folds": 5
    },
    training={
        "validation_size": 0.3,
        "random_state": 42
    }
)

# 环境变量支持 (在.env中设置)
# MODEL_DEFAULT_ALGORITHM=lightgbm
'''
        },
        {
            "title": "2. FeatureLoader 特征加载示例",
            "code": '''
from src.pipeline.feature_loader import FeatureLoader
from src.features.feature_store import FootballFeatureStore

# 创建特征加载器
store = FootballFeatureStore()
feature_loader = FeatureLoader(store, config)

# 加载训练数据 (同步接口)
match_ids = [1, 2, 3, 4, 5]
X, y = feature_loader.load_training_data(
    match_ids=match_ids,
    target_column="result",
    validate_quality=True
)

print(f"加载了 {len(X)} 个样本，{len(X.columns)} 个特征")

# 特征统计
stats = feature_loader.get_feature_stats(X)
print(f"特征统计: {stats['shape']}")

# 保存预处理器 (用于推理时复用)
feature_loader.save_preprocessors("./preprocessors/")
'''
        },
        {
            "title": "3. Trainer 训练器使用示例",
            "code": '''
from src.pipeline.trainer import Trainer

# 创建训练器
trainer = Trainer(config)

# 训练单个算法
result = trainer.train(X, y, algorithm="xgboost")
print(f"训练完成: {result['algorithm']}")
print(f"准确率: {result['metrics']['accuracy']:.3f}")

# 批量训练多种算法
algorithms = ["xgboost", "lightgbm", "random_forest"]
results = {}

for algo in algorithms:
    result = trainer.train(X, y, algorithm=algo)
    results[algo] = result['metrics']

# 获取最佳模型
best_model = trainer.get_best_model()
print(f"最佳模型: {best_model['algorithm']}")

# 查看训练历史
print(f"训练历史: {len(trainer.training_history)} 次训练")
'''
        },
        {
            "title": "4. ModelRegistry 模型管理示例",
            "code": '''
from src.pipeline.model_registry import ModelRegistry

# 创建模型注册表
registry = ModelRegistry(config)

# 保存模型
model_path = registry.save_model(
    model=trained_model,
    name="football_predictor_v1",
    metadata={
        "algorithm": "xgboost",
        "accuracy": 0.85,
        "features": ["team_strength", "recent_form"],
        "training_date": "2025-12-06",
        "model_version": "v1.0"
    }
)
print(f"模型已保存: {model_path}")

# 加载模型
model, metadata = registry.load_model("football_predictor_v1")
print(f"加载模型: {metadata['algorithm']}")

# 比较模型版本
comparison = registry.compare_models("football_predictor")
print(comparison)

# 导出模型 (用于部署)
deployment_package = registry.export_model(
    "football_predictor_v1",
    export_path="./deployment/"
)
'''
        },
        {
            "title": "5. Prefect 工作流自动化示例",
            "code": '''
from src.pipeline.flows.train_flow import train_flow

# 运行自动化训练流程
result = await train_flow(
    season="2023-2024",
    match_ids=[1, 2, 3, 4, 5, 6, 7, 8],
    model_name="season_predictor",
    algorithm="xgboost"
)

print(f"训练状态: {result['status']}")
print(f"模型路径: {result['model_path']}")
print(f"训练指标: {result['metrics']}")

# 批量评估
from src.pipeline.flows.eval_flow import eval_flow

eval_result = await eval_flow(
    model_names=["season_predictor_v1", "season_predictor_v2"],
    test_data_path="./test_data.csv"
)
'''
        }
    ]

    for example in examples:
        print(f"\n{example['title']}")
        print("-" * len(example['title']))
        print(example['code'])

def demo_architecture_flow():
    """展示架构流程图"""
    print("\n🏗️ P0-4 ML Pipeline 架构流程")
    print("=" * 50)

    flow_diagram = """
┌─────────────────────────────────────────────────────────────┐
│                    P0-4 ML Pipeline 架构                     │
└─────────────────────────────────────────────────────────────┘

┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   数据源     │    │  特征系统    │    │  特征加载器  │
│ FotMob API  │───►│ FeatureStore│───►│ FeatureLoader│
└─────────────┘    └─────────────┘    └─────────────┘
                                            │
┌─────────────┐    ┌─────────────┐         │
│  模型部署    │◄───│ 模型注册表   │◄────────┘
│ Production  │    │ModelRegistry│
└─────────────┘    └─────────────┘
                           ▲
                           │
┌─────────────┐    ┌─────────────┐
│  训练工作流  │───►│   训练器     │
│ Prefect Flow│    │   Trainer   │
└─────────────┘    └─────────────┘
       │                   │
       ▼                   ▼
┌─────────────┐    ┌─────────────┐
│  配置管理    │    │  质量监控    │
│PipelineConfig│    │QualityCheck │
└─────────────┘    └─────────────┘
"""

    print(flow_diagram)

    print("\n数据流程说明:")
    print("1. 数据源 → FeatureStore: 原始数据采集和存储")
    print("2. FeatureStore → FeatureLoader: 异步到同步桥接")
    print("3. FeatureLoader → Trainer: 预处理后的特征数据")
    print("4. Trainer → ModelRegistry: 训练完成的模型")
    print("5. ModelRegistry → Production: 部署就绪的模型")
    print("6. PipelineConfig: 统一配置所有组件")
    print("7. Prefect Flow: 自动化编排整个流程")

def demo_best_practices():
    """展示最佳实践"""
    print("\n💡 P0-4 ML Pipeline 最佳实践")
    print("=" * 50)

    practices = [
        {
            "category": "配置管理",
            "practices": [
                "✅ 使用PipelineConfig统一管理配置",
                "✅ 支持环境变量注入，便于部署",
                "✅ 配置验证防止无效参数",
                "❌ 避免硬编码配置参数"
            ]
        },
        {
            "category": "错误处理",
            "practices": [
                "✅ 完善的异常处理机制",
                "✅ 详细的错误信息记录",
                "✅ 优雅的降级处理",
                "✅ 自动重试机制"
            ]
        },
        {
            "category": "性能优化",
            "practices": [
                "✅ 批量数据加载减少IO开销",
                "✅ 预处理器缓存加速推理",
                "✅ 并行训练提升效率",
                "✅ 内存优化避免OOM"
            ]
        },
        {
            "category": "代码质量",
            "practices": [
                "✅ 完整的类型注解",
                "✅ 详细的文档字符串",
                "✅ 单元测试覆盖",
                "✅ 代码规范检查"
            ]
        },
        {
            "category": "运维友好",
            "practices": [
                "✅ 结构化日志输出",
                "✅ 关键指标监控",
                "✅ 模型版本管理",
                "✅ 自动化部署流程"
            ]
        }
    ]

    for practice_item in practices:
        print(f"\n{practice_item['category']}:")
        for practice in practice_item['practices']:
            print(f"  {practice}")

def demo_troubleshooting():
    """展示故障排除指南"""
    print("\n🔧 常见问题故障排除")
    print("=" * 50)

    troubleshooting = [
        {
            "问题": "FeatureLoader导入失败",
            "原因": "环境依赖问题或路径配置错误",
            "解决": [
                "1. 检查Python路径: export PYTHONPATH=$PWD/src",
                "2. 安装依赖: pip install -r requirements.txt",
                "3. 检查虚拟环境激活状态"
            ]
        },
        {
            "问题": "模型训练失败",
            "原因": "数据质量问题或参数配置错误",
            "解决": [
                "1. 检查数据格式: X, y 是否正确",
                "2. 验证数据质量: 使用validate_quality=True",
                "3. 调整超参数: 减少n_estimators或调整learning_rate"
            ]
        },
        {
            "问题": "配置验证失败",
            "原因": "无效的算法名称或参数范围错误",
            "解决": [
                "1. 检查支持算法: config.model.supported_algorithms",
                "2. 验证参数范围: 检查配置文件说明",
                "3. 使用默认配置作为参考"
            ]
        },
        {
            "问题": "模型保存失败",
            "原因": "路径权限问题或磁盘空间不足",
            "解决": [
                "1. 检查目录权限: ls -la artifacts/models/",
                "2. 确保磁盘空间: df -h",
                "3. 创建必要目录: mkdir -p artifacts/models"
            ]
        }
    ]

    for item in troubleshooting:
        print(f"\n❓ {item['问题']}")
        print(f"🔍 原因: {item['原因']}")
        print("💡 解决方案:")
        for solution in item['解决']:
            print(f"   {solution}")

def main():
    """主演示函数"""
    print("🚀 P0-4 ML Pipeline 培训演示")
    print("不依赖环境导入，展示核心概念和使用方法")
    print("=" * 60)

    # 执行演示
    demo_code_examples()
    demo_architecture_flow()
    demo_best_practices()
    demo_troubleshooting()

    print("\n" + "=" * 60)
    print("📚 培训资源")
    print("=" * 60)

    resources = [
        "📖 P0_4_TEAM_TRAINING_GUIDE.md - 完整培训指南",
        "📖 P0_4_COMPLETION_REPORT.md - 项目完成报告",
        "📖 P0_4_QA_AUDIT_REPORT.md - QA审计报告",
        "📖 patches/pr_p0_4_ml_pipeline_fix.md - PR文档",
        "📖 test_e2e_pipeline.py - 端到端测试示例",
        "📖 src/pipeline/ - 核心代码实现"
    ]

    for resource in resources:
        print(resource)

    print("\n🎯 下一步行动:")
    print("1. 在实际项目中应用新架构")
    print("2. 运行training_exercises.py进行实践")
    print("3. 参与代码审查和贡献")
    print("4. 分享使用经验和最佳实践")

    print("\n✅ 培训演示完成!")

if __name__ == "__main__":
    main()