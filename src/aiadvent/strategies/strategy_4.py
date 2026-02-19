from concurrent.futures import ThreadPoolExecutor, as_completed
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam
from aiadvent.utils import chat_loop, replay_typing_effect, MODEL


EXPERTS = {
    "Analyst": "You are a data analyst. Provide analytical insights with focus on patterns, trends, and data-driven conclusions.",
    "Engineer": "You are a software engineer. Provide technical solutions with focus on implementation, architecture, and best practices.",
    "Scientist": "You are a scientist. Provide scientific explanations with focus on theory, research, and evidence-based reasoning."
}


def run(client, temperature=0.7):
    """Group of experts answering in parallel"""
    
    def get_expert_response(expert_name, system_prompt, user_input):
        """Get streaming response from one expert"""
        stream = client.chat.completions.create(
            model=MODEL,
            temperature=temperature,
            messages=[
                ChatCompletionSystemMessageParam(role="system", content=system_prompt),
                ChatCompletionUserMessageParam(role="user", content=user_input)
            ],
            stream=True,
            stream_options={"include_usage": True}
        )
        
        chunks = []
        usage_data = None
        
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                safe_content = content.encode('utf-8', errors='ignore').decode('utf-8')
                chunks.append(safe_content)
            
            if chunk.usage:
                usage_data = chunk.usage
        
        return expert_name, chunks, usage_data
    
    def handle_input(user_input, console, tracker):
        print("\n[Consulting experts...]\n")
        
        # Run all experts in parallel
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(get_expert_response, name, prompt, user_input): name
                for name, prompt in EXPERTS.items()
            }
            
            # Display results as they complete
            for future in as_completed(futures):
                expert_name, chunks, usage_data = future.result()
                console.print(f"\n[bold cyan]--- {expert_name} ---[/bold cyan]\n")
                replay_typing_effect(chunks, console)
                tracker.add_usage(usage_data)
        
        print()
    
    chat_loop("Strategy 4: Group of experts mode", handle_input)
