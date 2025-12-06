#!/usr/bin/env python3
"""
P0-4 ML Pipeline 团队培训实践练习
通过实际操作加深对新架构的理解
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path

# 添加src路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

def exercise_1_basic_config():
    """
    练习1: 配置管理基础
    目标: 学会使用PipelineConfig进行配置管理
    """
    print("🎯 练习1: 配置管理基础")
    print("=" * 40)

    try:
        from src.pipeline.config import PipelineConfig

        # 任务1.1: 创建默认配置
        print("1.1 创建默认配置...")
        config = PipelineConfig()
        print(f"   默认算法: {config.model.default_algorithm}")
        print(f"   支持算法: {config.model.supported_algorithms}")

        # 任务1.2: 自定义配置
        print("\n1.2 创建自定义配置...")
        custom_config = PipelineConfig(
            model={
                "default_algorithm": "lightgbm",
                "hyperparameter_tuning": False
            },
            training={
                "validation_size": 0.25,
                "random_state": 123
            }
        )
        print(f"   自定义算法: {custom_config.model.default_algorithm}")
        print(f"   验证集大小: {custom_config.training.validation_size}")

        # 任务1.3: 配置验证
        print("\n1.3 测试配置验证...")
        try:
            bad_config = PipelineConfig(
                model={"default_algorithm": "invalid_algorithm"}
            )
            print("   ❌ 配置验证失败 - 应该抛出异常")
        except ValueError as e:
            print(f"   ✅ 配置验证成功 - {e}")

        print("\n✅ 练习1完成!")
        return True

    except Exception as e:
        print(f"❌ 练习1失败: {e}")
        return False

def exercise_2_feature_loading():
    """
    练习2: 特征加载接口理解
    目标: 理解FeatureLoader的接口设计（不需要实际运行）
    """
    print("\n🎯 练习2: 特征加载接口理解")
    print("=" * 40)

    try:
        from src.pipeline.feature_loader import FeatureLoader

        # 任务2.1: 查看类结构
        print("2.1 查看FeatureLoader类结构...")
        import inspect

        # 检查关键方法
        methods = [
            "load_training_data",
            "_load_training_data_async",
            "save_preprocessors",
            "get_feature_stats"
        ]

        for method in methods:
            if hasattr(FeatureLoader, method):
                print(f"   ✅ 找到方法: {method}")
            else:
                print(f"   ❌ 缺失方法: {method}")

        # 任务2.2: 分析方法签名
        print("\n2.2 分析核心方法签名...")
        load_method = getattr(FeatureLoader, "load_training_data")
        sig = inspect.signature(load_method)
        print(f"   load_training_data{sig}")

        print("\n✅ 练习2完成!")
        return True

    except Exception as e:
        print(f"❌ 练习2失败: {e}")
        return False

def exercise_3_trainer_interface():
    """
    练习3: 训练器接口理解
    目标: 理解Trainer的设计和使用方法
    """
    print("\n🎯 练习3: 训练器接口理解")
    print("=" * 40)

    try:
        from src.pipeline.config import PipelineConfig
        from src.pipeline.trainer import Trainer

        # 任务3.1: 创建训练器
        print("3.1 创建训练器...")
        config = PipelineConfig()
        trainer = Trainer(config)
        print("   ✅ 训练器创建成功")

        # 任务3.2: 检查支持的算法
        print("\n3.2 检查支持的算法...")
        algorithms = config.model.supported_algorithms
        print(f"   支持的算法: {algorithms}")

        # 任务3.3: 查看训练历史
        print("\n3.3 查看训练历史...")
        print(f"   初始训练历史长度: {len(trainer.training_history)}")

        # 任务3.4: 分析训练方法
        print("\n3.4 分析训练方法...")
        import inspect
        train_method = getattr(trainer, "train")
        sig = inspect.signature(train_method)
        print(f"   train方法签名: train{sig}")

        print("\n✅ 练习3完成!")
        return True

    except Exception as e:
        print(f"❌ 练习3失败: {e}")
        return False

def exercise_4_model_registry():
    """
    练习4: 模型注册表使用
    目标: 学习模型注册表的基本使用方法
    """
    print("\n🎯 练习4: 模型注册表使用")
    print("=" * 40)

    try:
        from src.pipeline.config import PipelineConfig
        from src.pipeline.model_registry import ModelRegistry

        # 任务4.1: 创建注册表
        print("4.1 创建模型注册表...")
        config = PipelineConfig()
        registry = ModelRegistry(config)
        print("   ✅ 模型注册表创建成功")

        # 任务4.2: 分析保存方法
        print("\n4.2 分析模型保存方法...")
        import inspect
        save_method = getattr(registry, "save_model")
        sig = inspect.signature(save_method)
        print(f"   save_model方法签名: save_model{sig}")

        # 任务4.3: 分析加载方法
        print("\n4.3 分析模型加载方法...")
        load_method = getattr(registry, "load_model")
        sig = inspect.signature(load_method)
        print(f"   load_model方法签名: load_model{sig}")

        # 任务4.4: 分析比较方法
        print("\n4.4 分析模型比较方法...")
        compare_method = getattr(registry, "compare_models")
        sig = inspect.signature(compare_method)
        print(f"   compare_models方法签名: compare_models{sig}")

        print("\n✅ 练习4完成!")
        return True

    except Exception as e:
        print(f"❌ 练习4失败: {e}")
        return False

def exercise_5_integration_concept():
    """
    练习5: 集成概念理解
    目标: 理解各组件如何协同工作
    """
    print("\n🎯 练习5: 集成概念理解")
    print("=" * 40)

    # 任务5.1: 分析代码结构
    print("5.1 分析P0-4项目文件结构...")

    pipeline_files = [
        "src/pipeline/__init__.py",
        "src/pipeline/config.py",
        "src/pipeline/feature_loader.py",
        "src/pipeline/trainer.py",
        "src/pipeline/model_registry.py",
        "src/pipeline/flows/"
    ]

    for file_path in pipeline_files:
        if Path(file_path).exists():
            print(f"   ✅ {file_path}")
        else:
            print(f"   ❌ {file_path}")

    # 任务5.2: 理解数据流
    print("\n5.2 理解ML Pipeline数据流...")
    print("   1. FeatureStore → FeatureLoader (异步→同步桥接)")
    print("   2. FeatureLoader → Trainer (特征数据)")
    print("   3. Trainer → ModelRegistry (训练好的模型)")
    print("   4. ModelRegistry → Production (模型部署)")

    # 任务5.3: 配置传播
    print("\n5.3 理解配置传播...")
    print("   PipelineConfig (统一配置) → 所有组件")

    print("\n✅ 练习5完成!")
    return True

def exercise_6_code_quality():
    """
    练习6: 代码质量检查
    目标: 学习检查和提升代码质量
    """
    print("\n🎯 练习6: 代码质量检查")
    print("=" * 40)

    # 任务6.1: 检查文档字符串
    print("6.1 检查核心文件的文档字符串...")

    quality_checks = [
        ("src/pipeline/config.py", ["FeatureConfig", "ModelConfig", "PipelineConfig"]),
        ("src/pipeline/trainer.py", ["Trainer"]),
        ("src/pipeline/model_registry.py", ["ModelRegistry"]),
        ("src/pipeline/feature_loader.py", ["FeatureLoader"])
    ]

    for file_path, classes in quality_checks:
        print(f"\n   检查 {file_path}:")
        try:
            content = Path(file_path).read_text()

            for class_name in classes:
                if f'class {class_name}' in content:
                    # 检查类文档字符串
                    class_start = content.find(f'class {class_name}')
                    class_section = content[class_start:class_start+1000]

                    if '"""' in class_section:
                        print(f"      ✅ {class_name}: 有文档字符串")
                    else:
                        print(f"      ⚠️ {class_name}: 缺少文档字符串")
                else:
                    print(f"      ❌ {class_name}: 未找到类定义")

        except Exception as e:
            print(f"      ❌ 读取失败: {e}")

    # 任务6.2: 检查类型注解
    print("\n6.2 检查类型注解使用...")

    type_annotation_files = [
        "src/pipeline/config.py",
        "src/pipeline/trainer.py",
        "src/pipeline/model_registry.py"
    ]

    for file_path in type_annotation_files:
        try:
            content = Path(file_path).read_text()
            if "from typing import" in content:
                print(f"   ✅ {file_path}: 使用类型注解")
            else:
                print(f"   ⚠️ {file_path}: 缺少类型注解")
        except Exception as e:
            print(f"   ❌ {file_path}: 读取失败 - {e}")

    print("\n✅ 练习6完成!")
    return True

