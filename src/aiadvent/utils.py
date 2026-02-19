import time
from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live


MODEL = "gpt-4.1-mini"


class TokenTracker:
    """Track token usage across API calls"""
    def __init__(self):
        self.total_tokens = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
    
    def add_usage(self, usage):
        """Add usage data from API response"""
        if usage:
            self.total_tokens += usage.total_tokens
            self.prompt_tokens += usage.prompt_tokens
            self.completion_tokens += usage.completion_tokens
    
    def print_summary(self):
        """Print token usage summary"""
        print(f"\nTotal tokens used: {self.total_tokens} (prompt: {self.prompt_tokens}, completion: {self.completion_tokens})")


def stream_with_typing_effect(stream, console, delay=0.01):
    """Stream API response with typing effect and markdown rendering"""
    response_content = ""
    usage_data = None
    
    with Live(Markdown(response_content), console=console, refresh_per_second=20) as live:
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                safe_content = content.encode('utf-8', errors='ignore').decode('utf-8')
                response_content += safe_content
                live.update(Markdown(response_content))
                time.sleep(delay)
            
            if chunk.usage:
                usage_data = chunk.usage
    
    return response_content, usage_data


def replay_typing_effect(chunks, console, delay=0.01):
    """Replay pre-fetched chunks with typing effect"""
    displayed_content = ""
    with Live(Markdown(displayed_content), console=console, refresh_per_second=20) as live:
        for chunk in chunks:
            displayed_content += chunk
            live.update(Markdown(displayed_content))
            time.sleep(delay)


def create_stream(client, messages, temperature=0.7):
    """Create streaming API call with standard parameters"""
    return client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=temperature,
        stream=True,
        stream_options={"include_usage": True}
    )


def chat_loop(strategy_name, handler):
    """Standard chat loop for all strategies"""
    console = Console()
    tracker = TokenTracker()

    print(f"{strategy_name}")
    print("Chat started. Type 'exit', 'quit', or press Ctrl+C to stop.\n")

    try:
        while True:
            user_input = input("> ")
            
            if user_input.lower() in ['/exit', '/quit']:
                tracker.print_summary()
                print("Goodbye!")
                break

            try:
                handler(user_input, console, tracker)
            except KeyboardInterrupt:
                print("\n\n[Generation cancelled by user]\n")
                continue

    except KeyboardInterrupt:
        tracker.print_summary()
        print("Goodbye!")
