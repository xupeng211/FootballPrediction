async def _save_daily_data(self, result: DailyDataResult):
    """保存每日数据到数据库 - 使用纯SQL避免ORM性能瓶颈"""
    try:
        from sqlalchemy import text
        from datetime import datetime

        async with self.async_session() as session:
            saved_count = 0
            all_teams_to_save = set()

            # 🏆 步骤1: 收集所有球队数据（不创建ORM对象）
            if result.football_data_matches:
                for match_data in result.football_data_matches:
                    home_team = match_data.get('homeTeam', {})
                    away_team = match_data.get('awayTeam', {})

                    if home_team.get('id'):
                        all_teams_to_save.add((
                            home_team.get('id', 0),
                            home_team.get('name', ''),
                            home_team.get('shortName', ''),
                        ))

                    if away_team.get('id'):
                        all_teams_to_save.add((
                            away_team.get('id', 0),
                            away_team.get('name', ''),
                            away_team.get('shortName', ''),
                        ))

            if result.fotmob_matches:
                for match_data in result.fotmob_matches:
                    home_team = match_data.get('home', {})
                    away_team = match_data.get('away', {})

                    if home_team.get('id'):
                        all_teams_to_save.add((
                            home_team.get('id', 0),
                            home_team.get('name', ''),
                            home_team.get('shortName', ''),
                        ))

                    if away_team.get('id'):
                        all_teams_to_save.add((
                            away_team.get('id', 0),
                            away_team.get('name', ''),
                            away_team.get('shortName', ''),
                        ))

            # 🛡️ 步骤2: 使用纯SQL批量保存球队（秒级完成）
            if all_teams_to_save:
                logger.info(f"🏆 纯SQL保存 {len(all_teams_to_save)} 个球队...")

                # 预定义球队插入SQL语句
                sql_team = text("""
                    INSERT INTO teams (id, name, short_name, country, venue, website, created_at, updated_at)
                    VALUES (:id, :name, :short_name, 'Unknown', '', '', NOW(), NOW())
                    ON CONFLICT (id) DO NOTHING
                """)

                # 批量插入球队
                for team_id, name, short_name in all_teams_to_save:
                    if team_id > 0:
                        try:
                            await session.execute(sql_team, {
                                'id': team_id,
                                'name': name or f"Team_{team_id}",
                                'short_name': short_name or name or f"Team_{team_id}"
                            })
                        except Exception as e:
                            if "Temporary failure in name resolution" in str(e):
                                logger.warning(f"⚠️ SQL球队 {team_id} ({name}) 跳过: {e}")
                            else:
                                logger.error(f"❌ SQL球队 {team_id} ({name}) 失败: {e}")
                            continue

            # 🎯 步骤3: 使用纯SQL保存比赛数据
            sql_match = text("""
                INSERT INTO matches (home_team_id, away_team_id, home_score, away_score,
                                    match_date, status, league_id, season, created_at, updated_at)
                VALUES (:home_team_id, :away_team_id, :home_score, :away_score,
                        :match_date, :status, :league_id, :season, NOW(), NOW())
                ON CONFLICT DO NOTHING
            """)

            # 处理Football-Data.org比赛
            if result.football_data_matches:
                for match_data in result.football_data_matches:
                    try:
                        home_team = match_data.get('homeTeam', {})
                        away_team = match_data.get('awayTeam', {})
                        score = match_data.get('score', {})

                        home_team_id = home_team.get('id', 0)
                        away_team_id = away_team.get('id', 0)

                        if home_team_id == 0 or away_team_id == 0:
                            continue

                        # 解析比赛时间
                        raw_date = datetime.fromisoformat(match_data.get('utcDate', f"{result.date}T15:00:00Z"))
                        match_date = raw_date.replace(tzinfo=None) if raw_date.tzinfo else raw_date

                        # 纯SQL插入比赛
                        await session.execute(sql_match, {
                            'home_team_id': home_team_id,
                            'away_team_id': away_team_id,
                            'home_score': score.get('fullTime', {}).get('home', 0),
                            'away_score': score.get('fullTime', {}).get('away', 0),
                            'match_date': match_date,
                            'status': match_data.get('status', 'SCHEDULED'),
                            'league_id': match_data.get('competition', {}).get('id', 0),
                            'season': match_data.get('season', {}).get('startDate', '')[:4] if match_data.get('season') else result.date[:4]
                        })

                        saved_count += 1

                    except Exception as e:
                        logger.error(f"❌ SQL Football-Data比赛失败: {e}")
                        continue

            # 处理FotMob比赛
            if result.fotmob_matches:
                for match_data in result.fotmob_matches:
                    try:
                        match_info = match_data.get('matchInfo', {})
                        if not match_info:
                            continue

                        home_team = match_data.get('home', {})
                        away_team = match_data.get('away', {})

                        home_team_id = home_team.get('id', 0)
                        away_team_id = away_team.get('id', 0)

                        if home_team_id == 0 or away_team_id == 0:
                            continue

                        # 解析日期
                        match_date_str = match_info.get('startDate', {}).get('ts', None)
                        if not match_date_str:
                            match_date_str = match_info.get('time', {}).get('longTs', None)

                        if not match_date_str:
                            continue

                        try:
                            raw_date = datetime.fromisoformat(match_date_str.replace('Z', '+00:00'))
                            match_date = raw_date.replace(tzinfo=None) if raw_date.tzinfo else raw_date
                        except ValueError:
                            try:
                                raw_date = datetime.strptime(match_date_str, '%d.%m.%Y %H:%M')
                                match_date = raw_date
                            except ValueError:
                                timestamp = int(match_date_str) / 1000
                                match_date = datetime.fromtimestamp(timestamp)

                        # 解析比分和状态
                        status_str = match_info.get('status', {}).get('scoreStr', '0-0')
                        if isinstance(status_str, str) and ':' in status_str:
                            scores = status_str.split(':')
                            home_score_val = int(scores[0])
                            away_score_val = int(scores[1])
                        else:
                            home_score_val = 0
                            away_score_val = 0

                        status = 'CANCELLED' if match_info.get('status', {}).get('cancelled', False) else ('FINISHED' if ':' in status_str and status_str != '0-0' else 'SCHEDULED')

                        # 纯SQL插入FotMob比赛
                        await session.execute(sql_match, {
                            'home_team_id': home_team_id,
                            'away_team_id': away_team_id,
                            'home_score': home_score_val,
                            'away_score': away_score_val,
                            'match_date': match_date,
                            'status': status,
                            'league_id': 0,
                            'season': result.date[:4]
                        })

                        saved_count += 1

                    except Exception as e:
                        logger.error(f"❌ SQL FotMob比赛失败: {e}")
                        continue

            # 提交所有事务 - 纯SQL方式应该是秒级完成
            await session.commit()
            logger.info(f"✅ 纯SQL数据保存成功: {result.date} - {saved_count} 场新比赛")

    except Exception as e:
        logger.error(f"❌ 纯SQL数据保存失败 {result.date}: {e}")
        import traceback
        logger.error(f"🐛 SQL保存失败详情: {traceback.format_exc()}")
        raise
