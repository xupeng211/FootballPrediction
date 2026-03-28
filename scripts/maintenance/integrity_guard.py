#!/usr/bin/env python3
"""
TITAN-V4.46.5 数据完整性卫士
=====================================

每日自动运行，确保 L1/L2/L3 数据对齐

功能:
1. 对比 matches, raw_match_data, l3_features 三张表的记录数
2. 检测数据缺失
3. 生成修复建议

用法:
    npm run status
    docker-compose -f docker-compose.dev.yml exec -T dev python scripts/maintenance/integrity_guard.py

添加到容器内 crontab:
    0 6 * * * python /app/scripts/maintenance/integrity_guard.py
"""

import sys
import os
from datetime import datetime

# 添加项目根目录到 Python 路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("❌ 请安装 psycopg2: pip install psycopg2-binary")
    sys.exit(1)

# 数据库配置
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'db'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'football_db'),
    'user': os.getenv('DB_USER', 'football_user'),
    'password': os.getenv('DB_PASSWORD', '')
}

# ============================================================================
# TITAN 数据完整性卫士 v4.46.5
# ============================================================================


class IntegrityGuard:
    """数据完整性守护者"""

    def __init__(self):
        self.conn = None
        self.l1_count = 0
        self.l2_count = 0
        self.l3_count = 0
        self.missing_l2 = []
        self.missing_l3 = []

    def connect(self):
        """建立数据库连接"""
        try:
            self.conn = psycopg2.connect(
                host=DB_CONFIG['host'],
                port=DB_CONFIG['port'],
                database=DB_CONFIG['database'],
                user=DB_CONFIG['user'],
                password=DB_CONFIG['password']
            )
            print(f"✅ 已连接数据库: {DB_CONFIG['host']}:{DB_CONFIG['port']}")
            return True
        except Exception as e:
            print(f"❌ 数据库连接失败: {e}")
            return False

    def check_alignment(self):
        """检查 L1/L2/L3 数据对齐"""
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)

        # L1: matches 表
        cursor.execute("SELECT COUNT(*) as count FROM matches")
        self.l1_count = cursor.fetchone()['count']
        print(f"  L1 (matches): {self.l1_count} 条记录")

        # L2: raw_match_data 表
        cursor.execute("SELECT COUNT(*) as count FROM raw_match_data")
        self.l2_count = cursor.fetchone()['count']
        print(f"  L2 (raw_match_data): {self.l2_count} 条记录")

        # L3: l3_features 表
        cursor.execute("SELECT COUNT(*) as count FROM l3_features")
        self.l3_count = cursor.fetchone()['count']
        print(f"  L3 (l3_features): {self.l3_count} 条记录")

        # 计算完整性百分比
        if self.l1_count > 0:
            l2_rate = (self.l2_count / self.l1_count) * 100
            l3_rate = (self.l3_count / self.l1_count) * 100
            print(f"  L2 完整性: {l2_rate:.1f}%")
            print(f"  L3 完整性: {l3_rate:.1f}%")

        # 检测缺失的 L2 数据
        cursor.execute("""
            SELECT m.match_id, m.home_team, m.away_team
            FROM matches m
            LEFT JOIN raw_match_data r ON m.match_id = r.match_id
            WHERE r.match_id IS NULL
            LIMIT 20
        """)
        self.missing_l2 = cursor.fetchall()
        if self.missing_l2:
            print(f"\n⚠️  检测到 {len(self.missing_l2)} 条缺失 L2 数据的记录（仅显示前 20 条）")

        # 检测缺失的 L3 数据
        cursor.execute("""
            SELECT m.match_id, m.home_team, m.away_team
            FROM matches m
            LEFT JOIN l3_features l ON m.match_id = l.match_id
            WHERE l.match_id IS NULL
            LIMIT 20
        """)
        self.missing_l3 = cursor.fetchall()
        if self.missing_l3:
            print(f"\n⚠️  检测到 {len(self.missing_l3)} 条缺失 L3 数据的记录（仅显示前 20 条）")

        cursor.close()

    def generate_fix_commands(self):
        """生成修复命令"""
        if not self.missing_l2 and not self.missing_l3:
            print("\n✅ 数据完整性良好，无需修复")
            return

        print("\n" + "=" * 60)
        print("修复建议")
        print("=" * 60)

        if self.missing_l2:
            print("\n缺失 L2 数据的比赛:")
            for match in self.missing_l2[:5]:
                print(f"  - {match['home_team']} vs {match['away_team']} ({match['match_id']})")
            if len(self.missing_l2) > 5:
                print(f"  ... 还有 {len(self.missing_l2) - 5} 条")

            print("\n修复命令:")
            print("  docker-compose -f docker-compose.dev.yml exec dev npm start -- --match-ids " + ",".join([m['match_id'] for m in self.missing_l2[:10]]))

        if self.missing_l3:
            print("\n缺失 L3 数据的比赛:")
            for match in self.missing_l3[:5]:
                print(f"  - {match['home_team']} vs {match['away_team']} ({match['match_id']})")
            if len(self.missing_l3) > 5:
                print(f"  ... 还有 {len(self.missing_l3) - 5} 条")

            print("\n修复命令:")
            print("  docker-compose -f docker-compose.dev.yml exec dev npm run smelt -- --match-ids " + ",".join([m['match_id'] for m in self.missing_l3[:10]]))

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            print("\n✅ 数据库连接已关闭")

    def run(self):
        """运行完整性检查"""
        print("=" * 60)
        print("TITAN 数据完整性卫士 v4.46.5")
        print("=" * 60)
        print(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 60)

        if not self.connect():
            return

        try:
            self.check_alignment()
            self.generate_fix_commands()
        except Exception as e:
            print(f"❌ 检查过程中发生错误: {e}")
        finally:
            self.close()

        print("\n" + "=" * 60)
        print("检查完成")
        print("=" * 60)


if __name__ == "__main__":
    guard = IntegrityGuard()
    guard.run()