def generate_training_report(results):
    """生成培训报告"""
    print("\n" + "=" * 60)
    print("📊 团队培训实践练习报告")
    print("=" * 60)

    passed = sum(results.values())
    total = len(results)
    success_rate = passed / total * 100

    print(f"完成率: {success_rate:.1f}% ({passed}/{total})")

    print("\n详细结果:")
    for i, (exercise_name, passed) in enumerate(results.items(), 1):
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  练习{i}: {exercise_name} - {status}")

    # 生成建议
    print(f"\n培训建议:")
    if success_rate >= 80:
        print("  🎉 优秀! 您已完全掌握P0-4 ML Pipeline的核心概念")
    elif success_rate >= 60:
        print("  👍 良好! 您理解了大部分概念，建议复习失败的部分")
    else:
        print("  💪 加油! 建议重新阅读培训材料，加强理解")

    return success_rate

def main():
    """主培训函数"""
    print("🚀 P0-4 ML Pipeline 团队培训实践练习")
    print("通过实际操作加深对新架构的理解")
    print("=" * 60)

    # 培训练习列表
    exercises = [
        ("配置管理基础", exercise_1_basic_config),
        ("特征加载接口理解", exercise_2_feature_loading),
        ("训练器接口理解", exercise_3_trainer_interface),
        ("模型注册表使用", exercise_4_model_registry),
        ("集成概念理解", exercise_5_integration_concept),
        ("代码质量检查", exercise_6_code_quality),
    ]

    # 执行练习
    results = {}
    for exercise_name, exercise_func in exercises:
        try:
            results[exercise_name] = exercise_func()
        except Exception as e:
            print(f"❌ 练习异常: {exercise_name} - {e}")
            results[exercise_name] = False

    # 生成报告
    success_rate = generate_training_report(results)

    # 保存报告
    report_content = f"""
# P0-4 ML Pipeline 团队培训实践报告

**培训时间**: 2025-12-06
**完成率**: {success_rate:.1f}% ({sum(results.values())}/{len(results)})

## 练习结果

"""
    for exercise_name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        report_content += f"- {exercise_name}: {status}\n"

    report_content += f"""
## 培训总结

{'恭喜完成培训！您已掌握了P0-4 ML Pipeline的核心概念和使用方法。' if success_rate >= 80 else '建议继续学习和实践，加强对新架构的理解。'}

### 下一步建议
1. 在实际项目中应用新架构
2. 参与代码审查和贡献
3. 分享使用经验和最佳实践
4. 持续关注项目更新和改进
"""

    Path("P0_4_TRAINING_EXERCISES_REPORT.md").write_text(report_content)
    print(f"\n📄 培训报告已保存: P0_4_TRAINING_EXERCISES_REPORT.md")

    return success_rate >= 60

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)