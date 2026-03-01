import os
import sys
import time
from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live
from rich.spinner import Spinner
from aiadvent.agent import Agent


def select_or_create_session(agent: Agent) -> bool:
    """Show session selection UI. Returns True if session selected/created, False to exit"""
    sessions = agent.list_sessions()
    is_new_session = False
    
    print("\n=== Available Sessions ===")
    if sessions:
        for idx, session in enumerate(sessions, 1):
            # Convert Unix timestamp to readable format
            from datetime import datetime
            last_updated = datetime.fromtimestamp(session['last_updated']).strftime('%Y-%m-%d %H:%M:%S')
            print(f"{idx}. {session['name']} ({session['strategy']}) - Last updated: {last_updated}")
        print(f"{len(sessions) + 1}. Create new session")
    else:
        print("No existing sessions found.")
        print("1. Create new session")
    
    print("0. Exit")
    
    while True:
        try:
            choice = input("\nSelect option: ").strip()
            
            if choice == "0":
                return False
            
            choice_num = int(choice)
            
            # Create new session
            if (sessions and choice_num == len(sessions) + 1) or (not sessions and choice_num == 1):
                agent.create_session("New Chat")
                print(f"✓ Created new session\n")
                return True
            
            # Load existing session
            if sessions and 1 <= choice_num <= len(sessions):
                session = sessions[choice_num - 1]
                print(f"Loading session '{session['name']}'...\n")
                agent.load_session(session['id'])
                
                console = Console()
                
                # Replay chat history (skip system prompt)
                for msg in agent.messages:
                    if msg["role"] == "system":
                        continue
                    
                    if msg["role"] == "user":
                        # Show user input with prompt style in green
                        token_count = agent.count_tokens()
                        percentage = int((token_count / agent.TOKEN_LIMIT) * 100)
                        console.print(f"[{percentage}%] > {msg['content']}", style="bold green")
                        print()
                    elif msg["role"] == "assistant":
                        # Show assistant response with markdown
                        console.print(Markdown(msg['content']))
                        print()
                
                return True
            
            print("Invalid choice. Please try again.")
            
        except (ValueError, KeyboardInterrupt):
            print("\nInvalid input. Please enter a number.")
            continue


def delete_session_command():
    """Standalone command to delete sessions"""
    from aiadvent.agent.history import HistoryManager
    
    manager = HistoryManager()
    sessions = manager.list_sessions()
    
    if not sessions:
        print("No sessions found.")
        return
    
    print("\n=== Available Sessions ===")
    for idx, session in enumerate(sessions, 1):
        print(f"{idx}. {session['name']} (Last updated: {session['last_updated'][:19]})")
    print("0. Cancel")
    
    try:
        choice = input("\nSelect session to delete: ").strip()
        
        if choice == "0":
            print("Cancelled.")
            return
        
        choice_num = int(choice)
        
        if 1 <= choice_num <= len(sessions):
            session_to_delete = sessions[choice_num - 1]
            confirm = input(f"Delete '{session_to_delete['name']}'? (yes/no): ").strip().lower()
            
            if confirm == "yes":
                manager.delete_session(session_to_delete['id'])
                print(f"✓ Deleted session: {session_to_delete['name']}")
            else:
                print("Cancelled.")
        else:
            print("Invalid choice.")
    
    except (ValueError, KeyboardInterrupt):
        print("\nCancelled.")


