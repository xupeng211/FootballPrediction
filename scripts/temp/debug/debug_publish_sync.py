#!/usr/bin/env python3
"""Debug script for publish_sync method"""

import asyncio
from src.events.bus import EventBus, Event
from unittest.mock import MagicMock


def debug_publish_sync():
    bus = EventBus()
    handler = MagicMock()
    handler.handle = MagicMock(return_value=None)
    handler.name = "mock_handler"

    print(f"Handler has handle: {hasattr(handler, 'handle')}")
    print(f"Handler handle is coroutine: {asyncio.iscoroutinefunction(handler.handle)}")
    print(f"Handler has name: {hasattr(handler, 'name')}")
    print(f"Handler name: {getattr(handler, 'name', 'NO_NAME')}")

    bus.subscribe_sync("TestEvent", handler)
    print(f"Subscribers: {bus._subscribers}")

    event = Event("TestEvent", {"test": True})
    print(f"About to call publish_sync")
    bus.publish_sync("TestEvent", event)
    print(f"publish_sync completed")
    print(f"Handler handle called: {handler.handle.called}")
    if handler.handle.called:
        print(f"Call args: {handler.handle.call_args}")


if __name__ == "__main__":
    debug_publish_sync()
