from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam
from aiadvent.utils import chat_loop, create_stream, stream_with_typing_effect


def run(client, temperature=0.7):
    """API call with system prompt asking to solve step by step"""
    
    def handle_input(user_input, console, tracker):
        stream = create_stream(client, [
            ChatCompletionSystemMessageParam(role="system", content="Solve the problem step by step."),
            ChatCompletionUserMessageParam(role="user", content=user_input)
        ], temperature)
        print()
        _, usage_data = stream_with_typing_effect(stream, console)
        tracker.add_usage(usage_data)
        print()
    
    chat_loop("Strategy 2: Step-by-step solving mode", handle_input)

