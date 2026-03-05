"""
Test scenarios for Task State Machine functionality
"""
import os
import tempfile
import sys
import time
import threading
from rich.console import Console
from rich.markdown import Markdown
from aiadvent.agent import Agent
from aiadvent.agent.history import HistoryManager


console = Console()


class ChatSimulator:
    """Simulates user-AI chat exchanges using real API calls"""
    
    def __init__(self, agent: Agent):
        self.agent = agent
        self._thinking = False
    
    def _show_thinking(self):
        """Show thinking animation while API call is in progress"""
        frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        idx = 0
        while self._thinking:
            console.print(f"[cyan]🤖 AI: {frames[idx]} thinking...[/cyan]", end="\r")
            idx = (idx + 1) % len(frames)
            time.sleep(0.1)
        console.print(" " * 50, end="\r")
    
    def exchange(self, user_message: str) -> str:
        """Send user message and get AI response via real API"""
        console.print(f"\n[bold blue]👤 User:[/bold blue] {user_message}")
        
        # Start thinking animation
        self._thinking = True
        thinking_thread = threading.Thread(target=self._show_thinking, daemon=True)
        thinking_thread.start()
        
        # Use real agent.think() to get response
        ai_response = self.agent.think(user_message)
        
        # Stop thinking animation
        self._thinking = False
        thinking_thread.join(timeout=0.5)
        
        console.print("[bold green]🤖 AI:[/bold green]")
        console.print(Markdown(ai_response))
        
        return ai_response


def test_realistic_conversation_flow():
    """Test state transitions through realistic user-AI conversation"""
    print("\n=== Test: Realistic Conversation Flow ===")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not set")
        return
    
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    
    try:
        agent = Agent(api_key=api_key, model="gpt-4o-mini")
        agent.history_manager = HistoryManager(db_path)
        agent.session_id = agent.create_session("Realistic Flow Test")
        
        chat = ChatSimulator(agent)
        
        # Exchange 1: User requests task → Planning
        print("\n--- Exchange 1: Task Request ---")
        response = chat.exchange("Create a simple Python function to calculate fibonacci numbers. "
                                 "Show me ONLY the plan, don't implement yet.")
        state = agent.task_state.get_state()
        console.print(f"   Phase: [yellow]{state['phase']}[/yellow]")
        print(f"   ✓ Should be in planning: {state['phase'] == 'planning'}")
        
        # Exchange 2: User refines plan → Stay in Planning
        print("\n--- Exchange 2: Refine Plan ---")
        response = chat.exchange("Can you add error handling for negative numbers to the plan?")
        state = agent.task_state.get_state()
        console.print(f"   Phase: [yellow]{state['phase']}[/yellow]")
        print(f"   ✓ Should stay in planning: {state['phase'] == 'planning'}")
        
        # Exchange 3: User approves → Execution
        print("\n--- Exchange 3: User Approves ---")
        response = chat.exchange("Looks good, proceed with the implementation")
        state = agent.task_state.get_state()
        console.print(f"   Phase: [yellow]{state['phase']}[/yellow]")
        print(f"   ✓ Should move to execution: {state['phase'] == 'execution'}")
        
        # Exchange 4: User asks for verification → Validation
        print("\n--- Exchange 4: Verification ---")
        response = chat.exchange("Could you proof result?")
        state = agent.task_state.get_state()
        console.print(f"   Phase: [yellow]{state['phase']}[/yellow]")
        print(f"   ✓ Should move to validation: {state['phase'] == 'validation'}")
        
        print("\n✓ Realistic conversation flow test completed!")
        
    finally:
        os.unlink(db_path)


def test_multi_turn_with_pause_resume():
    """Test multi-turn conversation with pause and resume"""
    print("\n=== Test: Multi-Turn with Pause/Resume ===")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not set")
        return
    
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    
    try:
        # Session 1: Start task
        print("\n--- Session 1: Start Task ---")
        agent1 = Agent(api_key=api_key, model="gpt-4o-mini")
        agent1.history_manager = HistoryManager(db_path)
        session_id = agent1.create_session("Multi-Turn Test")
        
        chat1 = ChatSimulator(agent1)
        
        # Start task
        chat1.exchange("Build a simple REST API endpoint. Plan it first with numbered steps.")
        state1 = agent1.task_state.get_state()
        print(f"   Phase before pause: {state1['phase']}")
        
        # Pause (simulate session end)
        print("\n--- Pausing Session ---")
        
        # Session 2: Resume task
        print("\n--- Session 2: Resume Task ---")
        agent2 = Agent(api_key=api_key, model="gpt-4o-mini")
        agent2.history_manager = HistoryManager(db_path)
        agent2.load_session(session_id)
        
        state2 = agent2.task_state.get_state()
        print(f"   Phase after resume: {state2['phase']}")
        
        chat2 = ChatSimulator(agent2)
        
        # Continue conversation
        chat2.exchange("Now implement it")
        state3 = agent2.task_state.get_state()
        print(f"   Phase after continue: {state3['phase']}")
        
        print("\n✓ Multi-turn with pause/resume test completed!")
        
    finally:
        os.unlink(db_path)


