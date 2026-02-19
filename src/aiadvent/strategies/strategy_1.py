from openai.types.chat import ChatCompletionUserMessageParam
from aiadvent.utils import chat_loop, create_stream, stream_with_typing_effect


def run(client, temperature=0.7):
    """Simple API call - no system prompt, no token limits, no stop arguments"""
    
    def handle_input(user_input, console, tracker):
        stream = create_stream(client, [ChatCompletionUserMessageParam(role="user", content=user_input)], temperature)
        print()
        _, usage_data = stream_with_typing_effect(stream, console)
        tracker.add_usage(usage_data)
        print()
    
    chat_loop("Strategy 1: Simple API call mode", handle_input)

