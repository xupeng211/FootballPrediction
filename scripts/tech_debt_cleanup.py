#!/usr/bin/env python3
"""
技术债务清理脚本 - V19.4 预发布环境净化

清理内容:
1. 代码收敛 - 归档 v1-v18 废弃代码
2. 配置唯一化 - 移除冗余配置文件
3. 数据清理 - 清理临时文件和旧数据库
4. 报告生成 - 生成清理报告
"""

import os
import shutil
import json
from pathlib import Path
from datetime import datetime, timedelta

# 项目根目录
ROOT = Path(__file__).parent.parent

# 归档目录
ARCHIVE_DIR = ROOT / "archive" / f"cleanup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

# 清理配置
CLEANUP_CONFIG = {
    "code_archive": {
        "source_dir": ROOT / "src",
        "files_to_archive": [
            # 旧版流水线 (保留 v19 作为生产)
            "src/core/pipeline_v18.py",
            "src/core/pipeline_v18_2.py",
            "src/core/pipeline.py",  # v17

            # 旧版 ML 脚本
            "src/ml/train_prematch_v85.py",
            "src/ml/lightgbm_trainer_v7.py",
            "src/ml/v18_1_optuna_optimizer.py",

            # 旧版脚本
            "src/scripts/season_reharvest_v7.py",
            "src/scripts/merge_v2_features_with_odds.py",
            "src/scripts/merge_v2_features_corrected.py",
            "src/scripts/merge_gold_dataset.py",
        ]
    },

    "config_cleanup": {
        "files_to_delete": [
            # 旧配置文件 (统一使用 config_unified.py)
            "configs/settings.py",
            "src/core/config.py",
            "src/database/config.py",

            # 冗余 .env 文件
            ".env.docker",
        ]
    },

    "data_cleanup": {
        "files_to_delete": [
            # 旧 SQLite 数据库
            "data/football_prediction.db",
            "data/football_prediction_Phase1_Final.db",

            # data/archive 下的旧模型文件 (保留 production_models)
            "data/archive/baseline_v1*.pkl",
            "data/archive/baseline_v1*.json",
            "data/archive/football_prediction_*.pkl",
            "data/archive/xgb_football_v1*.joblib",
            "data/archive/xgb_football_v2*.joblib",
            "data/archive/xgb_*.pkl",
            "data/archive/label_encoders_*.pkl",
            "data/archive/v1_*.pkl",
            "data/archive/v1_*.json",
        ],
        "temp_dirs": [
            "data/temp",
            "src/ml/reports/v43_real",
            "src/ml/reports/v43_emergency",
            "src/ml/data/models",
            "src/data/models",
        ]
    },

    "log_cleanup": {
        "logs_dir": ROOT / "logs",
        "keep_days": 7,  # 保留 7 天内的日志
    },

    "model_cleanup": {
        "keep_versions": ["v19"],  # 只保留 v19 系列模型
        "production_models_dir": ROOT / "src/production_models",
    }
}


def calculate_size(path: Path) -> int:
    """计算文件/目录大小（字节）"""
    if path.is_file():
        return path.stat().st_size
    if path.is_dir():
        return sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
    return 0


def format_size(size_bytes: int) -> str:
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} TB"


def archive_files(files: list, archive_subdir: str) -> dict:
    """归档文件"""
    result = {
        "archived": [],
        "not_found": [],
        "total_size": 0
    }

    target_dir = ARCHIVE_DIR / archive_subdir
    target_dir.mkdir(parents=True, exist_ok=True)

    for file_path in files:
        source = ROOT / file_path
        if source.exists():
            # 保持相对目录结构
            target = target_dir / file_path
            target.parent.mkdir(parents=True, exist_ok=True)

            size = calculate_size(source)
            shutil.move(str(source), str(target))
            result["archived"].append(file_path)
            result["total_size"] += size
            print(f"  ✓ 归档: {file_path} ({format_size(size)})")
        else:
            result["not_found"].append(file_path)
            print(f"  - 跳过(不存在): {file_path}")

    return result


def delete_files(patterns: list) -> dict:
    """删除匹配的文件"""
    import glob
    result = {
        "deleted": [],
        "total_size": 0
    }

    for pattern in patterns:
        # 处理通配符
        full_pattern = str(ROOT / pattern)
        matches = glob.glob(full_pattern, recursive=True)

        for file_path in matches:
            path = Path(file_path)
            if path.is_file():
                size = calculate_size(path)
                path.unlink()
                result["deleted"].append(str(path.relative_to(ROOT)))
                result["total_size"] += size
                print(f"  ✓ 删除: {path.relative_to(ROOT)} ({format_size(size)})")

    return result


def cleanup_old_logs(logs_dir: Path, keep_days: int) -> dict:
    """清理旧日志"""
    result = {
        "deleted": [],
        "kept": [],
        "total_size": 0
    }

    if not logs_dir.exists():
        return result

    cutoff_time = datetime.now() - timedelta(days=keep_days)

    for log_file in logs_dir.glob("*.json"):
        if log_file.is_file():
            mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            size = calculate_size(log_file)

            if mtime < cutoff_time:
                log_file.unlink()
                result["deleted"].append(log_file.name)
                result["total_size"] += size
                print(f"  ✓ 删除旧日志: {log_file.name} ({format_size(size)})")
            else:
                result["kept"].append(log_file.name)

    return result


