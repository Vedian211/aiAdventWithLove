import os
import sys
import time
from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live
from rich.spinner import Spinner
from aiadvent.agent import Agent


def start():
    """Start the AI agent interactive session"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: Please set OPENAI_API_KEY environment variable")
        return
    
    agent = Agent(
        api_key=api_key,
        model="gpt-4.1-nano",
        system_prompt="You are a helpful AI assistant."
    )
    
    console = Console()
    print("AI Agent started. Type '/exit' or '/quit' to stop, '/clear' to clear history.\n")
    
    try:
        while True:
            token_count = agent.count_tokens()
            percentage = int((token_count / agent.TOKEN_LIMIT) * 100)
            prompt = f"[{percentage}%] > "
            
            user_input = input(prompt)
            
            if user_input.lower() in ['/exit', '/quit']:
                print(f"\nTotal tokens used in session: {agent.total_tokens_used}")
                print("Goodbye!")
                break
            
            if user_input == "/clear":
                print(f"[History cleared. Tokens used in session: {agent.total_tokens_used}]\n")
                agent.clear_history()
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
        print("  start    Start the AI agent")
        return
    
    command = sys.argv[1]
    
    if command == "start":
        start()
    else:
        print(f"Unknown command: {command}")
        print("Available commands: start")


if __name__ == "__main__":
    main()