def start():
    """Start the AI agent interactive session"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: Please set OPENAI_API_KEY environment variable")
        return
    
    # Parse strategy argument
    strategy = "sliding_window"  # default
    if len(sys.argv) > 2:
        arg_strategy = sys.argv[2].lower()
        if arg_strategy in ["sliding_window", "sticky_facts", "branching"]:
            strategy = arg_strategy
        else:
            print(f"Unknown strategy: {arg_strategy}")
            print("Available strategies: sliding_window, sticky_facts, branching")
            return
    
    # Enable compression only for sliding_window (for now)
    compression_enabled = (strategy == "sliding_window")
    
    agent = Agent(
        api_key=api_key,
        model="gpt-4o-mini",
        system_prompt="You are a helpful AI assistant using a Branching Dialogue strategy." if strategy == "branching" else "You are a helpful AI assistant.",
        compression_enabled=compression_enabled,
        strategy=strategy
    )
    
    # Session selection
    if not select_or_create_session(agent):
        print("Goodbye!")
        return
    
    console = Console()
    
    # Show available commands based on strategy
    base_commands = "Type '/help' for commands, '/exit' or '/quit' to stop."
    
    console.print(f"AI Agent started ({strategy} strategy). {base_commands}\n", style="bold blue")
    
    first_exchange = True  # Track if this is the first exchange
    
    try:
        while True:
            token_count = agent.count_tokens()
            percentage = int((token_count / agent.TOKEN_LIMIT) * 100)
            
            console.print(f"[{percentage}%] > ", style="bold green", end="")
            user_input = input()
            
            if user_input.lower() in ['/exit', '/quit']:
                print(f"\nTotal tokens used in session: {agent.total_tokens_used}")
                print("Goodbye!")
                break
            
            if user_input == "/help":
                console.print("\n=== Available Commands ===", style="bold cyan")
                print("\nGeneral:")
                print("  /help       - Show this help message")
                print("  /exit       - Exit the session")
                print("  /quit       - Exit the session")
                print("  /clear      - Clear conversation history")
                print("  /sessions   - Switch to another session")
                print("  /delete     - Delete a session")
                
                if agent.strategy == "sliding_window":
                    print("\nSliding Window Strategy:")
                    print("  /compression [on|off|status] - Toggle or check compression")
                elif agent.strategy == "sticky_facts":
                    print("\nSticky Facts Strategy:")
                    print("  /facts      - View stored facts")
                elif agent.strategy == "branching":
                    print("\nBranching Strategy:")
                    print("  /checkpoint <name>           - Create a checkpoint")
                    print("  /checkpoint                  - List all checkpoints")
                    print("  /branch                      - List all branches")
                    print("  /branch create <checkpoint>  - Create branch from checkpoint")
                    print("  /branch switch <branch_id>   - Switch to a branch")
                
                print()
                continue
            
            if user_input == "/clear":
                print(f"[History cleared. Tokens used in session: {agent.total_tokens_used}]\n")
                agent.clear_history()
                continue
            
            if user_input == "/sessions":
                if select_or_create_session(agent):
                    print("Session switched.\n")
                    first_exchange = True  # Reset for new session
                else:
                    print("Staying in current session.\n")
                continue
            
            if user_input == "/delete":
                sessions = agent.list_sessions()
                if not sessions:
                    print("No sessions to delete.\n")
                    continue
                
                print("\n=== Delete Session ===")
                for idx, session in enumerate(sessions, 1):
                    from datetime import datetime
                    last_updated = datetime.fromtimestamp(session['last_updated']).strftime('%Y-%m-%d %H:%M:%S')
                    print(f"{idx}. {session['name']} ({session['strategy']}) - {last_updated}")
                print("0. Cancel")
                
                try:
                    choice = input("\nSelect session to delete: ").strip()
                    if choice == "0":
                        print("Cancelled.\n")
                        continue
                    
                    choice_num = int(choice)
                    if 1 <= choice_num <= len(sessions):
                        session_to_delete = sessions[choice_num - 1]
                        
                        # Confirm deletion
                        confirm = input(f"Delete '{session_to_delete['name']}'? (yes/no): ").strip().lower()
                        if confirm == "yes":
                            agent.history_manager.delete_session(session_to_delete['id'])
                            print(f"✓ Deleted session: {session_to_delete['name']}\n")
                            
                            # If deleted current session, prompt for new one
                            if agent.session_id == session_to_delete['id']:
                                print("Current session was deleted. Please select a new session.")
                                if not select_or_create_session(agent):
                                    print("Goodbye!")
                                    break
                        else:
                            print("Cancelled.\n")
                    else:
                        print("Invalid choice.\n")
                except (ValueError, KeyboardInterrupt):
                    print("\nCancelled.\n")
                continue
            
            if user_input.startswith("/compression"):
                parts = user_input.split()
                
                # Toggle compression
                if len(parts) == 1 or (len(parts) == 2 and parts[1] == "status"):
                    status = "enabled" if agent.compression_enabled else "disabled"
                    print(f"\nCompression: {status}")
                    
                    if agent.compression_enabled:
                        stats = agent.get_compression_stats()
                        if stats and stats['original'] > 0:
                            print(f"  Original tokens: {stats['original']}")
                            print(f"  Compressed tokens: {stats['compressed']}")
                            print(f"  Tokens saved: {stats['saved']}")
                            print(f"  Compression ratio: {stats['ratio']:.1f}%")
                        else:
                            print("  No compression stats yet (conversation too short)")
                    print()
                    continue
                
                if len(parts) == 2 and parts[1] in ["on", "off"]:
                    enabled = parts[1] == "on"
                    agent.toggle_compression(enabled)
                    status = "enabled" if enabled else "disabled"
                    print(f"\n✓ Compression {status}\n")
                    continue
                
                print("\nUsage: /compression [on|off|status]\n")
                continue
            
            if user_input == "/facts":
                if agent.sticky_facts_manager:
                    stats = agent.sticky_facts_manager.get_stats()
                    if stats["total_facts"] > 0:
                        import json
                        print("\n=== Sticky Facts ===")
                        for key, value in stats["facts"].items():
                            if value:
                                if isinstance(value, (dict, list)):
                                    print(f"  {key}:")
                                    print(f"    {json.dumps(value, indent=4)}")
                                else:
                                    print(f"  {key}: {value}")
                        print()
                    else:
                        print("\nNo facts stored yet.\n")
                else:
                    print("\nSticky facts not enabled for this session.\n")
                continue
            
            if user_input.startswith("/checkpoint"):
                if not agent.branching_manager:
                    print("\nBranching not enabled for this session.\n")
                    continue
                
                parts = user_input.split(maxsplit=1)
                if len(parts) == 1:
                    # List checkpoints
                    checkpoints = agent.branching_manager.list_checkpoints()
                    if checkpoints:
                        print("\n=== Checkpoints ===")
                        for cp in checkpoints:
                            print(f"  {cp['id']}: {cp['name']} ({cp['message_count']} messages)")
                        print()
                    else:
                        print("\nNo checkpoints created yet.\n")
                else:
                    # Create checkpoint
                    name = parts[1]
                    cp_id = agent.branching_manager.create_checkpoint(name, agent.messages)
                    print(f"\n✓ Created checkpoint '{name}' ({cp_id})\n")
                continue
            
            if user_input.startswith("/branch"):
                if not agent.branching_manager:
                    print("\nBranching not enabled for this session.\n")
                    continue
                
                parts = user_input.split()
                
                if len(parts) == 1:
                    # List branches
                    branches = agent.branching_manager.list_branches()
                    if branches:
                        print("\n=== Branches ===")
                        for br in branches:
                            active = " (active)" if br['active'] else ""
                            print(f"  {br['id']}: {br['name']} from {br['checkpoint_id']} ({br['message_count']} messages){active}")
                        print()
                    else:
                        print("\nNo branches created yet.\n")
                elif len(parts) == 3 and parts[1] == "create":
                    # Create branch: /branch create <checkpoint_id> <name>
                    checkpoint_id = parts[2]
                    name = input("Branch name: ").strip()
                    br_id = agent.branching_manager.create_branch(checkpoint_id, name, agent.messages)
                    if br_id:
                        print(f"\n✓ Created branch '{name}' ({br_id}) from {checkpoint_id}\n")
                    else:
                        print(f"\n✗ Checkpoint {checkpoint_id} not found\n")
                elif len(parts) == 3 and parts[1] == "switch":
                    # Switch branch: /branch switch <branch_id>
                    branch_id = parts[2]
                    messages = agent.branching_manager.switch_branch(branch_id)
                    if messages:
                        agent.messages = messages
                        print(f"\n✓ Switched to branch {branch_id}\n")
                    else:
                        print(f"\n✗ Branch {branch_id} not found\n")
                else:
                    print("\nUsage:")
                    print("  /branch                    - List all branches")
                    print("  /branch create <cp_id>     - Create branch from checkpoint")
                    print("  /branch switch <br_id>     - Switch to branch\n")
                continue
            
            if not user_input.strip():
                continue
            
            try:
                print()
                
                spinner = Spinner("dots", text="Thinking...")
                
                with Live(spinner, console=console, refresh_per_second=10) as live:
                    stream = agent.think_stream(user_input)
                    
                    response_content = ""
                    first_chunk = True
                    
                    for chunk in stream:
                        if chunk.choices and chunk.choices[0].delta.content:
                            if first_chunk:
                                time.sleep(0.1)
                                first_chunk = False
                            content = chunk.choices[0].delta.content
                            response_content += content
                            live.update(Markdown(response_content))
                        
                        # Track token usage from stream
                        if chunk.usage:
                            agent.total_tokens_used += chunk.usage.total_tokens
                
                # Add response to agent's history
                agent.add_message("assistant", response_content)
                
                # Count response tokens
                agent.set_last_response_tokens(response_content)
                
                # Display token statistics
                stats = agent.get_token_stats()
                
                if agent.compression_enabled and "compression" in stats and stats["compression"]["original"] > 0:
                    comp = stats["compression"]
                    print(f"\n[Tokens - Prompt: {stats['prompt']} | History: {stats['history']} | Compressed: {comp['original']}→{comp['compressed']} ({comp['ratio']:.1f}% saved) | Response: {stats['response']}]")
                elif agent.sticky_facts_manager and "sticky_facts" in stats:
                    facts = stats["sticky_facts"]
                    print(f"\n[Tokens - Prompt: {stats['prompt']} | History: {stats['history']} | Response: {stats['response']} | Facts: {facts['total_facts']}]")
                elif agent.branching_manager and "branching" in stats:
                    branching = stats["branching"]
                    branch_info = f" | Branch: {branching['current_branch']}" if branching['current_branch'] else ""
                    print(f"\n[Tokens - Prompt: {stats['prompt']} | History: {stats['history']} | Response: {stats['response']} | Checkpoints: {branching['checkpoints']} | Branches: {branching['branches']}{branch_info}]")
                else:
                    print(f"\n[Tokens - Prompt: {stats['prompt']} | History: {stats['history']} | Response: {stats['response']}]")
                
                # Save to database
                agent.save_message_to_db("user", user_input, stats['prompt'])
                agent.save_message_to_db("assistant", response_content, stats['response'])
                
                # Save facts only if using sticky facts strategy
                if agent.strategy == "sticky_facts" and agent.sticky_facts_manager:
                    agent.save_facts()
                
                # Generate title after first exchange for new sessions
                if first_exchange:
                    sessions = agent.list_sessions()
                    current_session = next((s for s in sessions if s['id'] == agent.session_id), None)
                    if current_session and current_session['name'] == "New Chat":
                        print("Generating session title...")
                        title = agent.generate_session_title()
                        agent.update_session_name(title)
                        print(f"Session titled: {title}\n")
                    first_exchange = False
                
                print()
                
                # Check token limit after response
                is_warning, token_count = agent.check_token_limit()
                if is_warning:
                    print(f"⚠️  Warning: Context window at {token_count}/{agent.TOKEN_LIMIT} tokens ({int(token_count/agent.TOKEN_LIMIT*100)}%)")
                    print("Consider using '/clear' to reset conversation history.\n")
                    
            except KeyboardInterrupt:
                print("\n[Cancelled]\n")
                continue
                
    except KeyboardInterrupt:
        print(f"\n\nTotal tokens used in session: {agent.total_tokens_used}")
        print("Goodbye!")


def main():
    """Main entry point for agent CLI"""
    if len(sys.argv) < 2:
        print("Usage: agent <command> [strategy]")
        print("Commands:")
        print("  start [strategy]  Start the AI agent")
        print("  delete            Delete a session")
        print("\nStrategies:")
        print("  sliding_window    Use sliding window compression (default)")
        print("  sticky_facts      Use sticky facts (coming soon)")
        print("  branching         Use branching (coming soon)")
        return
    
    command = sys.argv[1]
    
    if command == "start":
        start()
    elif command == "delete":
        delete_session_command()
    else:
        print(f"Unknown command: {command}")
        print("Available commands: start, delete")


if __name__ == "__main__":
    main()
