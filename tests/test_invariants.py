"""
Test scenarios for invariants functionality

Tests that:
1. Invariants are kept separate from dialogue
2. Assistant clearly takes them into account in reasoning
3. Assistant refuses to propose solutions that violate invariants
"""

import os
import tempfile
import time
import threading
from rich.console import Console
from rich.markdown import Markdown
from aiadvent.agent import Agent
from aiadvent.agent.history import HistoryManager


console = Console()


def show_thinking_animation(stop_event):
    """Show thinking animation while API call is in progress"""
    frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    idx = 0
    while not stop_event.is_set():
        console.print(f"[cyan]🤖 AI: {frames[idx]} thinking...[/cyan]", end="\r")
        idx = (idx + 1) % len(frames)
        time.sleep(0.1)
    console.print(" " * 50, end="\r")


def test_invariant_enforcement_business():
    """
    Test Case 1: Business Rules Invariant
    User sets business constraints, then requests something that violates them
    """
    console.print("\n" + "="*60, style="bold cyan")
    console.print("Test 1: Business Rules Invariant Enforcement", style="bold cyan")
    console.print("="*60 + "\n", style="bold cyan")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not set")
        return False
    
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    
    try:
        agent = Agent(api_key=api_key, model="gpt-4o-mini")
        agent.history_manager = HistoryManager(db_path)
        agent.session_id = agent.create_session("Architecture Invariant Test")
        
        # Add architecture invariant
        agent.invariants_manager.add_invariant(
            session_id=agent.session_id,
            category="architecture",
            title="Microservices Architecture Only",
            description="All solutions must use microservices architecture. No monolithic applications.",
            rationale="Company standard for scalability and independent deployment",
            priority="critical"
        )
        agent._rebuild_system_prompt()
        
        console.print("✓ Added invariant: Microservices Architecture Only\n", style="green")
        
        # Dialog with 10+ messages (5 user + 5 AI)
        exchanges = [
            ("Hello! I need help designing a new application.", "Should respect microservices"),
            ("What are the benefits of microservices?", "Should explain benefits"),
            ("Can you help me design a simple web app?", "Should suggest microservices design"),
            ("I want to build everything in one codebase for simplicity. Can you help?", "Should REFUSE - violates invariant"),
            ("Why can't I use a monolithic approach? It's simpler.", "Should explain invariant rationale"),
            ("What if I just want a small prototype?", "Should still enforce invariant or suggest compliant alternative"),
            ("Can you show me a monolithic Flask app example?", "Should REFUSE - violates invariant"),
            ("Okay, how would you structure it with microservices then?", "Should provide compliant solution"),
            ("What services would I need?", "Should detail microservices breakdown"),
            ("Thanks! Can you give me a single-file implementation?", "Should REFUSE if implies monolith"),
        ]
        
        violation_detected = False
        refusal_count = 0
        
        for i, (user_msg, expected_behavior) in enumerate(exchanges, 1):
            console.print(f"\n--- Exchange {i}/10 ---", style="bold yellow")
            console.print(f"User: {user_msg}", style="bold green")
            console.print(f"Expected: {expected_behavior}", style="dim")
            
            response = agent.think(user_msg)
            
            console.print("\nAssistant:", style="bold blue")
            console.print(Markdown(response))
            
            # Check if refusal occurred
            if "❌" in response or "cannot" in response.lower() or "violate" in response.lower():
                refusal_count += 1
                violation_detected = True
                console.print("\n✓ Refusal detected", style="green")
            
            stats = agent.get_token_stats()
            console.print(f"\n[Tokens - Prompt: {stats['prompt']} | History: {stats['history']} | Response: {stats['response']}]", style="dim")
        
        # Validation
        console.print("\n" + "="*60, style="bold cyan")
        console.print("Test Results:", style="bold cyan")
        console.print("="*60, style="bold cyan")
        
        success = True
        
        if refusal_count >= 2:
            console.print(f"✓ Refusals detected: {refusal_count}", style="green")
        else:
            console.print(f"✗ Expected at least 2 refusals, got {refusal_count}", style="red")
            success = False
        
        if violation_detected:
            console.print("✓ Invariant enforcement working", style="green")
        else:
            console.print("✗ No violations detected", style="red")
            success = False
        
        return success
        
    finally:
        os.unlink(db_path)


