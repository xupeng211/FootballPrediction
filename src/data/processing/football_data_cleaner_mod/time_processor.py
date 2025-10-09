"""
时间处理器模块

负责处理各种时间格式的转换和标准化。
"""



class TimeProcessor:
    """时间处理器"""

    def __init__(self):
        """初始化时间处理器"""
        self.logger = logging.getLogger(f"cleaner.{self.__class__.__name__}")

    def to_utc_time(self, time_str: Optional[str]) -> Optional[str]:
        """
        时间统一转换为UTC

        Args:
            time_str: 时间字符串

        Returns:
            Optional[str]: UTC时间字符串，无效则返回None
        """
        if not time_str:
            return None

        try:
            # 处理不同的时间格式
            if time_str.endswith("Z"):
                dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
            elif "+" in time_str or time_str.endswith("UTC"):
                dt = datetime.fromisoformat(time_str.replace("UTC", "+00:00"))
            else:
                # 假设是UTC时间
                dt = datetime.fromisoformat(time_str).replace(tzinfo=timezone.utc)

            return dt.astimezone(timezone.utc).isoformat()

        except (ValueError, TypeError) as e:
            self.logger.warning(f"Invalid time format: {time_str}, error: {str(e)}")
            return None

    def extract_season(self, season_data: dict) -> Optional[str]:
        """
        提取赛季信息

        Args:
            season_data: 赛季数据字典

        Returns:
            Optional[str]: 赛季字符串，无效则返回None
        """
        if not season_data:
            return None


        # 尝试不同的赛季格式
        season_id = season_data.get("id")
        if season_id:
            return str(season_id)

        # 从开始和结束年份构建赛季
        start_date = season_data.get("startDate")
        end_date = season_data.get("endDate")
        if start_date and end_date:
            try:
                start_year = datetime.fromisoformat(
                    start_date.replace("Z", "+00:00")
                ).year
                end_year = datetime.fromisoformat(end_date.replace("Z", "+00:00")).year
                return f"{start_year}-{end_year}"
            except ValueError:
                pass

        return None