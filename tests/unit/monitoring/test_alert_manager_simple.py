import os
"""Alert manager tests."""

import pytest

from src.monitoring.alert_manager import AlertManager, AlertLevel


@pytest.mark.unit
class TestAlertManager:
    """Test Alert Manager implementation."""

    @pytest.fixture(scope="class")
    def alert_manager(self):
        """Create a single alert manager instance for all tests in class."""
        # Create only one instance to avoid Prometheus metric conflicts
        return AlertManager()

    def test_initialization(self, alert_manager):
        """Test alert manager initialization."""
        assert alert_manager.alerts == []
        assert alert_manager.rules is not None
        assert len(alert_manager.rules) > 0  # Should have default rules
        assert alert_manager.metrics is not None

    def test_fire_alert(self, alert_manager):
        """Test firing an alert."""
        alert = alert_manager.fire_alert(
            title = os.getenv("TEST_ALERT_MANAGER_SIMPLE_TITLE_28"),
            message = os.getenv("TEST_ALERT_MANAGER_SIMPLE_MESSAGE_28"),
            level=AlertLevel.WARNING,
            source = os.getenv("TEST_ALERT_MANAGER_SIMPLE_SOURCE_29")
        )

        assert alert is not None
        assert alert.title == "Test Alert"
        assert alert.message == "This is a test"
        assert alert.level == AlertLevel.WARNING
        assert alert.source == "test_source"
        assert alert.alert_id is not None

    def test_fire_alert_with_labels(self, alert_manager):
        """Test firing an alert with labels."""
        labels = {"host": "server1", "metric": "cpu"}
        alert = alert_manager.fire_alert(
            title = os.getenv("TEST_ALERT_MANAGER_SIMPLE_TITLE_42"),
            message = os.getenv("TEST_ALERT_MANAGER_SIMPLE_MESSAGE_43"),
            level=AlertLevel.CRITICAL,
            source = os.getenv("TEST_ALERT_MANAGER_SIMPLE_SOURCE_45"),
            labels=labels
        )

        assert alert is not None
        assert alert.labels == labels

    def test_get_active_alerts(self, alert_manager):
        """Test getting active alerts."""
        # Clear previous alerts if any
        alert_manager.alerts.clear()

        # Fire some alerts
        alert1 = alert_manager.fire_alert("Test 1", "Info alert", AlertLevel.INFO, "test")
        alert2 = alert_manager.fire_alert("Test 2", "Warning alert", AlertLevel.WARNING, "test")
        alert3 = alert_manager.fire_alert("Test 3", "Critical alert", AlertLevel.CRITICAL, "test")

        # Get all active alerts (should include previous ones)
        active = alert_manager.get_active_alerts()
        assert len(active) >= 3
        assert alert1 in active
        assert alert2 in active
        assert alert3 in active

        # Filter by level
        warnings = alert_manager.get_active_alerts(level=AlertLevel.WARNING)
        assert len(warnings) >= 1

        # Check that the warning alert has the expected title
        assert any(w.title == "Test 2" for w in warnings)

    def test_resolve_alert(self, alert_manager):
        """Test resolving an alert."""
        # Fire an alert
        alert = alert_manager.fire_alert(
            title = os.getenv("TEST_ALERT_MANAGER_SIMPLE_TITLE_28"),
            message="Test",
            level=AlertLevel.WARNING,
            source="test"
        )

        # It should be active
        assert alert.status.value == "active"

        # Resolve it
        success = alert_manager.resolve_alert(alert.alert_id)
        assert success is True

        # Alert should still be in the list but resolved
        updated = alert_manager.get_active_alerts()
        # Resolved alerts should not be in active alerts
        assert alert not in updated

    def test_resolve_nonexistent_alert(self, alert_manager):
        """Test resolving non-existent alert."""
        success = alert_manager.resolve_alert("nonexistent_id")
        assert success is False

    def test_get_alert_summary(self, alert_manager):
        """Test alert summary."""
        # Get initial counts
        initial_summary = alert_manager.get_alert_summary()
        initial_total = initial_summary["total_alerts"]

        # Fire various alerts
        alert_manager.fire_alert("Info 1", "Test", AlertLevel.INFO, "source1")
        alert_manager.fire_alert("Info 2", "Test", AlertLevel.INFO, "source1")
        alert_manager.fire_alert("Warning 1", "Test", AlertLevel.WARNING, "source2")
        alert_manager.fire_alert("Critical 1", "Test", AlertLevel.CRITICAL, "source3")

        # Get summary
        summary = alert_manager.get_alert_summary()

        # Should have at least 4 new alerts
        assert summary["total_alerts"] >= initial_total + 4
        assert summary["active_alerts"] >= 4
        assert summary["by_level"]["info"] >= 2
        assert summary["by_level"]["warning"] >= 1
        assert summary["by_level"]["critical"] >= 1
        assert summary["by_source"]["source1"] >= 2
        assert summary["by_source"]["source2"] >= 1
        assert summary["by_source"]["source3"] >= 1
        assert summary["critical_alerts"] >= 1

    def test_add_and_remove_rule(self, alert_manager):
        """Test rule management."""
        from src.monitoring.alert_manager import AlertRule, AlertChannel

        # Add a rule
        rule = AlertRule(
            rule_id = os.getenv("TEST_ALERT_MANAGER_SIMPLE_RULE_ID_130"),
            name = os.getenv("TEST_ALERT_MANAGER_SIMPLE_NAME_131"),
            condition = os.getenv("TEST_ALERT_MANAGER_SIMPLE_CONDITION_132"),
            level=AlertLevel.WARNING,
            channels=[AlertChannel.LOG]
        )

        alert_manager.add_rule(rule)
        assert "test_rule" in alert_manager.rules

        # Remove the rule
        success = alert_manager.remove_rule("test_rule")
        assert success is True
        assert "test_rule" not in alert_manager.rules

    def test_throttling_with_rule(self, alert_manager):
        """Test alert throttling when rule is specified."""
        # Use an existing rule that has throttling
        rule_id = os.getenv("TEST_ALERT_MANAGER_SIMPLE_RULE_ID_146")

        # Fire first alert
        alert1 = alert_manager.fire_alert(
            title="Test",
            message = os.getenv("TEST_ALERT_MANAGER_SIMPLE_MESSAGE_150"),
            level=AlertLevel.WARNING,
            source="test",
            rule_id=rule_id
        )
        assert alert1 is not None

        # Fire identical alert immediately (should be throttled)
        alert2 = alert_manager.fire_alert(
            title="Test",
            message = os.getenv("TEST_ALERT_MANAGER_SIMPLE_MESSAGE_150"),
            level=AlertLevel.WARNING,
            source="test",
            rule_id=rule_id
        )
        # Should be throttled (return None)
        assert alert2 is None

    def test_update_quality_metrics(self, alert_manager):
        """Test updating quality metrics."""
        quality_data = {
            "freshness": {
                "table1": {"hours_since_last_update": 5.0}
            },
            "completeness": {
                "table1": {"completeness_ratio": 0.95}
            },
            "overall_score": 0.9
        }

        # Should not raise any errors
        alert_manager.update_quality_metrics(quality_data)

    def test_check_quality_alerts(self, alert_manager):
        """Test checking quality and firing alerts."""
        quality_data = {
            "freshness": {
                "table1": {"hours_since_last_update": 25}  # Should trigger critical
            },
            "completeness": {
                "table1": {"completeness_ratio": 0.7}     # Should trigger critical
            },
            "overall_score": 0.65                           # Should trigger critical
        }

        # Check and fire alerts
        fired_alerts = alert_manager.check_and_fire_quality_alerts(quality_data)

        # Should fire alerts for critical conditions
        assert len(fired_alerts) >= 2

        # Check that alerts were added to manager
        active = alert_manager.get_active_alerts()
        assert len(active) >= len(fired_alerts)