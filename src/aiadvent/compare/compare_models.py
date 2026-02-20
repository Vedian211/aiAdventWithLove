import os
import time
from openai import OpenAI
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam
from rich.console import Console
from rich.table import Table
from rich.markdown import Markdown


def compare_models():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: Please set OPENAI_API_KEY environment variable")
        return

    client = OpenAI(api_key=api_key)
    console = Console()
    
    models = [
        ("gpt-4.1-nano", "Cheapest"),
        ("gpt-4.1-mini", "Medium"),
        ("gpt-5.2", "Most Expensive")
    ]
    
    user_input = input("Enter your question: ")
    print()
    
    results = []
    
    for model_name, tier in models:
        console.print(f"[bold cyan]Testing {model_name} ({tier})...[/bold cyan]")
        
        messages = [
            ChatCompletionSystemMessageParam(role="system", content="You are a helpful assistant."),
            ChatCompletionUserMessageParam(role="user", content=user_input)
        ]
        
        start_time = time.time()
        first_token_time = None
        response_content = ""
        prompt_tokens = 0
        completion_tokens = 0
        
        try:
            stream = client.chat.completions.create(
                model=model_name,
                messages=messages,
                stream=True,
                stream_options={"include_usage": True}
            )
            
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    if first_token_time is None:
                        first_token_time = time.time()
                    response_content += chunk.choices[0].delta.content
                
                if chunk.usage:
                    prompt_tokens = chunk.usage.prompt_tokens
                    completion_tokens = chunk.usage.completion_tokens
            
            total_time = time.time() - start_time
            ttft = first_token_time - start_time if first_token_time else 0
            total_tokens = prompt_tokens + completion_tokens
            
            # Pricing per 1M tokens
            pricing = {
                "gpt-4.1-nano": {"input": 0.20, "output": 0.80},
                "gpt-4.1-mini": {"input": 0.80, "output": 3.20},
                "gpt-5.2": {"input": 1.75, "output": 14.00}
            }
            
            model_pricing = pricing.get(model_name, {"input": 0, "output": 0})
            cost = (prompt_tokens / 1_000_000) * model_pricing["input"] + \
                   (completion_tokens / 1_000_000) * model_pricing["output"]
            
            results.append({
                "model": model_name,
                "tier": tier,
                "ttft": ttft,
                "total_time": total_time,
                "tokens": total_tokens,
                "cost": cost,
                "response": response_content
            })
            
            console.print(f"[green]✓ Completed in {total_time:.2f}s[/green]\n")
            
        except Exception as e:
            console.print(f"[red]✗ Error: {e}[/red]\n")
            results.append({
                "model": model_name,
                "tier": tier,
                "ttft": 0,
                "total_time": 0,
                "tokens": 0,
                "cost": 0,
                "response": f"Error: {e}"
            })
    
    # Display comparison table
    table = Table(title="Model Comparison Results")
    table.add_column("Model", style="cyan")
    table.add_column("Tier", style="magenta")
    table.add_column("Time to First Token", justify="right", style="green")
    table.add_column("Total Time", justify="right", style="yellow")
    table.add_column("Tokens", justify="right", style="blue")
    table.add_column("Cost", justify="right", style="red")
    
    for result in results:
        table.add_row(
            result["model"],
            result["tier"],
            f"{result['ttft']:.2f}s",
            f"{result['total_time']:.2f}s",
            str(result["tokens"]),
            f"${result['cost']:.6f}"
        )
    
    console.print(table)
    
    # Display responses table
    console.print("\n")
    response_table = Table(title="Model Responses")
    
    # Add columns for each model
    for result in results:
        response_table.add_column(result["model"], style="cyan", vertical="top")
    
    # Add single row with all responses as markdown
    response_table.add_row(*[Markdown(result["response"]) for result in results])
    
    console.print(response_table)
    
    # Generate analysis prompt
    analysis_prompt = f"""Compare the three model responses to the question: "{user_input}"

Analyze based on these criteria:
1. **Quality** - accuracy, completeness, clarity of the answer
2. **Speed** - response time performance
3. **Cost Efficiency** - value for tokens/price spent

Performance Data:
- gpt-4.1-nano: {results[0]['tokens']} tokens, ${results[0]['cost']:.6f}, TTFT: {results[0]['ttft']:.2f}s, Total: {results[0]['total_time']:.2f}s
- gpt-4.1-mini: {results[1]['tokens']} tokens, ${results[1]['cost']:.6f}, TTFT: {results[1]['ttft']:.2f}s, Total: {results[1]['total_time']:.2f}s
- gpt-5.2: {results[2]['tokens']} tokens, ${results[2]['cost']:.6f}, TTFT: {results[2]['ttft']:.2f}s, Total: {results[2]['total_time']:.2f}s

Provide a structured response:
- Quality rating: [model name] - [score/10]
- Speed rating: [model name] - [score/10]
- Cost efficiency rating: [model name] - [score/10]
- **Overall Winner**: [model name] - [total score/30]
- Brief justification (1-2 sentences)"""

    # Get analysis from each model
    console.print("\n")
    console.print("[bold yellow]Getting analysis from each model...[/bold yellow]\n")
    
    analysis_results = []
    for model_name, tier in models:
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    ChatCompletionSystemMessageParam(role="system", content="You are an AI model comparison expert."),
                    ChatCompletionUserMessageParam(role="user", content=analysis_prompt)
                ]
            )
            analysis_results.append({
                "model": model_name,
                "analysis": response.choices[0].message.content
            })
        except Exception as e:
            analysis_results.append({
                "model": model_name,
                "analysis": f"Error: {e}"
            })
    
    # Display analysis table
    analysis_table = Table(title="Model Self-Analysis")
    for result in analysis_results:
        analysis_table.add_column(result["model"], style="cyan", vertical="top")
    
    analysis_table.add_row(*[Markdown(result["analysis"]) for result in analysis_results])
    console.print(analysis_table)
    
    # Extract scores and determine overall winner
    console.print("\n")
    console.print("[bold green]Final Verdict[/bold green]")
    
    model_scores = {"gpt-4.1-nano": 0, "gpt-4.1-mini": 0, "gpt-5.2": 0}
    
    for analysis in analysis_results:
        text = analysis["analysis"].lower()
        # Look for "overall winner" section and extract the model name
        if "overall winner" in text:
            # Check in order from most specific to least specific to avoid partial matches
            if "gpt-5.2" in text.split("overall winner")[1].split("\n")[0]:
                model_scores["gpt-5.2"] += 1
            elif "gpt-4.1-mini" in text.split("overall winner")[1].split("\n")[0]:
                model_scores["gpt-4.1-mini"] += 1
            elif "gpt-4.1-nano" in text.split("overall winner")[1].split("\n")[0]:
                model_scores["gpt-4.1-nano"] += 1
    
    winner = max(model_scores, key=model_scores.get)
    console.print(f"[bold yellow]🏆 Competition Winner: {winner}[/bold yellow]")

