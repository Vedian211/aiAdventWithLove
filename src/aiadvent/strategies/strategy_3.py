from textwrap import dedent
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam
from aiadvent.utils import chat_loop, create_stream, stream_with_typing_effect, MODEL


def run(client, temperature=0.7):
    """Generate optimized prompt first, then use it to answer"""
    
    def handle_input(user_input, console, tracker):
        # Step 1: Generate optimized prompt
        print("\n[Generating optimized prompt...]")
        prompt_response = client.chat.completions.create(
            model=MODEL,
            temperature=temperature,
            messages=[
                ChatCompletionSystemMessageParam(
                    role="system", 
                    content=dedent("""
                        You are an expert at crafting effective system prompts. 
                        Analyze the user's question and create a concise, actionable system prompt (max 3 sentences) 
                        that will guide an AI to provide the best possible answer. 
                        Focus on: 1) The specific expertise or role needed, 2) The format or structure of the response, 
                        3) Key considerations or constraints. Return only the system prompt text.
                    """).strip()
                ),
                ChatCompletionUserMessageParam(role="user", content=user_input)
            ]
        )
        
        generated_prompt = prompt_response.choices[0].message.content
        tracker.add_usage(prompt_response.usage)
        print(f"[Using prompt: {generated_prompt}]\n")
        
        # Step 2: Use generated prompt to answer
        stream = create_stream(client, [
            ChatCompletionSystemMessageParam(role="system", content=generated_prompt),
            ChatCompletionUserMessageParam(role="user", content=user_input)
        ], temperature)
        _, usage_data = stream_with_typing_effect(stream, console)
        tracker.add_usage(usage_data)
        print()
    
    chat_loop("Strategy 3: Auto-prompt optimization mode", handle_input)

