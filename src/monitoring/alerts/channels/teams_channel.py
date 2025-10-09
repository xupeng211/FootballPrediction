"""
Microsoft TeamsJf S
Teams Alert Channel

Microsoft Teams webhookJf
Sends alerts via Microsoft Teams webhook.
"""





class TeamsChannel(BaseAlertChannel):
    """
    Microsoft TeamsJf S
    Teams Alert Channel

    Microsoft Teams webhookJf
    Sends alerts via Microsoft Teams webhook.
    """

    def __init__(self, name: str = "teams", config: Dict[str, Any] | None = None):
        """
               Teams S
               Initialize Teams Channel

               Args:
                   name:  S
        / Channel name
                   config:  SMn / Channel configuration
        """
        super().__init__(name, config)
        self.webhook_url = self.config.get("webhook_url")
        self.title_prefix = self.config.get("title_prefix", "Alert")
        self.theme_color = self.config.get("theme_color", None)  # 9n+n

        if not self.webhook_url:
            self.logger.warning("Teams webhook URL not configured")
            self.enabled = False

    async def send(self, alert: Alert) -> bool:
        """
        Teamso
        Send Teams Message

        Args:
            alert: Jfa / Alert object

        Returns:
            bool: /& / Whether sent successfully
        """
        if not self.is_enabled():
            return False

        try:
            # Teamso<
            payload = {
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "themeColor": self._get_color_by_level(alert.level.value),
                "summary": f"{self.title_prefix}: {alert.title}",
                "sections": [
                    {
                        "activityTitle": f"[{alert.level.value.upper()}] {alert.title}",
                        "activitySubtitle": f"Alert ID: {alert.alert_id}",
                        "facts": [
                            {"name": "Message", "value": alert.message},
                            {"name": "Source", "value": alert.source},
                            {"name": "Severity", "value": alert.severity.value},
                            {"name": "Status", "value": alert.status.value},
                            {
                                "name": "Created At",
                                "value": alert.created_at.strftime(
                                    "%Y-%m-%d %H:%M:%S UTC"
                                ),
                            },
                        ],
                        "markdown": True,
                    }
                ],
            }

            # ~
            if alert.labels:
                labels_text = "\n".join(
                    [f"**{k}**: {v}" for k, v in alert.labels.items()]
                )
                payload["sections"][0]["facts"].append(
                    {"name": "Labels", "value": labels_text}
                )

            if alert.annotations:
                annotations_text = "\n".join(
                    [f"**{k}**: {v}" for k, v in alert.annotations.items()]
                )
                payload["sections"][0]["facts"].append(
                    {"name": "Annotations", "value": annotations_text}
                )

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url, json=payload, timeout=10
                ) as response:
                    success = response.status == 200
                    if success:
                        self.logger.info(f"Teams message sent: {alert.alert_id}")
                    else:
                        self.logger.warning(f"Teams API returned {response.status}")
                    return success

        except Exception as e:
            self.logger.error(f"Failed to send Teams message: {e}")
            return False

    def _get_color_by_level(self, level: str) -> str:
        """
        9n+֜r
        Get Color by Level

        Args:
            level: Jf+ / Alert level

        Returns:
            str: rAm6	 / Hex color code
        """
        colors = {
            "info": "00FF00",  # r
            "warning": "FF9500",  # Yr
            "error": "FF0000",  # r
            "critical": "8B0000",  # r
        }

        # MnIr(Mnr
        if self.theme_color:
            return self.theme_color

        return colors.get(level, "808080")  # ؤpr

    async def send_batch(self, alerts: list[Alert]) -> dict[str, bool]:
        """
        yTeamso
        Send Batch Teams Messages

        Args:
            alerts: Jfh / List of alerts

        Returns:
            Dict[str, bool]: Ӝ / Send results
        """
        if not self.is_enabled():
            return {alert.alert_id: False for alert in alerts}

        # Teams/(*o-+*sections



        try:
            payload = {
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "themeColor": "FF9500",  # Yr\:yJfr
                "summary": f"{self.title_prefix}: Batch Alert ({len(alerts)} alerts)",
                "sections": [],
            }

            for alert in alerts:
                section = {
                    "activityTitle": f"[{alert.level.value.upper()}] {alert.title}",
                    "activitySubtitle": f"Alert ID: {alert.alert_id}",
                    "facts": [
                        {"name": "Message", "value": alert.message},
                        {"name": "Source", "value": alert.source},
                        {"name": "Severity", "value": alert.severity.value},
                        {
                            "name": "Created At",
                            "value": alert.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
                        },
                    ],
                    "markdown": True,
                }
                payload["sections"].append(section)

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url, json=payload, timeout=10
                ) as response:
                    success = response.status == 200
                    return {alert.alert_id: success for alert in alerts}

        except Exception as e:
            self.logger.error(f"Failed to send batch Teams message: {e}")
            return {alert.alert_id: False for alert in alerts}