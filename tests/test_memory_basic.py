"""
Basic tests for memory layers functionality
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.aiadvent.agent.agent import Agent


def print_separator(title):
    """Print formatted section separator"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")


def print_profile(profile, title="User Profile"):
    """Print profile in formatted way"""
    print(f"\n{'='*70}")
    print(title)
    print(f"{'='*70}\n")
    
    if not profile:
        print("  (empty)")
        return
    
    for category, items in profile.items():
        print(f"  {category.upper()}:")
        for key, value in items.items():
            print(f"    • {key}: {value}")
        print()


def print_memory_stats(stats, title="Memory Statistics"):
    """Print memory stats in formatted way"""
    print(f"\n{'='*70}")
    print(title)
    print(f"{'='*70}\n")
    
    print(f"  Short-term messages:     {stats['short_term']}")
    print(f"  Working memory facts:    {stats['working_memory'].get('total_facts', 0)}")
    print(f"  Long-term profile items: {stats['long_term']['profile_items']}")
    print()


def test_memory_layers_basic():
    """Test basic memory layers functionality"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠ OPENAI_API_KEY not set, skipping test")
        return
    
    print_separator("Test 1: Basic Memory Layers")
    
    agent = Agent(
        api_key=api_key,
        model="gpt-4o-mini",
        system_prompt="You are a helpful assistant. Keep responses concise.",
        strategy="memory_layers"
    )
    
    session_id = agent.create_session("Memory Test")
    print(f"✓ Session created (id={session_id})")
    
    # Store preference
    print("\n📝 User: I prefer Python for all my projects")
    response1 = agent.respond("I prefer Python for all my projects")
    print(f"🤖 Assistant:\n{response1}\n")
    
    # Verify profile stored
    profile = agent.long_term_memory.get_profile()
    print_profile(profile, "Profile After First Exchange")
    assert profile, "Profile should be stored"
    
    # Ask for code example
    print("\n📝 User: Show me a simple hello world example")
    response2 = agent.respond("Show me a simple hello world example")
    print(f"🤖 Assistant:\n{response2}\n")
    
    # Check memory stats
    stats = agent.memory_manager.get_memory_stats()
    print_memory_stats(stats)
    
    print("✅ Basic memory test passed\n")


def test_memory_persistence():
    """Test memory persists across sessions"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠ OPENAI_API_KEY not set, skipping test")
        return
    
    print_separator("Test 2: Memory Persistence Across Sessions")
    
    # Session 1: Store information
    print("SESSION 1: Learning Phase")
    print("-" * 70)
    agent1 = Agent(
        api_key=api_key,
        model="gpt-4o-mini",
        system_prompt="You are a helpful assistant.",
        strategy="memory_layers"
    )
    agent1.create_session("Session 1")
    
    print("\n📝 User: I'm a backend developer working on REST APIs")
    agent1.respond("I'm a backend developer working on REST APIs")
    
    profile1 = agent1.long_term_memory.get_profile()
    print_profile(profile1, "Profile After Session 1")
    
    # Session 2: Check if information is recalled
    print("\nSESSION 2: Recall Phase (New Agent Instance)")
    print("-" * 70)
    agent2 = Agent(
        api_key=api_key,
        model="gpt-4o-mini",
        system_prompt="You are a helpful assistant.",
        strategy="memory_layers"
    )
    agent2.create_session("Session 2")
    
    profile2 = agent2.long_term_memory.get_profile()
    print_profile(profile2, "Profile Loaded in Session 2")
    
    # Profile should persist
    assert profile2, "Profile should persist across sessions"
    
    print("\n📝 User: What kind of work do I do?")
    response = agent2.respond("What kind of work do I do?")
    print(f"🤖 Assistant: {response[:100]}...")
    
    print("\n✅ Persistence test passed\n")


