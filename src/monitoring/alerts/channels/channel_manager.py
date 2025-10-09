"""
Jf Sh
Alert Channel Manager

@	Jf S
Manages all alert channels.
"""

import logging
from typing import Any, Dict, List

from .base_channel import BaseAlertChannel
from ...alert_manager_mod.models import Alert

logger = logging.getLogger(__name__)


class AlertChannelManager:
    """
    Jf Sh
    Alert Channel Manager

    @	Jf S
    Manages all alert channels.
    """

    def __init__(self):
        """Sh"""
        self.channels: Dict[str, BaseAlertChannel] = {}
        self.logger = logging.getLogger(__name__)

    def register_channel(self, channel: BaseAlertChannel):
        """
        Jf S
        Register Alert Channel

        Args:
            channel: Jf Sa / Alert channel object
        """
        self.channels[channel.name] = channel
        self.logger.info(f"Registered alert channel: {channel.name}")

    def unregister_channel(self, name: str):
        """
               Jf S
               Unregister Alert Channel

               Args:
                   name:  S
        / Channel name
        """
        if name in self.channels:
            del self.channels[name]
            self.logger.info(f"Unregistered alert channel: {name}")

    def get_channel(self, name: str) -> BaseAlertChannel | None:
        """
               Jf S
               Get Alert Channel

               Args:
                   name:  S
        / Channel name

               Returns:
                   Optional[BaseAlertChannel]: Jf Sa / Alert channel object
        """
        return self.channels.get(name)

    def get_enabled_channels(self) -> List[BaseAlertChannel]:
        """
        /( S
        Get Enabled Channels

        Returns:
            List[BaseAlertChannel]: /( Sh / List of enabled channels
        """
        return [channel for channel in self.channels.values() if channel.is_enabled()]

    async def send_to_all(
        self, alert: Alert, channel_names: List[str] | None = None
    ) -> Dict[str, bool]:
        """
                Jf0@	 S
                Send Alert to All Channels

                Args:
                    alert: Jfa / Alert object
                    channel_names:  S
        h / Specific channel names list

                Returns:
                    Dict[str, bool]: Ӝ / Send results
        """
        results = {}

        if channel_names:
            # 0 S
            for name in channel_names:
                if name in self.channels:
                    results[name] = await self.channels[name].send(alert)
                else:
                    results[name] = False
        else:
            # 0@	/( S
            for name, channel in self.channels.items():
                if channel.is_enabled():
                    results[name] = await channel.send(alert)

        return results

    async def send_batch_to_all(
        self, alerts: List[Alert], channel_names: List[str] | None = None
    ) -> Dict[str, Dict[str, bool]]:
        """
                yJf0@	 S
                Send Batch Alerts to All Channels

                Args:
                    alerts: Jfh / List of alerts
                    channel_names:  S
        h / Specific channel names list

                Returns:
                    Dict[str, Dict[str, bool]]: Ӝ / Send results
        """
        results = {}

        if channel_names:
            # 0 S
            for name in channel_names:
                if name in self.channels:
                    results[name] = await self.channels[name].send_batch(alerts)
                else:
                    results[name] = {alert.alert_id: False for alert in alerts}
        else:
            # 0@	/( S
            for name, channel in self.channels.items():
                if channel.is_enabled():
                    results[name] = await channel.send_batch(alerts)

        return results

    def get_channel_status(self) -> Dict[str, Dict[str, Any]]:
        """
         S
        Get Channel Status

        Returns:
            Dict[str, Dict[str, Any]]:  So / Channel status information
        """
        status = {}
        for name, channel in self.channels.items():
            status[name] = {
                "type": channel.__class__.__name__,
                "enabled": channel.is_enabled(),
                "config_keys": list(channel.config.keys()),
            }
        return status

    def enable_channel(self, name: str) -> bool:
        """
               /( S
               Enable Channel

               Args:
                   name:  S
        / Channel name

               Returns:
                   bool: /& / Whether successful
        """
        if name in self.channels:
            self.channels[name].enable()
            self.logger.info(f"Enabled channel: {name}")
            return True
        return False

    def disable_channel(self, name: str) -> bool:
        """
               ( S
               Disable Channel

               Args:
                   name:  S
        / Channel name

               Returns:
                   bool: /& / Whether successful
        """
        if name in self.channels:
            self.channels[name].disable()
            self.logger.info(f"Disabled channel: {name}")
            return True
        return False

    def get_channel_count(self) -> Dict[str, int]:
        """
         Sߡ
        Get Channel Statistics

        Returns:
            Dict[str, int]:  Sߡo / Channel statistics
        """
        enabled_count = sum(
            1 for channel in self.channels.values() if channel.is_enabled()
        )
        return {
            "total": len(self.channels),
            "enabled": enabled_count,
            "disabled": len(self.channels) - enabled_count,
        }

    async def test_all_channels(self) -> Dict[str, bool]:
        """
        K@	 S
        Test All Channels

        Returns:
            Dict[str, bool]: KӜ / Test results
        """
        results = {}
        for name, channel in self.channels.items():
            try:
                # KJf
                test_alert = Alert(
                    alert_id=f"test-{name}-{int(__import__('time').time())}",
                    title="Test Alert",
                    message="This is a test alert",
                    level=Alert.objects.level.INFO,
                    source="channel_manager",
                )
                results[name] = await channel.send(test_alert)
            except Exception as e:
                self.logger.error(f"Failed to test channel {name}: {e}")
                results[name] = False

        return results
