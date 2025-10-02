"""""""
Factory for generating user-related test data.
"""""""

from faker import Faker
import random
from datetime import datetime, timedelta

fake = Faker()


class UserFactory:
    """Factory for generating user-related test data."""""""

    @classmethod
    def generate_user_profile(cls):
        """Generate a user profile."""""""
        return {
            "user_id[": f["]user_{fake.uuid4().hex[:8]}"],""""
            "username[": fake.user_name(),""""
            "]email[": fake.email(),""""
            "]first_name[": fake.first_name(),""""
            "]last_name[": fake.last_name(),""""
            "]age[": random.randint(18, 65),""""
            "]country[": fake.country(),""""
            "]favorite_team[": fake.company(),""""
            "]preferred_league[": random.choice(""""
                ["]Premier League[", "]La Liga[", "]Bundesliga[", "]Serie A[", "]Ligue 1["]""""
            ),
            "]account_created[": datetime.now() - timedelta(days=random.randint(30, 365)),""""
            "]last_login[": datetime.now() - timedelta(days=random.randint(1, 30)),""""
            "]is_active[": True,""""
            "]subscription_type[": random.choice(["]free[", "]premium[", "]vip["]),""""
            "]prediction_accuracy[": round(random.uniform(0.4, 0.8), 3),""""
            "]total_predictions[": random.randint(10, 1000),""""
            "]successful_predictions[": random.randint(5, 800),""""
        }

    @classmethod
    def generate_user_preferences(cls):
        "]""Generate user preferences."""""""
        return {
            "notification_enabled[": random.choice([True, False]),""""
            "]email_notifications[": random.choice([True, False]),""""
            "]push_notifications[": random.choice([True, False]),""""
            "]preferred_odds_format[": random.choice(""""
                ["]decimal[", "]fractional[", "]american["]""""
            ),
            "]default_stake_amount[": random.choice([5, 10, 20, 50, 100]),""""
            "]risk_tolerance[": random.choice(["]low[", "]medium[", "]high["]),""""
            "]favorite_markets[": random.sample(""""
                ["]1X2[", "]BTTS[", "]Over/Under[", "]Correct Score[", "]Both Teams to Score["],": random.randint(1, 3),"""
            ),
            "]preferred_teams[: "fake.company() for _ in range(random.randint(1, 5))",""""
            "]time_zone[": fake.timezone(),""""
            "]language[": random.choice(["]en[", "]es[", "]fr[", "]de[", "]it["]),""""
        }

    @classmethod
    def generate_user_prediction_history(cls, num_predictions=10):
        "]""Generate user prediction history."""""""
        predictions = []
        for _ in range(num_predictions):
            prediction = {
                "prediction_id[": f["]pred_{fake.uuid4().hex[:8]}"],""""
                "user_id[": f["]user_{fake.uuid4().hex[:8]}"],""""
                "match_id[": random.randint(1, 10000),""""
                "]predicted_outcome[": random.choice(["]home_win[", "]draw[", "]away_win["]),""""
                "]predicted_score_home[": random.randint(0, 5),""""
                "]predicted_score_away[": random.randint(0, 5),""""
                "]confidence[": round(random.uniform(0.5, 1.0), 2),""""
                "]stake_amount[": random.choice([5, 10, 20, 50]),""""
                "]odds_taken[": round(random.uniform(1.5, 5.0), 2),""""
                "]actual_outcome[": random.choice(["]home_win[", "]draw[", "]away_win["]),""""
                "]actual_score_home[": random.randint(0, 5),""""
                "]actual_score_away[": random.randint(0, 5),""""
                "]is_correct[": random.choice([True, False]),""""
                "]profit_loss[": round(random.uniform(-50, 100), 2),""""
                "]prediction_time[": datetime.now()""""
                - timedelta(days=random.randint(1, 90)),
                "]match_time[": datetime.now() - timedelta(days=random.randint(0, 89)),""""
            }
            predictions.append(prediction)
        return predictions

    @classmethod
    def generate_active_user(cls):
        "]""Generate an active user profile."""""""
        profile = cls.generate_user_profile()
        profile.update(
            {
                "is_active[": True,""""
                "]last_login[": datetime.now() - timedelta(hours=random.randint(1, 24)),""""
                "]subscription_type[": random.choice(["]premium[", "]vip["]),""""
                "]total_predictions[": random.randint(100, 1000),""""
                "]successful_predictions[": random.randint(50, 800),""""
            }
        )
        return profile

    @classmethod
    def generate_inactive_user(cls):
        "]""Generate an inactive user profile."""""""
        profile = cls.generate_user_profile()
        profile.update(
            {
                "is_active[": False,""""
                "]last_login[": datetime.now() - timedelta(days=random.randint(90, 365)),""""
                "]subscription_type[: "free[","]"""
                "]total_predictions[": random.randint(0, 10),""""
            }
        )
        return profile

    @classmethod
    def generate_new_user(cls):
        "]""Generate a new user profile."""""""
        profile = cls.generate_user_profile()
        profile.update(
            {
                "account_created[": datetime.now()""""
                - timedelta(days=random.randint(1, 7)),
                "]last_login[": datetime.now() - timedelta(hours=random.randint(1, 24)),""""
                "]subscription_type[: "free[","]"""
                "]total_predictions[": 0,""""
                "]successful_predictions[": 0,""""
                "]prediction_accuracy[": 0.0,""""
            }
        )
        return profile

    @classmethod
    def generate_veteran_user(cls):
        "]""Generate a veteran user with extensive history."""""""
        profile = cls.generate_user_profile()
        profile.update(
            {
                "account_created[": datetime.now()""""
                - timedelta(days=random.randint(365, 1000)),
                "]last_login[": datetime.now() - timedelta(hours=random.randint(1, 48)),""""
                "]subscription_type[: "vip[","]"""
                "]total_predictions[": random.randint(500, 5000),""""
                "]successful_predictions[": random.randint(250, 4000),""""
                "]prediction_accuracy[": round(random.uniform(0.6, 0.85), 3),""""
            }
        )
        return profile

    @classmethod
    def generate_user_batch(cls, batch_size=10, user_types=None):
        "]""Generate a batch of users with different types."""""""
        if user_types is None = user_types ["active[", "]inactive[", "]new[", "]veteran["]": users = []": for _ in range(batch_size):": user_type = random.choice(user_types)"
            if user_type =="]active[":": users.append(cls.generate_active_user())": elif user_type =="]inactive[":": users.append(cls.generate_inactive_user())": elif user_type =="]new[":": users.append(cls.generate_new_user())": elif user_type =="]veteran[":": users.append(cls.generate_veteran_user())": return users[""

    @classmethod
    def generate_invalid_user_data(cls):
        "]]""Generate invalid user data for testing error handling."""""""
        invalid_data = [
            # Missing required fields
            {"username[: "test_user["},  # Missing email and other fields["]"]""
            # Invalid email
            {
                "]user_id[: "user_123[","]"""
                "]username[: "test_user[","]"""
                "]email[: "invalid_email[",  # Invalid email format["]"]""
                "]age[": 25,""""
            },
            # Invalid age
            {
                "]user_id[: "user_123[","]"""
                "]username[: "test_user[","]"""
                "]email[: "test@example.com[","]"""
                "]age[": -5,  # Invalid negative age[""""
            },
            # Invalid subscription type
            {
                "]]user_id[: "user_123[","]"""
                "]username[: "test_user[","]"""
                "]email[: "test@example.com[","]"""
                "]subscription_type[: "invalid_type[",  # Invalid subscription["]"]""
            },
            # Invalid accuracy (outside 0-1 range)
            {
                "]user_id[: "user_123[","]"""
                "]username[: "test_user[","]"""
                "]email[: "test@example.com[","]"""
                "]prediction_accuracy[": 1.5,  # Invalid accuracy > 1.0["]"]""
            },
        ]
        return invalid_data