def test_multiple_invariants():
    """
    Test Case 2: Multiple Invariants
    User sets multiple constraints and tries to violate different ones
    """
    console.print("\n" + "="*60, style="bold cyan")
    console.print("Test 2: Multiple Invariants Enforcement", style="bold cyan")
    console.print("="*60 + "\n", style="bold cyan")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not set")
        return False
    
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    
    try:
        agent = Agent(api_key=api_key, model="gpt-4o-mini")
        agent.history_manager = HistoryManager(db_path)
        agent.session_id = agent.create_session("Multiple Invariants Test")
        
        # Add multiple invariants
        agent.invariants_manager.add_invariant(
            session_id=agent.session_id,
            category="stack",
            title="React Frontend Only",
            description="Frontend must use React. No Vue, Angular, or other frameworks.",
            rationale="Team expertise",
            priority="high"
        )
        
        agent.invariants_manager.add_invariant(
            session_id=agent.session_id,
            category="technical",
            title="RESTful APIs Only",
            description="All APIs must follow REST principles. No GraphQL or gRPC.",
            rationale="Existing infrastructure and tooling",
            priority="high"
        )
        
        agent._rebuild_system_prompt()
        
        console.print("✓ Added 2 invariants: React Frontend + RESTful APIs\n", style="green")
        
        exchanges = [
            ("I need to build a web application", "Should suggest React and REST"),
            ("What frontend framework should I use?", "Should suggest React"),
            ("What about the API design?", "Should suggest REST"),
            ("I think Vue.js would be better. Can you help?", "Should REFUSE - violates React invariant"),
            ("Can we use GraphQL for the API?", "Should REFUSE - violates REST invariant"),
            ("Why not GraphQL? It's more efficient.", "Should explain REST invariant"),
            ("Can I use Angular instead of React?", "Should REFUSE - violates React invariant"),
            ("Okay, show me a React + REST example", "Should provide compliant solution"),
            ("How do I structure REST endpoints?", "Should provide compliant solution"),
            ("Can I at least use Vue for one small component?", "Should REFUSE - violates React invariant"),
        ]
        
        refusal_count = 0
        
        for i, (user_msg, expected_behavior) in enumerate(exchanges, 1):
            console.print(f"\n--- Exchange {i}/10 ---", style="bold yellow")
            console.print(f"User: {user_msg}", style="bold green")
            console.print(f"Expected: {expected_behavior}", style="dim")
            
            stop_event = threading.Event()
            thinking_thread = threading.Thread(target=show_thinking_animation, args=(stop_event,), daemon=True)
            thinking_thread.start()
            
            response = agent.think(user_msg)
            
            stop_event.set()
            thinking_thread.join(timeout=0.5)
            
            console.print("\nAssistant:", style="bold blue")
            console.print(Markdown(response))
            
            if "❌" in response or "cannot" in response.lower() or "violate" in response.lower():
                refusal_count += 1
                console.print("\n✓ Refusal detected", style="green")
            
            stats = agent.get_token_stats()
            console.print(f"\n[Tokens - Prompt: {stats['prompt']} | History: {stats['history']} | Response: {stats['response']}]", style="dim")
        
        console.print("\n" + "="*60, style="bold cyan")
        console.print("Test Results:", style="bold cyan")
        console.print("="*60, style="bold cyan")
        
        success = refusal_count >= 4
        
        if success:
            console.print(f"✓ Refusals detected: {refusal_count}", style="green")
        else:
            console.print(f"✗ Expected at least 4 refusals, got {refusal_count}", style="red")
        
        return success
        
    finally:
        os.unlink(db_path)


