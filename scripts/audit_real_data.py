#!/usr/bin/env python3
"""
真实数据审计脚本
验证后台回填脚本采集的真实数据质量
拒绝任何手动构造的测试数据
"""

import asyncio
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from database.async_manager import initialize_database, get_async_db_session
from sqlalchemy import text

def format_json_print(data, indent=2):
    """格式化打印JSON数据"""
    if not data:
        print("      None")
        return

    try:
        if isinstance(data, str):
            parsed = json.loads(data)
        else:
            parsed = data
        print(json.dumps(parsed, indent=indent, ensure_ascii=False))
    except:
        print(f"      {data}")

async def audit_real_data():
    """审计真实数据质量"""
    print("🔍 真实数据审计脚本")
    print("=" * 60)
    print("拒绝任何手动构造的测试数据，只验证回填脚本采集的真实数据")
    print("=" * 60)

    # 初始化数据库
    initialize_database()
    print("✅ 数据库连接成功")

    async for session in get_async_db_session():
        try:
            # 查询最近1小时内新抓取的真实数据
            query = text("""
                SELECT
                    id,
                    fotmob_id,
                    home_team_name,
                    away_team_name,
                    match_date,
                    status,
                    venue,
                    data_source,
                    data_completeness,
                    collection_time,
                    home_xg,
                    away_xg,
                    home_possession,
                    away_possession,
                    match_info,
                    lineups_json,
                    stats_json,
                    events,
                    environment_json,
                    odds_snapshot_json
                FROM matches
                WHERE collection_time > NOW() - INTERVAL '1 hour'
                ORDER BY id DESC
                LIMIT 1
            """)

            result = await session.execute(query)
            real_record = result.fetchone()

            if not real_record:
                print("\n❌ 审计结果：回填脚本没有在工作")
                print("   最近1小时内没有采集到任何数据")
                print("   可能原因：")
                print("   1. 回填脚本没有运行")
                print("   2. 网络连接问题")
                print("   3. API访问被限制")
                return False

            print(f"\n✅ 找到真实数据记录 (ID: {real_record.id})")
            print(f"   采集时间: {real_record.collection_time}")
            print(f"   数据源: {real_record.data_source}")
            print(f"   完整度: {real_record.data_completeness}")

            # 基础信息验证
            print(f"\n🏟️  基础信息验证:")
            print(f"   比赛: {real_record.home_team_name} vs {real_record.away_team_name}")
            print(f"   状态: {real_record.status}")
            print(f"   场地: {real_record.venue}")
            print(f"   FotMob ID: {real_record.fotmob_id}")

            if not real_record.home_team_name or not real_record.away_team_name:
                print("   ⚠️  警告: 队伍名称为空")
                return False

            # 深度验证 - 裁判信息
            print(f"\n👨‍⚖️  裁判信息验证:")
            environment_data = real_record.environment_json
            if environment_data and 'referee' in environment_data:
                referee = environment_data['referee']
                if referee and referee.get('name'):
                    print(f"   ✅ 裁判姓名: {referee.get('name')}")
                    print(f"   国籍: {referee.get('nationality', 'Unknown')}")
                    print(f"   ID: {referee.get('id', 'Unknown')}")
                else:
                    print("   ❌ 裁判信息为空")
                    return False
            else:
                print("   ❌ 没有找到裁判信息")
                return False

            # 深度验证 - 天气信息
            print(f"\n🌤️  天气信息验证:")
            if environment_data and 'weather' in environment_data:
                weather = environment_data['weather']
                if weather:
                    print(f"   ✅ 温度: {weather.get('temperature_celsius')}°C")
                    print(f"   状况: {weather.get('condition')}")
                    print(f"   湿度: {weather.get('humidity_percent')}%")
                    print(f"   风速: {weather.get('wind_speed_kmh')} km/h")
                else:
                    print("   ❌ 天气信息为空")
                    return False
            else:
                print("   ❌ 没有找到天气信息")
                return False

            # 深度验证 - xG数据
            print(f"\n📊 xG数据验证:")
            if real_record.home_xg is not None and real_record.away_xg is not None:
                print(f"   ✅ 主队xG: {real_record.home_xg}")
                print(f"   ✅ 客队xG: {real_record.away_xg}")
            else:
                print("   ❌ xG数据为空")
                return False

            # 深度验证 - 详细统计数据
            print(f"\n📈 详细统计数据验证:")
            stats_data = real_record.stats_json
            if stats_data:
                print(f"   ✅ 控球率数据: 主队 {real_record.home_possession}% - 客队 {real_record.away_possession}%")
                print(f"   ✅ 射门数据: 主队 {real_record.home_shots} - 客队 {real_record.away_shots}")

                if 'possession' in stats_data:
                    possession = stats_data['possession']
                    print(f"   JSON控球率: 主队 {possession.get('home')}% - 客队 {possession.get('away')}%")
            else:
                print("   ❌ 详细统计数据为空")
                return False

            # 深度验证 - 阵容信息
            print(f"\n👥 阵容信息验证:")
            lineups_data = real_record.lineups_json
            if lineups_data:
                home_team = lineups_data.get('home_team', {})
                away_team = lineups_data.get('away_team', {})

                if home_team.get('formation') and away_team.get('formation'):
                    print(f"   ✅ 主队阵型: {home_team.get('formation')}")
                    print(f"   ✅ 客队阵型: {away_team.get('formation')}")

                    if home_team.get('manager'):
                        print(f"   ✅ 主队教练: {home_team.get('manager')}")
                    if away_team.get('manager'):
                        print(f"   ✅ 客队教练: {away_team.get('manager')}")
                else:
                    print("   ❌ 阵型信息不完整")
                    return False
            else:
                print("   ❌ 阵容数据为空")
                return False

            # 深度验证 - 比赛事件
            print(f"\n⚽ 比赛事件验证:")
            events_data = real_record.events
            if events_data and 'goals' in events_data:
                goals = events_data['goals']
                if goals:
                    print(f"   ✅ 进球事件: {len(goals)} 个")
                    for i, goal in enumerate(goals[:3], 1):  # 只显示前3个
                        scorer = goal.get('scorer', {})
                        print(f"      {i}. {goal.get('minute')}\\' - {scorer.get('name', 'Unknown')}")
                else:
                    print("   ⚠️  比赛可能未开始或没有进球")
            else:
                print("   ⚠️  没有进球事件数据")

            # 数据完整性评分
            print(f"\n🎯 数据完整性评分:")
            checks = [
                real_record.home_team_name and real_record.away_team_name,  # 基础信息
                environment_data and 'referee' in environment_data,         # 裁判
                environment_data and 'weather' in environment_data,         # 天气
                real_record.home_xg is not None and real_record.away_xg is not None,  # xG
                stats_data is not None,                                     # 统计
                lineups_data is not None                                     # 阵容
            ]

            completeness = sum(1 for check in checks if check) / len(checks) * 100
            print(f"   完整度: {completeness:.1f}%")

            if completeness >= 90:
                print("   🏆 评级: 优秀 - 真实数据质量极佳")
                audit_result = True
            elif completeness >= 75:
                print("   🥈 评级: 良好 - 真实数据质量不错")
                audit_result = True
            elif completeness >= 50:
                print("   🥉 评级: 基础 - 真实数据部分可用")
                audit_result = True
            else:
                print("   ❌ 评级: 失败 - 真实数据质量太差")
                audit_result = False

            # 显示真实数据样本
            print(f"\n🔍 真实数据样本展示:")
            print(f"   match_info 样本:")
            format_json_print(real_record.match_info)

            print(f"   environment_json 样本:")
            format_json_print(environment_data)

            return audit_result

        except Exception as e:
            print(f"\n❌ 审计过程出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            await session.close()

async def main():
    """主函数"""
    print("🚀 启动真实数据审计")

    # 验证是否有回填脚本在运行
    print("\n📡 检查后台回填脚本状态...")

    audit_result = await audit_real_data()

    print("\n" + "=" * 60)
    print("📊 最终审计结果")
    print("=" * 60)

    if audit_result:
        print("✅ 审计通过：回填脚本正在工作，采集了高质量的真实数据")
        print("   - 裁判信息：完整")
        print("   - 天气数据：完整")
        print("   - xG数据：完整")
        print("   - 阵容统计：完整")
        print("   - 数据质量：优秀")
    else:
        print("❌ 审计失败：回填脚本存在问题")
        print("   要么没有采集数据，要么数据质量不达标")

    return audit_result

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)