#!/usr/bin/env python3
"""
数据库重置脚本 - 净室测试 Phase 1
清空数据库中的所有比赛数据，保留表结构
"""

import sys
import sqlite3
from pathlib import Path

def reset_database():
    """重置数据库，清空所有比赛数据"""

    # 数据库文件路径
    db_path = Path("data/football_prediction.db")

    if not db_path.exists():
        print("❌ 数据库文件不存在，无需重置")
        return False

    print("🧹 开始重置数据库...")

    try:
        # 连接数据库
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # 查看重置前的数据量
        cursor.execute("SELECT COUNT(*) FROM matches")
        matches_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM teams")
        teams_count = cursor.fetchone()[0]

        print(f"📊 重置前状态: {matches_count} 场比赛, {teams_count} 支球队")

        # 清空比赛数据
        cursor.execute("DELETE FROM matches")

        # 可选：也清空球队数据（重新采集）
        cursor.execute("DELETE FROM teams")

        # 重置自增ID（如果表存在）
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sqlite_sequence'")
        if cursor.fetchone():
            cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('matches', 'teams')")

        # 提交更改
        conn.commit()

        # 验证重置结果
        cursor.execute("SELECT COUNT(*) FROM matches")
        matches_after = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM teams")
        teams_after = cursor.fetchone()[0]

        print(f"✅ 重置完成: {matches_after} 场比赛, {teams_after} 支球队")

        # 关闭连接
        conn.close()

        print("🎉 数据库重置成功，可以进行净室测试")
        return True

    except Exception as e:
        print(f"❌ 数据库重置失败: {str(e)}")
        return False

def main():
    """主函数"""
    print("🏆 净室测试 - Phase 1: 系统重置")
    print("=" * 50)

    success = reset_database()

    if success:
        print("✅ Phase 1 完成，数据库已清空")
    else:
        print("❌ Phase 1 失败")
        sys.exit(1)

if __name__ == "__main__":
    main()