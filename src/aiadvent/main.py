import os
import sys
from openai import OpenAI
from openai.types.chat import (ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam, ChatCompletionAssistantMessageParam)
from rich.console import Console

from aiadvent.strategies import strategy_1, strategy_2, strategy_3, strategy_4


# noinspection PyTypeChecker
def main():
    # Get API key from environment variable
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: Please set OPENAI_API_KEY environment variable")
        return

    # Parse parameters
    strategy = None
    temperature = 0.7
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg.startswith('-p'):
            try:
                strategy = int(arg[2:])
            except ValueError:
                print(f"Error: Invalid strategy parameter '{arg}'. Use -p1, -p2, etc.")
                return
        elif arg == '-t':
            if i + 1 < len(sys.argv):
                try:
                    temperature = float(sys.argv[i + 1])
                    if not 0 <= temperature <= 2:
                        print("Error: Temperature must be between 0 and 2")
                        return
                    i += 1
                except ValueError:
                    print(f"Error: Invalid temperature value '{sys.argv[i + 1]}'")
                    return
            else:
                print("Error: -t requires a value")
                return
        i += 1

    client = OpenAI(api_key=api_key)
    
    # Route to strategy
    if strategy == 1:
        strategy_1.run(client, temperature)
        return
    elif strategy == 2:
        strategy_2.run(client, temperature)
        return
    elif strategy == 3:
        strategy_3.run(client, temperature)
        return
    elif strategy == 4:
        strategy_4.run(client, temperature)
        return
    
    # Default behavior (original implementation)
    console = Console()
    messages = [
        ChatCompletionSystemMessageParam(
            role="system",
            content="You are a helpful assistant. Provide clear, short, concise answers in a structured format."
        )
    ]
    
    total_tokens = 0
    prompt_tokens = 0
    completion_tokens = 0

    print("Chat started. Type 'exit', 'quit', or press Ctrl+C to stop.\n")

    try:
        while True:
            user_input = input("> ")
            
            if user_input.lower() in ['/exit', '/quit']:
                print(f"\nTotal tokens used: {total_tokens} (prompt: {prompt_tokens}, completion: {completion_tokens})")
                print("Goodbye!")
                break

            messages.append(ChatCompletionUserMessageParam(role="user", content=user_input))

            try:
                stream = client.chat.completions.create(
                    model="gpt-4.1-mini",
                    messages=messages,
                    max_tokens=500,
                    temperature=temperature,
                    stream=True,
                    stream_options={"include_usage": True},
                )

                print()
                response_content = ""
                finish_reason = None
                for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        safe_content = content.encode('utf-8', errors='ignore').decode('utf-8')
                        response_content += safe_content
                        print(safe_content, end='', flush=True)
                    
                    if chunk.choices and chunk.choices[0].finish_reason:
                        finish_reason = chunk.choices[0].finish_reason
                    
                    if chunk.usage:
                        total_tokens += chunk.usage.total_tokens
                        prompt_tokens += chunk.usage.prompt_tokens
                        completion_tokens += chunk.usage.completion_tokens
                
                print()
                if finish_reason == "length":
                    print("\n[Response stopped: max tokens reached]")
                print()
                
                messages.append(ChatCompletionAssistantMessageParam(role="assistant", content=response_content))

            except KeyboardInterrupt:
                print("\n\n[Generation cancelled by user]\n")
                messages.pop()
                continue

    except KeyboardInterrupt:
        print(f"\n\nTotal tokens used: {total_tokens} (prompt: {prompt_tokens}, completion: {completion_tokens})")
        print("Goodbye!")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
