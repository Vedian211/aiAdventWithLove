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
            print(f"{idx}. {session['name']} (Last updated: {session['last_updated'][:19]})")
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
    
    agent = Agent(
        api_key=api_key,
        model="gpt-4",
        system_prompt="You are a helpful AI assistant."
    )
    
    # Session selection
    if not select_or_create_session(agent):
        print("Goodbye!")
        return
    
    console = Console()
    print("AI Agent started. Type '/exit' or '/quit' to stop, '/clear' to clear history, '/sessions' to switch sessions, '/delete' to delete a session.\n")
    
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
                    print(f"{idx}. {session['name']}")
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
                print(f"\n[Tokens - Prompt: {stats['prompt']} | History: {stats['history']} | Response: {stats['response']}]")
                
                # Save to database
                agent.save_message_to_db("user", user_input)
                agent.save_message_to_db("assistant", response_content)
                
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
        print("Usage: agent <command>")
        print("Commands:")
        print("  start     Start the AI agent")
        print("  delete    Delete a session")
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
