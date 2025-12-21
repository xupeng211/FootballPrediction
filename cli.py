#!/usr/bin/env python3
"""
FootballPrediction V7.0 统一CLI入口
提供项目所有功能的命令行接口
"""

import argparse
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from src.core.config import get_config
from src.utils import setup_logger

def harvest_command(args):
    """数据收割命令"""
    try:
        from src.scripts.season_reharvest_v7 import SeasonReharvesterV7

        print("🚀 开始数据收割...")
        reharvester = SeasonReharvesterV7()
        reharvester.run()

    except Exception as e:
        print(f"❌ 数据收割失败: {e}")
        sys.exit(1)

def predict_command(args):
    """预测命令"""
    try:
        from predict_match_v7 import MatchPredictorV7

        if args.id:
            print(f"🔍 预测比赛 {args.id}...")
            predictor = MatchPredictorV7()
            result = predictor.predict_match(args.id)
            if result:
                predictor.save_prediction_result(result)
            else:
                print("❌ 预测失败")
                sys.exit(1)
        else:
            print("🎯 交互式预测模式...")
            predictor = MatchPredictorV7()
            predictor.interactive_predict()

    except Exception as e:
        print(f"❌ 预测失败: {e}")
        sys.exit(1)

def train_command(args):
    """模型训练命令"""
    try:
        from src.ml.model_trainer import train_new_model

        print("🏋️ 开始模型训练...")
        print("📊 将使用最新收割的数据进行训练")

        success = train_new_model()

        if success:
            print("✅ 模型训练完成!")
            print("🎯 新模型已保存，可用于预测")
        else:
            print("❌ 模型训练失败")
            sys.exit(1)

    except Exception as e:
        print(f"❌ 训练失败: {e}")
        sys.exit(1)

def status_command(args):
    """系统状态检查命令"""
    try:
        from src.models.model_handler import get_model_handler
        from src.data_access.api_client import get_api_client
        from src.utils import get_db_manager

        config = get_config()
        print("=" * 60)
        print("🔍 FootballPrediction V7.0 系统状态检查")
        print("=" * 60)

        # 配置验证
        validation = config.validate()
        print(f"📋 配置状态: {'✅ 正常' if validation['valid'] else '❌ 异常'}")
        print(f"  环境: {validation['environment']}")
        if validation['issues']:
            for issue in validation['issues']:
                print(f"  ⚠️ {issue}")

        # 模型状态
        print(f"\n🤖 模型状态:")
        try:
            model_handler = get_model_handler()
            if model_handler.is_loaded:
                model_info = model_handler.get_model_info()
                print(f"  ✅ 模型已加载: {model_info.get('model_type', 'unknown')}")
                print(f"  📊 特征数量: {model_info.get('feature_count', 'unknown')}")
                print(f"  🌳 树数量: {model_info.get('tree_count', 'unknown')}")
            else:
                print(f"  ❌ 模型未加载")
        except Exception as e:
            print(f"  ❌ 模型检查失败: {e}")

        # API客户端状态
        print(f"\n🌐 API客户端状态:")
        try:
            api_client = get_api_client()
            stats = api_client.get_request_stats()
            print(f"  ✅ 客户端初始化成功")
            print(f"  📈 Session ID: {stats['session_id']}")
        except Exception as e:
            print(f"  ❌ API客户端初始化失败: {e}")

        # 数据库状态
        print(f"\n🗄️ 数据库状态:")
        try:
            db_manager = get_db_manager()
            if db_manager.is_available():
                print(f"  ✅ 数据库连接正常")
                # 检查表信息
                table_info = db_manager.get_table_info('match_features_training')
                if table_info:
                    print(f"  📊 训练数据表: {table_info['row_count']} 条记录")
            else:
                print(f"  ⚠️ 数据库不可用 (将使用文件模式)")
        except Exception as e:
            print(f"  ❌ 数据库检查失败: {e}")

        # 路径状态
        print(f"\n📁 路径状态:")
        print(f"  📂 项目根目录: {config.paths.project_root}")
        print(f"  📂 数据目录: {config.paths.data_dir}")
        print(f"  📂 模型文件: {config.paths.current_model_path}")
        print(f"  📂 特征文件: {config.paths.final_features_path}")
        print(f"  📂 日志目录: {config.paths.logs_dir}")

        # 检查关键文件
        model_exists = config.paths.current_model_path.exists()
        features_exists = config.paths.final_features_path.exists()
        print(f"  🔧 模型文件: {'✅ 存在' if model_exists else '❌ 缺失'}")
        print(f"  🔧 特征文件: {'✅ 存在' if features_exists else '❌ 缺失'}")

        print("\n" + "=" * 60)
        print("🎯 系统状态检查完成")
        print("=" * 60)

    except Exception as e:
        print(f"❌ 状态检查失败: {e}")
        sys.exit(1)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="FootballPrediction V7.0 - 专业足球预测系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python cli.py harvest                    # 全量数据收割
  python cli.py predict --id 123456       # 预测指定比赛
  python cli.py predict                    # 交互式预测
  python cli.py train                      # 模型训练
  python cli.py status                     # 系统状态检查
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # 收割命令
    harvest_parser = subparsers.add_parser('harvest', help='全量数据收割')
    harvest_parser.set_defaults(func=harvest_command)

    # 预测命令
    predict_parser = subparsers.add_parser('predict', help='比赛预测')
    predict_parser.add_argument('--id', type=str, help='比赛ID')
    predict_parser.set_defaults(func=predict_command)

    # 训练命令
    train_parser = subparsers.add_parser('train', help='模型训练')
    train_parser.set_defaults(func=train_command)

    # 状态命令
    status_parser = subparsers.add_parser('status', help='系统状态检查')
    status_parser.set_defaults(func=status_command)

    # 如果没有提供参数，显示帮助
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    # 解析参数
    args = parser.parse_args()

    # 执行命令
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()