def test_invariant_persistence():
    """
    Test Case 3: Invariant Persistence
    Verify invariants persist across session reloads
    """
    console.print("\n" + "="*60, style="bold cyan")
    console.print("Test 3: Invariant Persistence", style="bold cyan")
    console.print("="*60 + "\n", style="bold cyan")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not set")
        return False
    
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    
    try:
        # Session 1: Create invariant
        agent1 = Agent(api_key=api_key, model="gpt-4o-mini")
        agent1.history_manager = HistoryManager(db_path)
        session_id = agent1.create_session("Persistence Test")
        
        agent1.invariants_manager.add_invariant(
            session_id=session_id,
            category="technical",
            title="No Third-Party Libraries",
            description="Use only standard library. No external dependencies.",
            rationale="Security policy",
            priority="critical"
        )
        agent1._rebuild_system_prompt()
        
        console.print("✓ Session 1: Added invariant\n", style="green")
        
        # Verify it was added
        invariants_check = agent1.invariants_manager.get_invariants(session_id)
        console.print(f"  Debug: Session {session_id} has {len(invariants_check)} invariant(s)", style="dim")
        
        # Session 2: Reload and verify
        agent2 = Agent(api_key=api_key, model="gpt-4o-mini")
        agent2.history_manager = HistoryManager(db_path)
        agent2.load_session(session_id)
        
        invariants = agent2.invariants_manager.get_invariants(session_id)
        
        console.print(f"✓ Session 2: Loaded {len(invariants)} invariant(s) for session {session_id}\n", style="green")
        
        # Debug: show what we got
        if len(invariants) != 1:
            console.print(f"  Debug: Expected 1 invariant, got {len(invariants)}", style="yellow")
            seen_titles = set()
            for inv in invariants:
                if inv['title'] not in seen_titles:
                    console.print(f"    - {inv['title']} (session {inv['session_id']})", style="dim")
                    seen_titles.add(inv['title'])
        
        if len(invariants) >= 1 and any(inv['title'] == "No Third-Party Libraries" and inv['session_id'] == session_id for inv in invariants):
            console.print("✓ Invariant persisted correctly", style="green")
            
            # Test enforcement after reload
            console.print("\nUser: Can you show me how to use the requests library?", style="bold green")
            
            stop_event = threading.Event()
            thinking_thread = threading.Thread(target=show_thinking_animation, args=(stop_event,), daemon=True)
            thinking_thread.start()
            
            response = agent2.think("Can you show me how to use the requests library?")
            
            stop_event.set()
            thinking_thread.join(timeout=0.5)
            
            console.print("\nAssistant:", style="bold blue")
            console.print(Markdown(response))
            
            if "❌" in response or "cannot" in response.lower() or "violate" in response.lower():
                console.print("\n✓ Invariant enforced after reload", style="green")
                return True
            else:
                console.print("\n✗ Invariant not enforced after reload", style="red")
                return False
        else:
            console.print("✗ Invariant not persisted", style="red")
            return False
        
    finally:
        os.unlink(db_path)


def run_all_tests():
    """Run all test scenarios"""
    console.print("\n" + "█"*60, style="bold blue")
    console.print("  INVARIANTS ENFORCEMENT TEST SUITE", style="bold blue")
    console.print("█"*60 + "\n", style="bold blue")
    
    results = []
    
    try:
        result3 = test_invariant_enforcement_business()
        results.append(("Business Rules Invariant", result3))
        input("\nPress Enter to continue to next test...")
        
        result4 = test_multiple_invariants()
        results.append(("Multiple Invariants", result4))
        input("\nPress Enter to continue to next test...")
        
        result5 = test_invariant_persistence()
        results.append(("Invariant Persistence", result5))
        
        # Final summary
        console.print("\n" + "█"*60, style="bold blue")
        console.print("  TEST SUMMARY", style="bold blue")
        console.print("█"*60, style="bold blue")
        
        for name, passed in results:
            status = "✅ PASSED" if passed else "❌ FAILED"
            console.print(f"{name}: {status}")
        
        all_passed = all(result for _, result in results)
        console.print("\n" + "█"*60, style="bold blue")
        if all_passed:
            console.print("  ✅ ALL TESTS PASSED", style="bold green")
        else:
            console.print("  ❌ SOME TESTS FAILED", style="bold red")
        console.print("█"*60 + "\n", style="bold blue")
        
    except KeyboardInterrupt:
        console.print("\n\nTests interrupted by user.", style="yellow")
    except Exception as e:
        console.print(f"\n\nError during tests: {e}", style="red")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()
