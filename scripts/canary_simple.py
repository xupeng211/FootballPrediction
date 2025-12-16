#!/usr/bin/env python3
"""
简化的L2数据冒烟测试脚本

直接使用asyncpg连接数据库，验证新字段填充情况
"""

import asyncio
import asyncpg
import random
import time
import argparse
import logging
import json
import httpx
from typing import Dict, Any, List, Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SimpleCanary:
    """简化的冒烟测试器"""

    def __init__(self, db_url: str):
        self.db_url = db_url
        self.http_client = None

    async def initialize(self):
        """初始化HTTP客户端"""
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )
        logger.info("✅ HTTP客户端初始化完成")

    async def get_random_matches(self, limit: int) -> List[Dict[str, Any]]:
        """从数据库随机获取比赛样本"""
        logger.info(f"🎲 从数据库随机获取 {limit} 场比赛...")

        # 解析数据库URL
        import urllib.parse
        parsed = urllib.parse.urlparse(self.db_url.replace("postgresql+asyncpg://", "postgresql://"))

        conn = await asyncpg.connect(
            host=parsed.hostname,
            port=parsed.port,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path.lstrip("/")
        )

        try:
            # 获取总比赛数
            total_count = await conn.fetchval("SELECT COUNT(*) FROM matches WHERE fotmob_id IS NOT NULL")
            if total_count == 0:
                logger.error("❌ 数据库中没有找到有fotmob_id的比赛")
                return []

            logger.info(f"📊 数据库中共有 {total_count} 场有fotmob_id的比赛")

            # 随机选择比赛
            rows = await conn.fetch("""
                SELECT id, fotmob_id, home_team_name, away_team_name
                FROM matches
                WHERE fotmob_id IS NOT NULL
                ORDER BY RANDOM()
                LIMIT $1
            """, limit)

            matches = [dict(row) for row in rows]
            logger.info(f"✅ 成功获取 {len(matches)} 场随机比赛")
            return matches

        finally:
            await conn.close()

    async def collect_fotmob_data(self, fotmob_id: int) -> Optional[Dict[str, Any]]:
        """采集FotMob数据"""
        url = f"https://www.fotmob.com/api/matchDetails?matchId={fotmob_id}"

        try:
            logger.info(f"   📡 采集FotMob数据: {fotmob_id}")
            response = await self.http_client.get(url)

            if response.status_code == 200:
                data = response.json()
                logger.info(f"   ✅ 采集成功: {fotmob_id}")
                return data
            else:
                logger.warning(f"   ⚠️ HTTP错误 {response.status_code}: {fotmob_id}")
                return None

        except Exception as e:
            logger.error(f"   ❌ 采集异常 {fotmob_id}: {e}")
            return None

    def extract_shotmap_data(self, content: Dict[str, Any]) -> List[Dict[str, Any]]:
        """提取射图谱数据"""
        shots = []
        try:
            if "shotmap" in content and isinstance(content["shotmap"], dict):
                shotmap_data = content["shotmap"]
                if "shots" in shotmap_data and isinstance(shotmap_data["shots"], list):
                    shots = shotmap_data["shots"]
                    logger.info(f"   🎯 提取到 {len(shots)} 个射门数据")
        except Exception as e:
            logger.error(f"   ❌ 射谱提取失败: {e}")

        return shots

    def extract_match_events(self, content: Dict[str, Any]) -> List[Dict[str, Any]]:
        """提取比赛事件数据"""
        events = []
        try:
            if "events" in content and isinstance(content["events"], dict):
                events_data = content["events"]
                if "events" in events_data and isinstance(events_data["events"], list):
                    events = events_data["events"]
                    logger.info(f"   ⚽️ 提取到 {len(events)} 个事件数据")
        except Exception as e:
            logger.error(f"   ❌ 事件提取失败: {e}")

        return events

    def extract_match_metadata(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """提取比赛元数据"""
        metadata = {
            "referee": None,
            "stadium": None,
            "attendance": None,
            "city": None,
            "country": None
        }

        try:
            if "matchFacts" in content and isinstance(content["matchFacts"], dict):
                match_facts = content["matchFacts"]
                if "infoBox" in match_facts and isinstance(match_facts["infoBox"], dict):
                    info_box = match_facts["infoBox"]

                    # 裁判信息
                    if "Referee" in info_box and isinstance(info_box["Referee"], dict):
                        metadata["referee"] = info_box["Referee"].get("text")

                    # 球场信息
                    if "Stadium" in info_box and isinstance(info_box["Stadium"], dict):
                        stadium_info = info_box["Stadium"]
                        metadata["stadium"] = stadium_info.get("name")
                        metadata["city"] = stadium_info.get("city")
                        metadata["country"] = stadium_info.get("country")

                    # 观众人数
                    if "Attendance" in info_box:
                        attendance_info = info_box["Attendance"]
                        if isinstance(attendance_info, dict) and "value" in attendance_info:
                            try:
                                metadata["attendance"] = int(attendance_info["value"])
                            except (ValueError, TypeError):
                                pass
                        elif isinstance(attendance_info, (int, str)):
                            try:
                                metadata["attendance"] = int(attendance_info)
                            except (ValueError, TypeError):
                                pass

            if metadata["referee"] or metadata["stadium"]:
                logger.info(f"   🏟️ 提取元数据: 裁判={metadata['referee']}, 球场={metadata['stadium']}")

        except Exception as e:
            logger.error(f"   ❌ 元数据提取失败: {e}")

        return metadata

    async def update_database(self, match_id: int, update_data: Dict[str, Any]) -> bool:
        """更新数据库"""
        try:
            # 解析数据库URL
            import urllib.parse
            parsed = urllib.parse.urlparse(self.db_url.replace("postgresql+asyncpg://", "postgresql://"))

            conn = await asyncpg.connect(
                host=parsed.hostname,
                port=parsed.port,
                user=parsed.username,
                password=parsed.password,
                database=parsed.path.lstrip("/")
            )

            try:
                # 构建更新语句
                set_clauses = []
                params = {"match_id": match_id}
                param_index = 1

                for key, value in update_data.items():
                    if value is not None:
                        param_index += 1
                        if isinstance(value, list):
                            # JSON数组
                            set_clauses.append(f"{key} = ${param_index}")
                            params[f"param_{param_index}"] = json.dumps(value)
                        elif isinstance(value, (str, int, float)):
                            set_clauses.append(f"{key} = ${param_index}")
                            params[f"param_{param_index}"] = value

                if not set_clauses:
                    logger.warning(f"   ⚠️ 没有数据需要更新: match_id={match_id}")
                    return True

                query = f"""
                    UPDATE matches
                    SET {', '.join(set_clauses)}
                    WHERE id = $1
                """

                await conn.execute(query, *params.values())
                logger.info(f"   ✅ 数据库更新成功: match_id={match_id}")
                return True

            finally:
                await conn.close()

        except Exception as e:
            logger.error(f"   ❌ 数据库更新失败 {match_id}: {e}")
            return False

    async def process_match(self, match: Dict[str, Any]) -> Dict[str, Any]:
        """处理单场比赛"""
        match_id = match["id"]
        fotmob_id = match["fotmob_id"]
        home_team = match["home_team_name"]
        away_team = match["away_team_name"]

        logger.info(f"⚽ 处理比赛: {home_team} vs {away_team} (ID: {match_id}, FotMob ID: {fotmob_id})")

        try:
            # 采集FotMob数据
            fotmob_data = await self.collect_fotmob_data(fotmob_id)
            if not fotmob_data:
                return {
                    "match_id": match_id,
                    "status": "failed",
                    "reason": "FotMob数据采集失败",
                    "stats": {}
                }

            # 提取content
            content = fotmob_data.get("content", {})
            if not content:
                return {
                    "match_id": match_id,
                    "status": "failed",
                    "reason": "没有content数据",
                    "stats": {}
                }

            # 提取各类数据
            shotmap = self.extract_shotmap_data(content)
            events = self.extract_match_events(content)
            metadata = self.extract_match_metadata(content)

            # 构建更新数据
            update_data = {
                "match_shotmap": shotmap,
                "match_events": events,
                "referee": metadata["referee"],
                "stadium": metadata["stadium"],
                "attendance": metadata["attendance"],
                "city": metadata["city"],
                "country": metadata["country"],
            }

            # 更新数据库
            success = await self.update_database(match_id, update_data)

            # 统计结果
            stats = {
                "shots": len(shotmap),
                "events": len(events),
                "referee": 1 if metadata["referee"] else 0,
                "stadium": 1 if metadata["stadium"] else 0,
                "attendance": 1 if metadata["attendance"] else 0,
            }

            if success:
                logger.info(f"   ✅ 处理成功: {home_team} vs {away_team}")
                logger.info(f"   📊 数据统计: 射门={stats['shots']}, 事件={stats['events']}, 裁判={stats['referee']}, 球场={stats['stadium']}")
                return {
                    "match_id": match_id,
                    "status": "success",
                    "reason": "处理成功",
                    "stats": stats
                }
            else:
                return {
                    "match_id": match_id,
                    "status": "failed",
                    "reason": "数据库更新失败",
                    "stats": stats
                }

        except Exception as e:
            logger.error(f"   ❌ 处理异常 {match_id}: {e}")
            return {
                "match_id": match_id,
                "status": "error",
                "reason": f"处理异常: {str(e)}",
                "stats": {}
            }

    async def run_canary_test(self, limit: int = 5, delay: float = 2.0):
        """运行冒烟测试"""
        logger.info(f"🐦 开始简化冒烟测试 (limit={limit}, delay={delay}s)")
        logger.info("=" * 80)

        # 获取随机比赛
        matches = await self.get_random_matches(limit)
        if not matches:
            logger.error("❌ 无法获取比赛样本，测试终止")
            return

        logger.info(f"📋 测试比赛列表:")
        for i, match in enumerate(matches, 1):
            logger.info(f"   {i}. {match['home_team_name']} vs {match['away_team_name']} (FotMob ID: {match['fotmob_id']})")

        logger.info("\n" + "=" * 80)

        # 处理每场比赛
        results = []
        for i, match in enumerate(matches, 1):
            logger.info(f"\n🔄 处理第 {i}/{len(matches)} 场比赛...")

            result = await self.process_match(match)
            results.append(result)

            # API限流延迟
            if i < len(matches):
                logger.info(f"   ⏱️  等待 {delay}s 后处理下一场比赛...")
                time.sleep(delay)

        # 生成测试报告
        self.generate_report(results)

        logger.info("\n" + "=" * 80)
        logger.info("🎉 简化冒烟测试完成！")

    def generate_report(self, results: List[Dict[str, Any]]):
        """生成测试报告"""
        logger.info("\n📊 冒烟测试报告:")
        logger.info("=" * 50)

        total_matches = len(results)
        successful_matches = len([r for r in results if r["status"] == "success"])
        failed_matches = total_matches - successful_matches

        logger.info(f"总比赛数: {total_matches}")
        logger.info(f"成功: {successful_matches}")
        logger.info(f"失败: {failed_matches}")
        logger.info(f"成功率: {successful_matches/total_matches*100:.1f}%")

        # 统计各字段填充情况
        total_stats = {
            "shots": 0,
            "events": 0,
            "referee": 0,
            "stadium": 0,
            "attendance": 0,
        }

        for result in results:
            stats = result.get("stats", {})
            for key, value in stats.items():
                if key in total_stats:
                    total_stats[key] += value

        logger.info("\n📈 数据填充统计:")
        logger.info(f"   射门数据: {total_stats['shots']} 个")
        logger.info(f"   事件数据: {total_stats['events']} 个")
        logger.info(f"   裁判信息: {total_stats['referee']}/{total_matches}")
        logger.info(f"   球场信息: {total_stats['stadium']}/{total_matches}")
        logger.info(f"   观众信息: {total_stats['attendance']}/{total_matches}")

        # 详细结果
        logger.info("\n📋 详细处理结果:")
        for result in results:
            status_icon = "✅" if result["status"] == "success" else "❌"
            logger.info(f"   {status_icon} 比赛ID {result['match_id']}: {result['reason']}")

    async def close(self):
        """关闭资源"""
        if self.http_client:
            await self.http_client.aclose()
            logger.info("🔐 HTTP客户端已关闭")


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="简化L2数据冒烟测试脚本")
    parser.add_argument("--limit", type=int, default=5, help="测试比赛数量 (默认: 5)")
    parser.add_argument("--delay", type=float, default=2.0, help="API调用间隔秒数 (默认: 2.0)")
    parser.add_argument("--db-host", default="localhost", help="数据库主机")
    parser.add_argument("--db-port", default="5432", help="数据库端口")
    parser.add_argument("--db-name", default="football_prediction", help="数据库名")
    parser.add_argument("--db-user", default="postgres", help="数据库用户")
    parser.add_argument("--db-password", default="postgres", help="数据库密码")

    args = parser.parse_args()

    # 构建数据库URL
    db_url = f"postgresql+asyncpg://{args.db_user}:{args.db_password}@{args.db_host}:{args.db_port}/{args.db_name}"

    # 创建冒烟测试器
    canary = SimpleCanary(db_url=db_url)

    try:
        # 初始化
        await canary.initialize()

        # 运行测试
        await canary.run_canary_test(limit=args.limit, delay=args.delay)

    except KeyboardInterrupt:
        logger.info("\n⚠️ 用户中断测试")
    except Exception as e:
        logger.error(f"❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理资源
        await canary.close()


if __name__ == "__main__":
    asyncio.run(main())