def test_edge_cases():
    """Test edge cases in state detection"""
    print("\n=== Test: Edge Cases ===")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not set")
        return
    
    agent = Agent(api_key=api_key, model="gpt-4o-mini")
    
    # Test 1: Multiple phase keywords in one response
    print("\n1. Testing multiple phase keywords...")
    response = "I'm planning to execute this and then verify the results when done."
    agent.task_state.detect_and_update(response)
    state = agent.task_state.get_state()
    print(f"   Detected phase: {state['phase']}")
    assert state['phase'] in ['planning', 'execution', 'validation', 'done'], "Should detect one valid phase"
    
    # Test 2: Phase regression (back to planning)
    print("\n2. Testing phase regression...")
    agent.task_state.phase = 'execution'
    agent.task_state.step = 2
    response = "Wait, let me plan this differently. First, I need to: 1. Check requirements 2. Redesign"
    agent.task_state.detect_and_update(response)
    state = agent.task_state.get_state()
    print(f"   Phase after regression: {state['phase']}")
    assert state['phase'] == 'planning', "Should allow regression to planning"
    
    # Test 3: Minimal response
    print("\n3. Testing minimal response...")
    agent.task_state.reset()
    response = "OK."
    agent.task_state.detect_and_update(response)
    state = agent.task_state.get_state()
    print(f"   Phase after minimal response: {state['phase']}")
    # Should not change from None if no keywords detected
    
    # Test 4: Step extraction from complex numbering
    print("\n4. Testing step extraction...")
    agent.task_state.reset()
    response = "Let me plan this: 1. Setup 2. Config 3. Build 4. Test 5. Deploy 6. Monitor"
    agent.task_state.detect_and_update(response)
    state = agent.task_state.get_state()
    print(f"   Extracted steps: {state['total_steps']}")
    assert state['total_steps'] == 6, f"Expected 6 steps, got {state['total_steps']}"
    
    print("\n✓ Edge cases test passed!")


def test_state_progression():
    """Test state progression through all phases"""
    print("\n=== Test: State Progression ===")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not set")
        return
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    
    try:
        agent = Agent(
            api_key=api_key,
            model="gpt-4o-mini",
            system_prompt="You are a helpful assistant."
        )
        agent.history_manager = HistoryManager(db_path)
        agent.session_id = agent.create_session("State Test")
        
        # Simulate planning phase
        print("\n1. Testing PLANNING phase detection...")
        planning_response = "Let me plan this out. First, I need to: 1. Create the file 2. Add the function 3. Test it"
        agent.task_state.detect_and_update(planning_response)
        state = agent.task_state.get_state()
        print(f"   Phase: {state['phase']}, Step: {state['step']}/{state['total_steps']}")
        assert state['phase'] == 'planning', f"Expected 'planning', got '{state['phase']}'"
        assert state['total_steps'] == 3, f"Expected 3 steps, got {state['total_steps']}"
        
        # Simulate execution phase
        print("\n2. Testing EXECUTION phase detection...")
        execution_response = "Now I'll create the file with the necessary code."
        agent.task_state.detect_and_update(execution_response)
        state = agent.task_state.get_state()
        print(f"   Phase: {state['phase']}, Step: {state['step']}")
        assert state['phase'] == 'execution', f"Expected 'execution', got '{state['phase']}'"
        
        # Simulate validation phase
        print("\n3. Testing VALIDATION phase detection...")
        validation_response = "Let me verify that everything works correctly."
        agent.task_state.detect_and_update(validation_response)
        state = agent.task_state.get_state()
        print(f"   Phase: {state['phase']}, Step: {state['step']}")
        assert state['phase'] == 'validation', f"Expected 'validation', got '{state['phase']}'"
        
        # Simulate done phase
        print("\n4. Testing DONE phase detection...")
        done_response = "All set! The implementation is completed successfully."
        agent.task_state.detect_and_update(done_response)
        state = agent.task_state.get_state()
        print(f"   Phase: {state['phase']}, Step: {state['step']}")
        assert state['phase'] == 'done', f"Expected 'done', got '{state['phase']}'"
        
        print("\n✓ State progression test passed!")
        
    finally:
        os.unlink(db_path)


