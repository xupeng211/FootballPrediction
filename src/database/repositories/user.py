"""
用户仓储

提供用户数据的访问操作。
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

from sqlalchemy import select, and_, or_, func, desc, asc
from sqlalchemy.orm import selectinload

from .base import BaseRepository, RepositoryConfig
from src.database.models.user import User
from src.database.models.predictions import Prediction


class UserRepository(BaseRepository[User]):
    """用户仓储类"""

    def __init__(self, session, config: Optional[RepositoryConfig] = None):
        super().__init__(session, User, config or RepositoryConfig())

    # ==================== 基础查询 ====================

    async def get_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        return await self.find_one({"username": username})

    async def get_by_email(self, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        return await self.find_one({"email": email})

    async def search_users(self, query: str, limit: int = 20) -> List[User]:
        """搜索用户（按用户名或邮箱）"""
        stmt = (
            select(self.model_class)
            .where(
                or_(
                    self.model_class.username.ilike(f"%{query}%"),
                    self.model_class.email.ilike(f"%{query}%"),
                )
            )
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ==================== 状态相关查询 ====================

    async def get_active_users(self, limit: int = 100) -> List[User]:
        """获取活跃用户"""
        stmt = (
            select(self.model_class)
            .where(self.model_class.is_active is True)
            .order_by(desc(self.model_class.last_login))
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_inactive_users(self, days: int = 30, limit: int = 100) -> List[User]:
        """获取不活跃用户"""
        cutoff_date = datetime.now() - timedelta(days=days)

        stmt = (
            select(self.model_class)
            .where(
                or_(
                    self.model_class.last_login < cutoff_date,
                    self.model_class.last_login.is_(None),
                )
            )
            .order_by(asc(self.model_class.last_login))
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_recent_users(self, days: int = 7, limit: int = 50) -> List[User]:
        """获取最近注册的用户"""
        start_date = datetime.now() - timedelta(days=days)

        stmt = (
            select(self.model_class)
            .where(self.model_class.created_at >= start_date)
            .order_by(desc(self.model_class.created_at))
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ==================== 角色相关查询 ====================

    async def get_by_role(self, role: str, limit: int = 100) -> List[User]:
        """根据角色获取用户"""
        return await self.find({"role": role}, limit=limit)

    async def get_admins(self) -> List[User]:
        """获取管理员用户"""
        return await self.get_by_role("admin")

    async def get_premium_users(self) -> List[User]:
        """获取高级用户"""
        stmt = (
            select(self.model_class)
            .where(
                and_(
                    self.model_class.is_premium is True,
                    self.model_class.is_active is True,
                )
            )
            .order_by(desc(self.model_class.created_at))
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ==================== 统计相关查询 ====================

    async def get_user_statistics(self, user_id: int) -> Dict[str, Any]:
        """获取用户统计信息"""
        user = await self.get_by_id(user_id)
        if not user:
            return {}

        # 获取预测统计
        stmt = select(
            func.count(Prediction.id).label("total_predictions"),
            func.sum(func.case((Prediction.is_correct is True, 1), else_=0)).label(
                "correct_predictions"
            ),
        ).where(Prediction.user_id == user_id)

        pred_result = await self.session.execute(stmt)
        pred_stats = pred_result.first()

        # 计算准确率
        accuracy = 0.0
        if pred_stats and pred_stats.total_predictions:
            accuracy = pred_stats.correct_predictions / pred_stats.total_predictions

        # 计算注册天数
        days_since_registration = (datetime.now() - user.created_at).days + 1

        return {
            "user_id": user_id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "is_premium": user.is_premium,
            "created_at": user.created_at,
            "last_login": user.last_login,
            "days_since_registration": days_since_registration,
            "total_predictions": pred_stats.total_predictions if pred_stats else 0,
            "correct_predictions": pred_stats.correct_predictions if pred_stats else 0,
            "accuracy": accuracy,
        }

    async def get_user_activity_summary(self, days: int = 30) -> Dict[str, Any]:
        """获取用户活动汇总"""
        start_date = datetime.now() - timedelta(days=days)

        # 总用户数
        total_users_stmt = select(func.count(self.model_class.id))
        total_result = await self.session.execute(total_users_stmt)
        total_users = total_result.scalar() or 0

        # 活跃用户数（近期有登录）
        active_users_stmt = select(func.count(self.model_class.id)).where(
            and_(
                self.model_class.last_login >= start_date,
                self.model_class.is_active is True,
            )
        )
        active_result = await self.session.execute(active_users_stmt)
        active_users = active_result.scalar() or 0

        # 新注册用户数
        new_users_stmt = select(func.count(self.model_class.id)).where(
            self.model_class.created_at >= start_date
        )
        new_result = await self.session.execute(new_users_stmt)
        new_users = new_result.scalar() or 0

        # 高级用户数
        premium_users_stmt = select(func.count(self.model_class.id)).where(
            and_(
                self.model_class.is_premium is True, self.model_class.is_active is True
            )
        )
        premium_result = await self.session.execute(premium_users_stmt)
        premium_users = premium_result.scalar() or 0

        # 各角色用户数
        role_stmt = (
            select(
                self.model_class.role, func.count(self.model_class.id).label("count")
            )
            .where(self.model_class.is_active is True)
            .group_by(self.model_class.role)
        )

        role_result = await self.session.execute(role_stmt)
        role_counts = {role: count for role, count in role_result.all()}

        return {
            "period_days": days,
            "total_users": total_users,
            "active_users": active_users,
            "new_users": new_users,
            "premium_users": premium_users,
            "activity_rate": active_users / total_users if total_users > 0 else 0,
            "role_distribution": role_counts,
        }

    async def get_daily_user_registrations(
        self, days: int = 30
    ) -> List[Dict[str, Any]]:
        """获取每日用户注册数"""
        start_date = datetime.now() - timedelta(days=days)

        stmt = (
            select(
                func.date(self.model_class.created_at).label("date"),
                func.count(self.model_class.id).label("count"),
            )
            .where(self.model_class.created_at >= start_date)
            .group_by(func.date(self.model_class.created_at))
            .order_by("date")
        )

        result = await self.session.execute(stmt)
        return [{"date": str(date), "count": count} for date, count in result.all()]

    # ==================== 批量操作 ====================

    async def update_last_login(self, user_id: int) -> bool:
        """更新用户最后登录时间"""
        updates = {"last_login": datetime.now(), "updated_at": datetime.now()}

        updated_count = await self.update_batch({"id": user_id}, updates)

        return updated_count > 0

    async def deactivate_inactive_users(self, days: int = 90) -> int:
        """停用长期不活跃的用户"""
        cutoff_date = datetime.now() - timedelta(days=days)

        updates = {"is_active": False, "updated_at": datetime.now()}

        updated_count = await self.update_batch(
            {"last_login": cutoff_date, "is_active": True}, updates
        )

        if updated_count > 0:
            self.logger.info(f"Deactivated {updated_count} inactive users")

        return updated_count

    async def bulk_update_role(self, user_ids: List[int], new_role: str) -> int:
        """批量更新用户角色"""
        updates = {"role": new_role, "updated_at": datetime.now()}

        # 使用IN子句更新多个ID
        stmt = select(self.model_class).where(self.model_class.id.in_(user_ids))
        result = await self.session.execute(stmt)
        entities = result.scalars().all()

        for entity in entities:
            for key, value in updates.items():
                setattr(entity, key, value)

        await self.session.commit()
        return len(entities)

    # ==================== 高级查询 ====================

    async def get_top_predictors(
        self, days: int = 30, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """获取预测准确率最高的用户"""
        start_date = datetime.now() - timedelta(days=days)

        # 查询用户的预测统计
        stmt = (
            select(
                self.model_class,
                func.count(Prediction.id).label("total_predictions"),
                func.sum(func.case((Prediction.is_correct is True, 1), else_=0)).label(
                    "correct_predictions"
                ),
            )
            .join(Prediction, self.model_class.id == Prediction.user_id)
            .where(
                and_(
                    Prediction.created_at >= start_date, Prediction.status == "verified"
                )
            )
            .group_by(self.model_class.id)
            .having(
                func.count(Prediction.id) >= 10  # 至少预测10次
            )
            .order_by(
                desc(
                    func.sum(func.case((Prediction.is_correct is True, 1), else_=0))
                    / func.count(Prediction.id)
                )
            )
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        top_predictors = []

        for row in result:
            user = row[0]
            total = row[1]
            correct = row[2]
            accuracy = correct / total if total > 0 else 0

            top_predictors.append(
                {
                    "user_id": user.id,
                    "username": user.username,
                    "total_predictions": total,
                    "correct_predictions": correct,
                    "accuracy": accuracy,
                }
            )

        return top_predictors

    async def get_user_prediction_history(
        self, user_id: int, limit: int = 50, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取用户的预测历史"""
        stmt = (
            select(Prediction)
            .options(selectinload(Prediction.match))
            .where(Prediction.user_id == user_id)
            .order_by(desc(Prediction.created_at))
            .limit(limit)
        )

        if status:
            stmt = stmt.where(Prediction.status == status)

        result = await self.session.execute(stmt)
        predictions = result.scalars().all()

        history = []
        for pred in predictions:
            history.append(
                {
                    "id": pred.id,
                    "match_id": pred.match_id,
                    "match": {
                        "home_team": pred.match.home_team.name
                        if pred.match and pred.match.home_team
                        else None,
                        "away_team": pred.match.away_team.name
                        if pred.match and pred.match.away_team
                        else None,
                        "match_time": pred.match.match_time if pred.match else None,
                    },
                    "predicted_result": pred.predicted_result,
                    "confidence": pred.confidence,
                    "status": pred.status.value,
                    "is_correct": pred.is_correct,
                    "created_at": pred.created_at,
                }
            )

        return history
