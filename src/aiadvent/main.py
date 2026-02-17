import os
from openai import OpenAI
from openai.types.chat import (ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam, ChatCompletionAssistantMessageParam)
from rich.console import Console
from rich.markdown import Markdown


# noinspection PyTypeChecker
def main():
    # Get API key from environment variable
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: Please set OPENAI_API_KEY environment variable")
        return

    client = OpenAI(api_key=api_key)
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
                    max_tokens=100,
                    temperature=0.7,
                    stream=True,
                    stream_options={"include_usage": True},
                    stop=["Humans", "Fun Facts", "Fingerprints", "Brain"]
                )

                print()
                response_content = ""
                finish_reason = None
                for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        safe_content = content.encode('utf-8', errors='ignore').decode('utf-8')
                        # print(safe_content, end="", flush=True)
                        response_content += safe_content
                    
                    if chunk.choices and chunk.choices[0].finish_reason:
                        finish_reason = chunk.choices[0].finish_reason
                    
                    if chunk.usage:
                        total_tokens += chunk.usage.total_tokens
                        prompt_tokens += chunk.usage.prompt_tokens
                        completion_tokens += chunk.usage.completion_tokens
                
                print("\n")
                console.print(Markdown(response_content))
                if finish_reason == "stop" and response_content:
                    print("\n[Response stopped: stop phrase detected]")
                elif finish_reason == "length":
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