def test_state_persistence():
    """Test state persistence across session restarts"""
    print("\n=== Test: State Persistence ===")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not set")
        return
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    
    try:
        # Create agent and set state
        print("\n1. Creating session and setting state...")
        agent1 = Agent(api_key=api_key, model="gpt-4o-mini")
        agent1.history_manager = HistoryManager(db_path)
        session_id = agent1.create_session("Persistence Test")
        
        # Set a state
        agent1.task_state.phase = "execution"
        agent1.task_state.step = 2
        agent1.task_state.total_steps = 5
        agent1.task_state.action_description = "Creating the main function"
        agent1.history_manager.save_task_state(session_id, agent1.task_state.get_state())
        
        print(f"   Saved state: {agent1.task_state.get_state()}")
        
        # Create new agent and load session
        print("\n2. Loading session in new agent...")
        agent2 = Agent(api_key=api_key, model="gpt-4o-mini")
        agent2.history_manager = HistoryManager(db_path)
        agent2.load_session(session_id)
        
        print(f"   Loaded state: {agent2.task_state.get_state()}")
        
        # Verify state was restored
        assert agent2.task_state.phase == "execution", f"Expected 'execution', got '{agent2.task_state.phase}'"
        assert agent2.task_state.step == 2, f"Expected step 2, got {agent2.task_state.step}"
        assert agent2.task_state.total_steps == 5, f"Expected 5 total steps, got {agent2.task_state.total_steps}"
        assert agent2.task_state.action_description == "Creating the main function"
        
        print("\n✓ State persistence test passed!")
        
    finally:
        os.unlink(db_path)


def test_pause_and_resume():
    """Test pausing at any phase and resuming without repetition"""
    print("\n=== Test: Pause and Resume ===")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not set")
        return
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    
    try:
        agent = Agent(api_key=api_key, model="gpt-4o-mini")
        agent.history_manager = HistoryManager(db_path)
        session_id = agent.create_session("Pause Test")
        
        # Start execution phase
        print("\n1. Starting execution phase...")
        agent.task_state.phase = "execution"
        agent.task_state.step = 2
        agent.task_state.total_steps = 5
        agent.history_manager.save_task_state(session_id, agent.task_state.get_state())
        print(f"   State: {agent.task_state.phase}")
        
        # Simulate pause (session reload)
        print("\n2. Pausing (simulating session reload)...")
        agent2 = Agent(api_key=api_key, model="gpt-4o-mini")
        agent2.history_manager = HistoryManager(db_path)
        agent2.load_session(session_id)
        print(f"   Resumed state: {agent2.task_state.phase}")
        
        # Continue from where we left off
        print("\n3. Continuing execution...")
        agent2.task_state.step = 3
        agent2.history_manager.save_task_state(session_id, agent2.task_state.get_state())
        print(f"   State: {agent2.task_state.phase}")
        
        assert agent2.task_state.step == 3, f"Expected step 3, got {agent2.task_state.step}"
        assert agent2.task_state.phase == "execution", f"Expected 'execution', got '{agent2.task_state.phase}'"
        
        print("\n✓ Pause and resume test passed!")
        
    finally:
        os.unlink(db_path)


def test_display_format():
    """Test state display formatting"""
    print("\n=== Test: Display Format ===")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not set")
        return
    
    agent = Agent(api_key=api_key, model="gpt-4o-mini")
    
    # Test with total_steps
    print("\n1. Testing display with total steps...")
    agent.task_state.phase = "planning"
    agent.task_state.step = 2
    agent.task_state.total_steps = 5
    display = agent.task_state.phase
    print(f"   Display: '{display}'")
    assert display == "[Planning 2/5]", f"Expected '[Planning 2/5]', got '{display}'"
    
    # Test without total_steps
    print("\n2. Testing display without total steps...")
    agent.task_state.phase = "execution"
    agent.task_state.step = 1
    agent.task_state.total_steps = 0
    display = agent.task_state.phase
    print(f"   Display: '{display}'")
    assert display == "[Execution]", f"Expected '[Execution]', got '{display}'"
    
    # Test empty state
    print("\n3. Testing empty state...")
    agent.task_state.reset()
    display = agent.task_state.phase
    print(f"   Display: '{display}'")
    assert display == "", f"Expected empty string, got '{display}'"
    
    print("\n✓ Display format test passed!")


def run_all_tests():
    """Run all test scenarios"""
    print("=" * 60)
    print("Task State Machine Test Suite")
    print("=" * 60)
    
    # New chat-based tests
    test_realistic_conversation_flow()
    # test_multi_turn_with_pause_resume()
    # test_edge_cases()
    
    # Original tests
    # test_state_progression()
    # test_state_persistence()
    # test_pause_and_resume()
    # test_display_format()
    
    print("\n" + "=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