def cleanup_temp_dirs(dirs: list) -> dict:
    """清理临时目录"""
    result = {
        "cleaned": [],
        "total_size": 0
    }

    for dir_path in dirs:
        full_path = ROOT / dir_path
        if full_path.exists() and full_path.is_dir():
            size = calculate_size(full_path)
            shutil.rmtree(full_path)
            result["cleaned"].append(dir_path)
            result["total_size"] += size
            print(f"  ✓ 清理目录: {dir_path} ({format_size(size)})")

    return result


def cleanup_old_models(production_dir: Path, keep_versions: list) -> dict:
    """清理旧版本模型"""
    result = {
        "archived": [],
        "kept": [],
        "total_size": 0
    }

    if not production_dir.exists():
        return result

    archive_dir = ARCHIVE_DIR / "old_models"
    archive_dir.mkdir(parents=True, exist_ok=True)

    for model_file in production_dir.glob("*"):
        if model_file.is_file():
            filename = model_file.name

            # 检查是否需要保留
            should_keep = any(f"v{v}" in filename for v in keep_versions)

            if not should_keep:
                size = calculate_size(model_file)
                target = archive_dir / filename
                shutil.move(str(model_file), str(target))
                result["archived"].append(filename)
                result["total_size"] += size
                print(f"  ✓ 归档旧模型: {filename} ({format_size(size)})")
            else:
                result["kept"].append(filename)

    return result


def generate_report(cleanup_results: dict) -> str:
    """生成清理报告"""
    total_size = sum(
        r.get("total_size", 0)
        for r in cleanup_results.values()
        if isinstance(r, dict)
    )

    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_space_freed": format_size(total_size),
            "total_size_bytes": total_size,
        },
        "details": cleanup_results
    }

    return report


def main():
    """主函数"""
    print("=" * 70)
    print("Football Prediction - 技术债务清理脚本")
    print(f"清理时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"归档目录: {ARCHIVE_DIR}")
    print("=" * 70)
    print()

    results = {}

    # 1. 代码归档
    print("【1/5】代码归档 - 移动废弃版本到 archive/")
    results["code_archive"] = archive_files(
        CLEANUP_CONFIG["code_archive"]["files_to_archive"],
        "code_archive"
    )
    print(f"  归档文件数: {len(results['code_archive']['archived'])}")
    print(f"  释放空间: {format_size(results['code_archive']['total_size'])}")
    print()

    # 2. 配置清理
    print("【2/5】配置唯一化 - 删除冗余配置文件")
    results["config_cleanup"] = delete_files(
        CLEANUP_CONFIG["config_cleanup"]["files_to_delete"]
    )
    print(f"  删除文件数: {len(results['config_cleanup']['deleted'])}")
    print(f"  释放空间: {format_size(results['config_cleanup']['total_size'])}")
    print()

    # 3. 数据清理
    print("【3/5】数据清理 - 删除临时文件和旧数据库")
    results["data_cleanup"] = delete_files(
        CLEANUP_CONFIG["data_cleanup"]["files_to_delete"]
    )
    results["temp_cleanup"] = cleanup_temp_dirs(
        CLEANUP_CONFIG["data_cleanup"]["temp_dirs"]
    )
    data_size = results["data_cleanup"]["total_size"] + results["temp_cleanup"]["total_size"]
    print(f"  删除文件数: {len(results['data_cleanup']['deleted'])}")
    print(f"  清理目录数: {len(results['temp_cleanup']['cleaned'])}")
    print(f"  释放空间: {format_size(data_size)}")
    print()

    # 4. 日志清理
    print("【4/5】日志清理 - 删除 7 天前的日志")
    results["log_cleanup"] = cleanup_old_logs(
        CLEANUP_CONFIG["log_cleanup"]["logs_dir"],
        CLEANUP_CONFIG["log_cleanup"]["keep_days"]
    )
    print(f"  删除日志数: {len(results['log_cleanup']['deleted'])}")
    print(f"  保留日志数: {len(results['log_cleanup']['kept'])}")
    print(f"  释放空间: {format_size(results['log_cleanup']['total_size'])}")
    print()

    # 5. 模型清理
    print("【5/5】模型清理 - 归档 v17/v18 旧模型")
    results["model_cleanup"] = cleanup_old_models(
        CLEANUP_CONFIG["model_cleanup"]["production_models_dir"],
        CLEANUP_CONFIG["model_cleanup"]["keep_versions"]
    )
    print(f"  归档模型数: {len(results['model_cleanup']['archived'])}")
    print(f"  保留模型数: {len(results['model_cleanup']['kept'])}")
    print(f"  释放空间: {format_size(results['model_cleanup']['total_size'])}")
    print()

    # 生成报告
    print("=" * 70)
    report = generate_report(results)
    print("清理完成！")
    print(f"总释放空间: {report['summary']['total_space_freed']}")
    print()

    # 保存报告
    report_path = ROOT / "logs" / f"cleanup_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_path.parent.mkdir(exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"清理报告已保存至: {report_path}")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    exit(main())
