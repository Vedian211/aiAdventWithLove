#!/usr/bin/env python3
"""Test script for HistoryManager"""

from src.aiadvent.agent.history import HistoryManager

# Initialize manager
print("1. Initializing HistoryManager...")
manager = HistoryManager()
print("✓ Database initialized\n")

# Create a test session
print("2. Creating test session...")
session_id = manager.create_session(
    name="Test Chat",
    model="gpt-4.1-nano",
    system_prompt="You are a helpful assistant."
)
print(f"✓ Session created with ID: {session_id}\n")

# Save some messages
print("3. Saving messages...")
manager.save_message(session_id, "user", "Hello, how are you?")
manager.save_message(session_id, "assistant", "I'm doing well, thank you!")
manager.save_message(session_id, "user", "What's the weather like?")
print("✓ Messages saved\n")

# List sessions
print("4. Listing all sessions...")
sessions = manager.list_sessions()
for session in sessions:
    print(f"  - ID: {session['id']}, Name: {session['name']}, Model: {session['model']}")
print()

# Load session
print("5. Loading session...")
loaded = manager.load_session(session_id)
print(f"✓ Loaded session: {loaded['name']}")
print(f"  Model: {loaded['model']}")
print(f"  System prompt: {loaded['system_prompt']}")
print(f"  Messages: {len(loaded['messages'])}")
for msg in loaded['messages']:
    print(f"    - {msg['role']}: {msg['content'][:50]}...")
print()

print("✅ All tests passed!")
print(f"\nDatabase location: {manager.db_path}")