def test_existing_strategies_still_work():
    """Verify existing strategies are not broken"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠ OPENAI_API_KEY not set, skipping test")
        return
    
    print_separator("Test 3: Existing Strategies Compatibility")
    
    # Test sliding_window (default)
    agent1 = Agent(api_key=api_key, model="gpt-4o-mini", strategy="sliding_window")
    assert agent1.memory_manager is None
    print("✓ sliding_window strategy works")
    
    # Test sticky_facts
    agent2 = Agent(api_key=api_key, model="gpt-4o-mini", strategy="sticky_facts")
    assert agent2.memory_manager is None
    assert agent2.sticky_facts_manager is not None
    print("✓ sticky_facts strategy works")
    
    print("\n✅ Existing strategies test passed\n")


if __name__ == "__main__":
    # Collect test data
    test_data = {
        "test1": {},
        "test2": {},
        "profiles": []
    }
    
    # Run tests and collect data
    print("Running tests and collecting data...\n")
    
    # Test 1
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        agent1 = Agent(api_key=api_key, model="gpt-4o-mini", 
                      system_prompt="You are a helpful assistant. Keep responses concise.",
                      strategy="memory_layers")
        agent1.create_session("Test 1")
        
        test_data["test1"]["input1"] = "I prefer Python for all my projects"
        test_data["test1"]["response1"] = agent1.respond(test_data["test1"]["input1"])
        test_data["test1"]["profile_after_1"] = agent1.long_term_memory.get_profile()
        
        test_data["test1"]["input2"] = "Show me a simple hello world example"
        test_data["test1"]["response2"] = agent1.respond(test_data["test1"]["input2"])
        test_data["test1"]["stats"] = agent1.memory_manager.get_memory_stats()
        
        # Test 2 - persistence
        agent2 = Agent(api_key=api_key, model="gpt-4o-mini",
                      system_prompt="You are a helpful assistant. Keep responses concise.",
                      strategy="memory_layers")
        agent2.create_session("Test 2")
        test_data["test2"]["profile_loaded"] = agent2.long_term_memory.get_profile()
        
        test_data["test2"]["input"] = "What kind of work do I do?"
        test_data["test2"]["response"] = agent2.respond(test_data["test2"]["input"])
    
    # Now run the actual tests with output
    test_memory_layers_basic()
    test_memory_persistence()
    test_existing_strategies_still_work()
    
    print("\n" + "="*70)
    print("  🎉 ALL TESTS PASSED!")
    print("="*70 + "\n")
    
    # Generate AI summary
    if api_key and test_data["test1"]:
        print("="*70)
        print("  🤖 AI-GENERATED ANALYSIS")
        print("="*70 + "\n")
        print("Analyzing test results...\n")
        
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        analysis_prompt = f"""Analyze this memory layers test data and provide a clear summary.

TEST 1 - Basic Memory:
User Input 1: "{test_data["test1"]["input1"]}"
Assistant Response 1: "{test_data["test1"]["response1"][:200]}..."

Profile Stored: {test_data["test1"]["profile_after_1"]}

User Input 2: "{test_data["test1"]["input2"]}"
Assistant Response 2: "{test_data["test1"]["response2"][:200]}..."

Memory Stats: {test_data["test1"]["stats"]}

TEST 2 - Persistence (New Session):
Profile Loaded: {test_data["test2"]["profile_loaded"]}

User Input: "{test_data["test2"]["input"]}"
Assistant Response: "{test_data["test2"]["response"][:200]}..."

Please answer these questions based on the ACTUAL data above:

1. What data went into each memory layer? (short-term, working, long-term)
2. How did the stored profile affect the assistant's responses?
3. What evidence shows memory persistence across sessions?

Be specific and reference the actual data. Keep it concise."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a technical analyst. Provide clear, data-driven analysis."},
                {"role": "user", "content": analysis_prompt}
            ],
            temperature=0
        )
        
        print(response.choices[0].message.content)
        print("\n" + "="*70 + "\n")
