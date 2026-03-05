"""
Test scenarios for user personalization feature
"""
import os
from aiadvent.agent.agent import Agent
from aiadvent.agent.user_profile import UserProfile
from rich.console import Console
from rich.markdown import Markdown
from rich.spinner import Spinner
from rich.live import Live


def test_formal_vs_casual():
    """Test Case 1: Formal vs Casual profiles"""
    console = Console()
    console.print("\n## Test 1: Formal vs Casual\n", style="bold cyan")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not set")
        return
    
    # Create agent
    agent = Agent(api_key=api_key, model="gpt-4o-mini")
    agent.create_session("Test Formal vs Casual")
    
    # Create formal profile
    formal_profile = UserProfile(agent.client, agent.model, agent.history_manager)
    formal_profile.name = "Formal User"
    formal_profile.communication_style = "formal"
    formal_profile.response_format = "detailed"
    formal_profile.constraints = ["no_emoji"]
    formal_profile_id = formal_profile.save_profile()
    
    # Create casual profile
    casual_profile = UserProfile(agent.client, agent.model, agent.history_manager)
    casual_profile.name = "Casual User"
    casual_profile.communication_style = "casual"
    casual_profile.response_format = "concise"
    casual_profile.preferences = {"emoji": True}
    casual_profile_id = casual_profile.save_profile()
    
    questions = [
        "What is Python?",
        "What are its main features?",
        "How does it compare to Java?",
        "What is it used for?",
        "Is it good for beginners?"
    ]
    
    # Test with formal profile
    console.print("\n### Formal Profile Response\n", style="bold yellow")
    agent.set_user_profile(formal_profile_id)
    
    for question in questions:
        console.print(f"**Q:** {question}\n", style="bold cyan")
        with console.status("[cyan]Thinking...", spinner="dots"):
            response = agent.think(question)
        console.print(Markdown(f"**A:** {response}"))
        console.print()
    
    # Clear and test with casual profile
    agent.clear_history()
    console.print("\n### Casual Profile Response\n", style="bold yellow")
    agent.set_user_profile(casual_profile_id)
    
    for question in questions:
        console.print(f"**Q:** {question}\n", style="bold cyan")
        with console.status("[cyan]Thinking...", spinner="dots"):
            response = agent.think(question)
        console.print(Markdown(f"**A:** {response}"))
        console.print()


def test_language_preference():
    """Test Case 2: Language preference"""
    console = Console()
    console.print("\n## Test 2: Language Preference\n", style="bold cyan")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not set")
        return
    
    agent = Agent(api_key=api_key, model="gpt-4o-mini")
    agent.create_session("Test Language")
    
    # Create Russian profile
    ru_profile = UserProfile(agent.client, agent.model, agent.history_manager)
    ru_profile.name = "Russian User"
    ru_profile.language = "ru"
    ru_profile_id = ru_profile.save_profile()
    
    agent.set_user_profile(ru_profile_id)
    
    questions = [
        "What is artificial intelligence?",
        "How does machine learning work?",
        "What are neural networks?",
        "Can you explain deep learning?",
        "What is the future of AI?"
    ]
    
    for question in questions:
        console.print(f"**Q:** {question}\n", style="bold cyan")
        with console.status("[cyan]Thinking...", spinner="dots"):
            response = agent.think(question)
        console.print(Markdown(f"**A (Russian):** {response}"))
        console.print()


def test_constraints():
    """Test Case 3: Constraints"""
    console = Console()
    console.print("\n## Test 3: Constraints\n", style="bold cyan")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not set")
        return
    
    agent = Agent(api_key=api_key, model="gpt-4o-mini")
    agent.create_session("Test Constraints")
    
    # Create constrained profile
    constrained_profile = UserProfile(agent.client, agent.model, agent.history_manager)
    constrained_profile.name = "Constrained User"
    constrained_profile.constraints = ["no_code_examples", "bullet_points_only"]
    constrained_profile_id = constrained_profile.save_profile()
    
    agent.set_user_profile(constrained_profile_id)
    
    questions = [
        "How do I create a list in Python?",
        "What is a function?",
        "How do loops work?",
        "What are variables?",
        "Explain object-oriented programming",
        "What is a class?"
    ]
    
    for question in questions:
        console.print(f"**Q:** {question}\n", style="bold cyan")
        with console.status("[cyan]Thinking...", spinner="dots"):
            response = agent.think(question)
        console.print(Markdown(f"**A (bullets, no code):** {response}"))
        console.print()


def test_profile_persistence():
    """Test Case 4: Profile persistence across sessions"""
    console = Console()
    console.print("\n## Test 4: Profile Persistence\n", style="bold cyan")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not set")
        return
    
    # Create first agent and profile
    agent1 = Agent(api_key=api_key, model="gpt-4o-mini")
    agent1.create_session("Test Persistence 1")
    
    profile = UserProfile(agent1.client, agent1.model, agent1.history_manager)
    profile.name = "Persistent User"
    profile.communication_style = "technical"
    profile_id = profile.save_profile()
    
    console.print(f"Created profile with ID: **{profile_id}**")
    
    # Create second agent and load profile
    agent2 = Agent(api_key=api_key, model="gpt-4o-mini")
    agent2.create_session("Test Persistence 2")
    
    if agent2.set_user_profile(profile_id):
        console.print(f"✓ Successfully loaded profile in new session", style="green")
        console.print(f"  - Profile name: **{agent2.user_profile.name}**")
        console.print(f"  - Style: **{agent2.user_profile.communication_style}**\n")
    else:
        console.print("✗ Failed to load profile\n", style="red")


def run_all_tests():
    """Run all test scenarios"""
    console = Console()
    console.print("\n" + "=" * 60, style="bold blue")
    console.print("# User Personalization Feature Tests", style="bold blue")
    console.print("=" * 60 + "\n", style="bold blue")
    
    try:
        test_formal_vs_casual()
        test_language_preference()
        test_constraints()
        test_profile_persistence()
        
        console.print("\n" + "=" * 60, style="bold green")
        console.print("✓ All tests completed!", style="bold green")
        console.print("=" * 60, style="bold green")
    except Exception as e:
        console.print(f"\n✗ Test failed with error: {e}", style="bold red")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()
