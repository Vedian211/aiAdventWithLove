#!/usr/bin/env python3
"""Test script for Agent with session persistence"""

import os
from src.aiadvent.agent.agent import Agent

# Mock API key for testing (we won't make actual API calls)
os.environ["OPENAI_API_KEY"] = "test-key"

print("Step 2 Test: Agent Session Management\n")

# 1. Create agent
print("1. Creating agent...")
agent = Agent(
    api_key="test-key",
    model="gpt-4.1-nano",
    system_prompt="You are a helpful assistant."
)
print("✓ Agent created\n")

# 2. Create a new session
print("2. Creating new session...")
session_id = agent.create_session("Test Session from Agent")
print(f"✓ Session created with ID: {session_id}\n")

# 3. Manually add messages and save them
print("3. Adding messages to agent and saving to DB...")
agent.add_message("user", "What is Python?")
agent.save_message_to_db("user", "What is Python?")

agent.add_message("assistant", "Python is a programming language.")
agent.save_message_to_db("assistant", "Python is a programming language.")

print(f"✓ Messages in memory: {len(agent.messages)}")
print(f"  (including system prompt)\n")

# 4. List sessions
print("4. Listing all sessions...")
sessions = agent.list_sessions()
for session in sessions:
    print(f"  - ID: {session['id']}, Name: {session['name']}")
print()

# 5. Create a new agent and load the session
print("5. Creating new agent and loading session...")
agent2 = Agent(
    api_key="test-key",
    model="gpt-4.1-nano",
    system_prompt="Different prompt"
)
success = agent2.load_session(session_id)
print(f"✓ Session loaded: {success}")
print(f"  Model: {agent2.model}")
print(f"  System prompt: {agent2.system_prompt}")
print(f"  Messages restored: {len(agent2.messages)}")
for msg in agent2.messages:
    role = msg["role"]
    content = msg["content"][:50]
    print(f"    - {role}: {content}...")
print()

print("✅ Step 2 complete! Agent can save and load sessions.")
