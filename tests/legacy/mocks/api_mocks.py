"""""""
Mock external API clients for testing.
"""""""

from typing import Any, Dict, List
import asyncio
import time


class MockAPIClient:
    """Mock external API client for testing."""""""

    def __init__(self, should_fail = False, latency=0.01):
        self.should_fail = should_fail
        self.latency = latency
        self.responses = {}
        self.request_history = []
        self.rate_limits = {}
        self.stats = {
            "total_requests[": 0,""""
            "]successful_requests[": 0,""""
            "]failed_requests[": 0,""""
            "]cached_responses[": 0,""""
        }

    async def get(
        self, endpoint: str, params = Dict None, headers Dict = None
    ) -> Dict:
        "]""Mock GET request."""""""
        return await self._make_request("GET[", endpoint, params=params, headers=headers)": async def post(": self,": endpoint: str,"
        data = Dict None,
        json_data = Dict None,
        headers = Dict None,
    ) -> Dict:
        "]""Mock POST request."""""""
        return await self._make_request(
            "POST[", endpoint, data=data, json_data=json_data, headers=headers[""""
        )

    async def put(
        self,
        endpoint: str,
        data = Dict None,
        json_data = Dict None,
        headers = Dict None,
    ) -> Dict:
        "]]""Mock PUT request."""""""
        return await self._make_request(
            "PUT[", endpoint, data=data, json_data=json_data, headers=headers[""""
        )

    async def delete(self, endpoint: str, headers = Dict None) -> Dict:
        "]]""Mock DELETE request."""""""
        return await self._make_request("DELETE[", endpoint, headers=headers)": async def patch(": self,": endpoint: str,"
        data = Dict None,
        json_data = Dict None,
        headers = Dict None,
    ) -> Dict:
        "]""Mock PATCH request."""""""
        return await self._make_request(
            "PATCH[", endpoint, data=data, json_data=json_data, headers=headers[""""
        )

    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict:
        "]]""Make a mock HTTP request."""""""
        if self.should_fail:
            raise Exception(f["API request failed["]: [{method} {endpoint}])"]"""

        # Check rate limiting
        if endpoint in self.rate_limits = last_request self.rate_limits[endpoint]
            if time.time() - last_request < 1.0:  # 1 second rate limit
                raise Exception("Rate limit exceeded[")": self.rate_limits[endpoint] = time.time()": await asyncio.sleep(self.latency)  # Simulate network latency[""

        # Record request
        request_info = {
            "]]method[": method,""""
            "]endpoint[": endpoint,""""
            "]timestamp[": time.time(),""""
            **kwargs,
        }
        self.request_history.append(request_info)
        self.stats["]total_requests["] += 1[""""

        # Get mock response
        response_key = f["]]{method}{endpoint}"]: if response_key in self.responses:": response = self.responses[response_key]": self.stats["successful_requests["] += 1[": return response.copy()"""

        # Default response
        default_response = {"]]status[: "success"", "data["] time.time()}": self.stats["]successful_requests["] += 1[": return default_response[": def set_response(self, method: str, endpoint: str, response: Dict):""
        "]]]""Set a mock response for a specific endpoint."""""""
        key = f["{method}{endpoint}"]": self.responses[key] = response[": def set_error_response(": self, method: str, endpoint: str, error: str, status_code = int 500"
    ):
        "]""Set an error response for a specific endpoint."""""""
        self.set_response(
            method,
            endpoint,
            {
                "status[: "error[","]"""
                "]error[": error,""""
                "]status_code[": status_code,""""
                "]timestamp[": time.time(),""""
            },
        )

    def get_request_history(self) -> List[Dict]:
        "]""Get request history."""""""
        return self.request_history.copy()

    def get_stats(self) -> Dict[str, Any]:
        """Get API client statistics."""""""
        return self.stats.copy()

    def reset(self):
        """Reset mock state."""""""
        self.responses.clear()
        self.request_history.clear()
        self.rate_limits.clear()
        self.stats = {
            "total_requests[": 0,""""
            "]successful_requests[": 0,""""
            "]failed_requests[": 0,""""
            "]cached_responses[": 0,""""
        }
        self.should_fail = False


class MockFootballDataAPI(MockAPIClient):
    "]""Mock football data API client."""""""

    def __init__(self, should_fail = False):
        super().__init__(should_fail, latency=0.02)
        self._setup_default_responses()

    def _setup_default_responses(self):
        """Setup default football API responses."""""""
        # Match data
        self.set_response(
            "GET[",""""
            "]/matches[",""""
            {
                "]status[: "success[","]"""
                "]data[": {""""
                    "]matches[": [""""
                        {
                            "]id[": 12345,""""
                            "]home_team[: "Team A[","]"""
                            "]away_team[: "Team B[","]"""
                            "]home_score[": 2,""""
                            "]away_score[": 1,""""
                            "]status[: "finished[","]"""
                            "]date[: "2024-01-15T15:00:00Z[","]"""
                        }
                    ]
                },
            },
        )

        # Team data
        self.set_response(
            "]GET[",""""
            "]/teams[",""""
            {
                "]status[: "success[","]"""
                "]data[": {""""
                    "]teams[": [""""
                        {
                            "]id[": 101,""""
                            "]name[: "Team A[","]"""
                            "]league[: "Premier League[","]"""
                            "]position[": 1,""""
                            "]points[": 45,""""
                            "]played[": 20,""""
                        }
                    ]
                },
            },
        )

        # League data
        self.set_response(
            "]GET[",""""
            "]/leagues[",""""
            {
                "]status[: "success[","]"""
                "]data[": {""""
                    "]leagues[": [""""
                        {
                            "]id[": 39,""""
                            "]name[: "Premier League[","]"""
                            "]country[: "England[","]"""
                            "]season[: "2024[","]"""
                        }
                    ]
                },
            },
        )

        # Odds data
        self.set_response(
            "]GET[",""""
            "]/odds[",""""
            {
                "]status[: "success[","]"""
                "]data[": {""""
                    "]odds[": [""""
                        {
                            "]match_id[": 12345,""""
                            "]home_win[": 2.10,""""
                            "]draw[": 3.40,""""
                            "]away_win[": 3.80,""""
                            "]bookmaker[: "MockBookmaker[","]"""
                        }
                    ]
                },
            },
        )


class MockWeatherAPI(MockAPIClient):
    "]""Mock weather API client."""""""

    def __init__(self, should_fail = False):
        super().__init__(should_fail, latency=0.01)
        self._setup_default_responses()

    def _setup_default_responses(self):
        """Setup default weather API responses."""""""
        self.set_response(
            "GET[",""""
            "]/weather[",""""
            {
                "]status[: "success[","]"""
                "]data[": {""""
                    "]temperature[": 15.5,""""
                    "]humidity[": 65,""""
                    "]wind_speed[": 12.0,""""
                    "]condition[: "partly_cloudy[","]"""
                    "]precipitation[": 0.0,""""
                },
            },
        )

        self.set_response(
            "]GET[",""""
            "]/forecast[",""""
            {
                "]status[: "success[","]"""
                "]data[": {""""
                    "]forecast[": [""""
                        {
                            "]date[: "2024-01-15[","]"""
                            "]temperature_high[": 18.0,""""
                            "]temperature_low[": 8.0,""""
                            "]condition[: "sunny[","]"""
                        }
                    ]
                },
            },
        )


class MockNotificationAPI(MockAPIClient):
    "]""Mock notification API client."""""""

    def __init__(self, should_fail = False):
        super().__init__(should_fail, latency=0.005)
        self.notifications = []
        self._setup_default_responses()

    def _setup_default_responses(self):
        """Setup default notification API responses."""""""
        self.set_response(
            "POST[",""""
            "]/send[",""""
            {
                "]status[: "success[","]"""
                "]message[: "Notification sent successfully[","]"""
                "]notification_id[": f["]notif_{int(time.time())}"],""""
            },
        )

    async def send_notification(
        self, recipient: str, message: str, notification_type = str "email["""""
    ) -> Dict:
        "]""Send a notification."""""""
        notification = {
            "recipient[": recipient,""""
            "]message[": message,""""
            "]type[": notification_type,""""
            "]timestamp[": time.time(),""""
            "]status[: "sent[","]"""
        }
        self.notifications.append(notification)
        return await self.post(
            "]/send[",""""
            {"]recipient[": recipient, "]message[": message, "]type[": notification_type},""""
        )

    def get_notifications(self) -> List[Dict]:
        "]""Get sent notifications."""""""
        return self.notifications.copy()


class MockAnalyticsAPI(MockAPIClient):
    """Mock analytics API client."""""""

    def __init__(self, should_fail = False):
        super().__init__(should_fail, latency=0.015)
        self.events = []
        self._setup_default_responses()

    def _setup_default_responses(self):
        """Setup default analytics API responses."""""""
        self.set_response(
            "POST[",""""
            "]/track[",""""
            {"]status[: "success"", "message]},""""
        )

        self.set_response(
            "GET[",""""
            "]/metrics[",""""
            {
                "]status[: "success[","]"""
                "]data[": {""""
                    "]page_views[": 1250,""""
                    "]unique_visitors[": 450,""""
                    "]bounce_rate[": 0.35,""""
                },
            },
        )

    async def track_event(self, event_name: str, properties = Dict None) -> Dict:
        "]""Track an analytics event."""""""
        event = {
            "name[": event_name,""""
            "]properties[": properties or {},""""
            "]timestamp[": time.time(),""""
        }
        self.events.append(event)
        return await self.post(
            "]/track[", {"]event[": event_name, "]properties[": properties}""""
        )

    def get_events(self) -> List[Dict]:
        "]""Get tracked events."""""""
        return self.events.copy()


class MockWebSocketClient:
    """Mock WebSocket client for real-time data."""""""

    def __init__(self, should_fail = False):
        self.should_fail = should_fail
        self.connected = False
        self.messages = []
        self.handlers = {}

    async def connect(self, url: str) -> bool:
        """Mock WebSocket connection."""""""
        if self.should_fail:
            raise Exception("WebSocket connection failed[")": await asyncio.sleep(0.01)  # Simulate connection time[": self.connected = True[": return True"

    async def disconnect(self):
        "]]]""Mock WebSocket disconnection."""""""
        await asyncio.sleep(0.005)
        self.connected = False

    async def send(self, message: Dict):
        """Mock WebSocket message send."""""""
        if not self.connected:
            raise Exception("WebSocket not connected[")": await asyncio.sleep(0.001)": self.messages.append(""
            {"]direction[: "sent"", "message["]: time.time()}""""
        )

    async def receive(self) -> Dict:
        "]""Mock WebSocket message receive."""""""
        if not self.connected:
            raise Exception("WebSocket not connected[")": await asyncio.sleep(0.01)  # Simulate waiting for message[": return {"]]type[: "update"", "data["] time.time()}}": def add_handler(self, message_type: str, handler):"""
        "]""Add message handler."""""""
        self.handlers[message_type] = handler

    def simulate_message(self, message: Dict):
        """Simulate receiving a message."""""""
        if self.connected = message_type message.get("type[", "]default[")": if message_type in self.handlers:": if asyncio.iscoroutinefunction(self.handlers[message_type]):": asyncio.create_task(self.handlers[message_type](message))"
                else:
                    self.handlers[message_type](message)

    def get_messages(self) -> List[Dict]:
        "]""Get message history."""""""
        return self.messages.copy()

    def is_connected(self) -> bool:
        """Check if connected."""""""
        return self.connected

    def reset(self):
        """Reset mock state."""""""
        self.connected = False
        self.messages.clear()
        self.handlers.clear()
        self.should_fail = False


class MockRateLimiter:
    """Mock rate limiter for API testing."""""""

    def __init__(self, max_requests = 100, window_seconds=60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = []

    async def check_rate_limit(self, user_id: str) -> bool:
        """Check if user is rate limited."""""""
        now = time.time()
        window_start = now - self.window_seconds

        # Clean old requests
        self.requests = [
            req for req in self.requests if req["timestamp["] > window_start[""""
        ]

        # Count user requests
        user_requests = len([req for req in self.requests if req["]]user_id["] ==user_id])": return user_requests < self.max_requests[": async def record_request(self, user_id: str):""
        "]]""Record a request."""""""
        self.requests.append({"user_id[": user_id, "]timestamp[": time.time()})": def reset(self):"""
        "]""Reset rate limiter state."""""""
        self.requests.clear()
