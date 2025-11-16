#!/usr/bin/env python3
"""
Test script to verify all bot dependencies can be imported
"""

print("Testing bot dependencies...")

try:
    import socket
    print("✓ socket")
except ImportError as e:
    print(f"✗ socket: {e}")

try:
    import time
    print("✓ time")
except ImportError as e:
    print(f"✗ time: {e}")

try:
    import threading
    print("✓ threading")
except ImportError as e:
    print(f"✗ threading: {e}")

try:
    import json
    print("✓ json")
except ImportError as e:
    print(f"✗ json: {e}")

try:
    import os
    print("✓ os")
except ImportError as e:
    print(f"✗ os: {e}")

try:
    import logging
    print("✓ logging")
except ImportError as e:
    print(f"✗ logging: {e}")

try:
    import pickle
    print("✓ pickle")
except ImportError as e:
    print(f"✗ pickle: {e}")

try:
    from datetime import datetime
    print("✓ datetime")
except ImportError as e:
    print(f"✗ datetime: {e}")

try:
    import pytz
    print("✓ pytz")
except ImportError as e:
    print(f"✗ pytz: {e}")

try:
    from zoneinfo import ZoneInfo
    print("✓ zoneinfo (Python 3.9+)")
except ImportError:
    print("⚠ zoneinfo (not available - using pytz fallback)")

try:
    import base64
    print("✓ base64")
except ImportError as e:
    print(f"✗ base64: {e}")

try:
    from collections import defaultdict
    print("✓ collections.defaultdict")
except ImportError as e:
    print(f"✗ collections.defaultdict: {e}")

try:
    from midi_player import MidiManager
    print("✓ midi_player")
except ImportError as e:
    print(f"✗ midi_player: {e}")

try:
    from web_server import WebServer
    print("✓ web_server")
except ImportError as e:
    print(f"✗ web_server: {e}")

try:
    from ircbot import IRCBot
    print("✓ ircbot")
except ImportError as e:
    print(f"✗ ircbot: {e}")

print("\nAll tests complete!")
print("If you see any ✗ marks above, those dependencies need to be installed.")
