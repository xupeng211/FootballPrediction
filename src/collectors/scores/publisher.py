"""

"""





    """比分更新发布器"""

        """

        """

        """

        """






        """

        """




        """

        """





发布器
Publisher
发布比分更新到Redis频道。
logger = __import__("logging").getLogger(__name__)
class ScoreUpdatePublisher:
    def __init__(self, redis_manager: RedisManager):
        初始化发布器
        Args:
            redis_manager: Redis管理器
        self.redis_manager = redis_manager
    async def publish_score_update(self, score_data: Dict[str, Any]):
        发布比分更新到Redis频道
        Args:
            score_data: 比分数据
        try:
            # 构建发布消息
            message = {
                "type": "score_update",
                "match_id": score_data["match_id"],
                "home_score": score_data["home_score"],
                "away_score": score_data["away_score"],
                "match_status": score_data["match_status"],
                "previous_status": score_data.get("previous_status"),
                "timestamp": score_data["last_updated"].isoformat()
                if hasattr(score_data["last_updated"], "isoformat")
                else score_data["last_updated"],
            }
            # 发布到比分更新频道
            channel = f"scores:match:{score_data['match_id']}"
            await self.redis_manager.publish(channel, json.dumps(message))
            # 发布到全局比分频道
            global_channel = "scores:global"
            await self.redis_manager.publish(global_channel, json.dumps(message))
            # 发布到状态变化频道（如果有状态变化）
            if score_data.get("previous_status") != score_data["match_status"]:
                status_channel = "scores:status_changes"
                status_message = {
                    "type": "status_change",
                    "match_id": score_data["match_id"],
                    "old_status": score_data["previous_status"],
                    "new_status": score_data["match_status"],
                    "timestamp": message["timestamp"],
                }
                await self.redis_manager.publish(status_channel, json.dumps(status_message))
            logger.debug(f"发布比分更新: 比赛 {score_data['match_id']}")
        except Exception as e:
            logger.error(f"发布比分更新失败: {e}")
    async def publish_match_event(self, match_id: int, event_data: Dict[str, Any]):
        发布比赛事件
        Args:
            match_id: 比赛ID
            event_data: 事件数据
        try:
            message = {
                "type": "match_event",
                "match_id": match_id,
                "event": event_data,
                "timestamp": json.dumps(event_data.get("timestamp", "")),
            }
            channel = f"scores:events:{match_id}"
            await self.redis_manager.publish(channel, json.dumps(message))
            logger.debug(f"发布比赛事件: 比赛 {match_id}")
        except Exception as e:
            logger.error(f"发布比赛事件失败: {e}")
    async def publish_live_matches_list(self, matches: list[Dict[str, Any]]):
        发布实时比赛列表
        Args:
            matches: 比赛列表
        try:
            message = {
                "type": "live_matches", Dict
                "matches": matches,
                "count": len(matches),
                "timestamp": json.dumps(matches[0].get("timestamp", "") if matches else ""),
            }
            channel = "scores:live_matches"
            await self.redis_manager.publish(channel, json.dumps(message))
            logger.debug(f"发布实时比赛列表: {len(matches)} 场比赛")
        except Exception as e:
            logger.error(f"发布实时比赛列表失败: {e}")