"""
Jf S
SMS Alert Channel

APIJf
Sends alerts via SMS API.
"""

from typing import Any, Dict

import aiohttp

from .base_channel import BaseAlertChannel
from ...alert_manager_mod.models import Alert


class SMSChannel(BaseAlertChannel):
    """
    Jf S
    SMS Alert Channel

    APIJf
    Sends alerts via SMS API.
    """

    def __init__(self, name: str = "sms", config: Dict[str, Any] | None = None):
        """
         S
        Initialize SMS Channel

        Args:
            name:  S / Channel name
            config:  SMn / Channel configuration
        """
        super().__init__(name, config)
        self.api_url = self.config.get("api_url")
        self.api_key = self.config.get("api_key")
        self.api_secret = self.config.get("api_secret")
        self.phone_numbers = self.config.get("phone_numbers", [])
        self.max_message_length = self.config.get("max_message_length", 160)
        self.template = self.config.get("template", "[{level}] {title}: {message}")
        self.provider = self.config.get("provider", "generic")  # /ЛF

        if not all([self.api_url, self.api_key]) or not self.phone_numbers:
            self.logger.warning("SMS channel not properly configured")
            self.enabled = False

    async def send(self, alert: Alert) -> bool:
        """
        Jf
        Send SMS Alert

        Args:
            alert: Jfa / Alert object

        Returns:
            bool: /& / Whether sent successfully
        """
        if not self.is_enabled():
            return False

        try:
            # <ᅹ
            message = self._format_message(alert)

            # *K:
            success_count = 0
            for phone_number in self.phone_numbers:
                if await self._send_sms(phone_number, message):
                    success_count += 1

            # 	*1
            success = success_count > 0
            if success:
                self.logger.info(f"SMS sent successfully to {success_count}/{len(self.phone_numbers)} numbers: {alert.alert_id}")
            else:
                self.logger.error(f"Failed to send SMS to any number: {alert.alert_id}")

            return success

        except Exception as e:
            self.logger.error(f"Failed to send SMS: {e}")
            return False

    def _format_message(self, alert: Alert) -> str:
        """
        <ᅹ
        Format SMS Message

        Args:
            alert: Jfa / Alert object

        Returns:
            str: <ᅹ / Formatted SMS message
        """
        # (!<o
        message = self.template.format(
            level=alert.level.value.upper(),
            title=alert.title,
            message=alert.message,
            source=alert.source,
            alert_id=alert.alert_id
        )

        # P6
        if len(message) > self.max_message_length:
            # *oÝo
            truncated = message[:self.max_message_length-3] + "..."
            message = truncated

        return message

    async def _send_sms(self, phone_number: str, message: str) -> bool:
        """
        0
        Send SMS to specific phone number

        Args:
            phone_number: K: / Phone number
            message: ᅹ / SMS message

        Returns:
            bool: /& / Whether sent successfully
        """
        try:
            # 9nЛFB
            if self.provider.lower() == "aliyun":
                return await self._send_aliyun_sms(phone_number, message)
            elif self.provider.lower() == "tencent":
                return await self._send_tencent_sms(phone_number, message)
            else:
                return await self._send_generic_sms(phone_number, message)

        except Exception as e:
            self.logger.error(f"Failed to send SMS to {phone_number}: {e}")
            return False

    async def _send_generic_sms(self, phone_number: str, message: str) -> bool:
        """
        (API
        Generic SMS API Send

        Args:
            phone_number: K: / Phone number
            message: ᅹ / SMS message

        Returns:
            bool: /& / Whether sent successfully
        """
        payload = {
            "api_key": self.api_key,
            "phone": phone_number,
            "message": message
        }

        if self.api_secret:
            payload["api_secret"] = self.api_secret

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.api_url,
                json=payload,
                timeout=10
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("success", False)
                else:
                    self.logger.warning(f"SMS API returned {response.status}")
                    return False

    async def _send_aliyun_sms(self, phone_number: str, message: str) -> bool:
        """
        ?̑
        Aliyun SMS Send

        Args:
            phone_number: K: / Phone number
            message: ᅹ / SMS message

        Returns:
            bool: /& / Whether sent successfully
        """
        # ?̑APIH
        import hashlib
        import hmac
        import base64
        from urllib.parse import quote

        # ?̑APIBp
        params = {
            "PhoneNumbers": phone_number,
            "SignName": self.config.get("sign_name", "Jf"),
            "TemplateCode": self.config.get("template_code"),
            "TemplateParam": f'{{"message":"{message}"}}',
            "AccessKeyId": self.api_key,
            "Format": "JSON",
            "Version": "2017-05-25",
            "Action": "SendSms",
            "SignatureMethod": "HMAC-SHA1",
            "Timestamp": self._get_iso_timestamp(),
            "SignatureVersion": "1.0",
            "SignatureNonce": self._generate_nonce(),
        }

        # ~
        signature = self._calculate_signature(params, self.api_secret)
        params["Signature"] = signature

        async with aiohttp.ClientSession() as session:
            async with session.get(
                self.api_url,
                params=params,
                timeout=10
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("Code") == "OK"
                else:
                    self.logger.warning(f"Aliyun SMS API returned {response.status}")
                    return False

    async def _send_tencent_sms(self, phone_number: str, message: str) -> bool:
        """
        ~
        Tencent SMS Send

        Args:
            phone_number: K: / Phone number
            message: ᅹ / SMS message

        Returns:
            bool: /& / Whether sent successfully
        """
        # ~APIH
        payload = {
            "PhoneNumberSet": [phone_number],
            "TemplateID": self.config.get("template_id"),
            "TemplateParamSet": [message],
            "SdkAppId": self.config.get("sdk_app_id"),
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=10
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("Response", {}).get("SendStatusSet", [{}])[0].get("Code") == "Ok"
                else:
                    self.logger.warning(f"Tencent SMS API returned {response.status}")
                    return False

    def _calculate_signature(self, params: Dict[str, str], secret: str) -> str:
        """
        ?̑API~
        Calculate Aliyun API Signature

        Args:
            params: Bp / Request parameters
            secret: ƥ / Secret key

        Returns:
            str: ~ / Signature
        """
        # 	Wzp
        sorted_params = sorted(params.items())
        query_string = "&".join([f"{quote(k)}={quote(v)}" for k, v in sorted_params])

        # HMAC-SHA1~
        string_to_sign = f"POST&%2F&{quote(query_string)}"
        signature = base64.b64encode(
            hmac.new(secret.encode(), string_to_sign.encode(), hashlib.sha1).digest()
        ).decode()

        return signature

    def _get_iso_timestamp(self) -> str:
        """ISO<3"""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    def _generate_nonce(self) -> str:
        """:nonce"""
        import secrets
        return secrets.token_hex(16)
