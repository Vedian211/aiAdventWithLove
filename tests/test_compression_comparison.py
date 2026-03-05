"""
Compression Comparison Test Suite

Compares AI agent performance with and without context compression:
- Scenario 1: Medium conversation (15-20 exchanges)
- Scenario 2: Long conversation (30-40 exchanges)

For each scenario, runs twice:
- Run A: Without compression (baseline)
- Run B: With compression enabled

Displays comparison graphs and metrics.
"""

import os
import time
from aiadvent.agent import Agent
from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live
from rich.spinner import Spinner


def print_separator(title):
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")


def print_comparison_graph(baseline_tokens, compressed_tokens, title="Token Usage Comparison"):
    """Print side-by-side comparison of token usage"""
    print(f"\n{'='*70}")
    print(title)
    print(f"{'='*70}\n")
    
    max_tokens = max(max(baseline_tokens), max(compressed_tokens))
    graph_width = 40
    
    print(f"{'Exchange':<10} {'Baseline':<45} {'Compressed':<45}")
    print("-" * 70)
    
    for i in range(len(baseline_tokens)):
        baseline = baseline_tokens[i]
        compressed = compressed_tokens[i] if i < len(compressed_tokens) else 0
        
        baseline_bar_len = int((baseline / max_tokens) * graph_width) if max_tokens > 0 else 0
        compressed_bar_len = int((compressed / max_tokens) * graph_width) if max_tokens > 0 else 0
        
        baseline_bar = "█" * baseline_bar_len
        compressed_bar = "█" * compressed_bar_len
        
        print(f"Q{i+1:<9} {baseline_bar:<40} {baseline:>4}  {compressed_bar:<40} {compressed:>4}")


def print_savings_graph(savings_percentages, title="Token Savings Over Time"):
    """Print graph showing compression savings percentage"""
    print(f"\n{'='*70}")
    print(title)
    print(f"{'='*70}\n")
    
    graph_width = 50
    
    for i, savings in enumerate(savings_percentages):
        if savings > 0:
            bar_len = int((savings / 100) * graph_width)
            bar = "█" * bar_len
            print(f"Q{i+1:<4} [{savings:>5.1f}%] {bar}")
        else:
            print(f"Q{i+1:<4} [  0.0%] (no compression yet)")


def print_cost_comparison(baseline_tokens, compressed_tokens, price_per_million=5.0):
    """Print cost comparison"""
    print(f"\n{'='*70}")
    print(f"Cost Comparison (${price_per_million} per million tokens)")
    print(f"{'='*70}\n")
    
    baseline_total = sum(baseline_tokens)
    compressed_total = sum(compressed_tokens)
    
    baseline_cost = (baseline_total / 1_000_000) * price_per_million
    compressed_cost = (compressed_total / 1_000_000) * price_per_million
    savings = baseline_cost - compressed_cost
    savings_pct = (savings / baseline_cost * 100) if baseline_cost > 0 else 0
    
    print(f"Baseline total tokens:   {baseline_total:>8}")
    print(f"Compressed total tokens: {compressed_total:>8}")
    print(f"Tokens saved:            {baseline_total - compressed_total:>8}")
    print(f"\nBaseline cost:           ${baseline_cost:>8.6f}")
    print(f"Compressed cost:         ${compressed_cost:>8.6f}")
    print(f"Cost savings:            ${savings:>8.6f} ({savings_pct:.1f}%)")


def print_summary_table(baseline_tokens, compressed_tokens):
    """Print summary statistics table"""
    print(f"\n{'='*70}")
    print("Summary Statistics")
    print(f"{'='*70}\n")
    
    baseline_total = sum(baseline_tokens)
    compressed_total = sum(compressed_tokens)
    baseline_avg = baseline_total / len(baseline_tokens) if baseline_tokens else 0
    compressed_avg = compressed_total / len(compressed_tokens) if compressed_tokens else 0
    
    print(f"{'Metric':<30} {'Baseline':>15} {'Compressed':>15} {'Difference':>10}")
    print("-" * 70)
    print(f"{'Total tokens':<30} {baseline_total:>15} {compressed_total:>15} {baseline_total - compressed_total:>10}")
    print(f"{'Average tokens/exchange':<30} {baseline_avg:>15.1f} {compressed_avg:>15.1f} {baseline_avg - compressed_avg:>10.1f}")
    print(f"{'Number of exchanges':<30} {len(baseline_tokens):>15} {len(compressed_tokens):>15} {0:>10}")
    
    if baseline_total > 0:
        compression_ratio = ((baseline_total - compressed_total) / baseline_total) * 100
        print(f"\nOverall compression ratio: {compression_ratio:.1f}%")


def run_conversation(agent, questions, console):
    """Run a conversation and collect token usage data"""
    token_history = []
    compression_active = []  # Track when compression is actually active
    
    for i, question in enumerate(questions):
        # Display user input in green
        console.print(f"\n> {question}", style="bold green")
        print()
        
        # Show thinking spinner and stream response
        spinner = Spinner("dots", text="Thinking...")
        
        with Live(spinner, console=console, refresh_per_second=10) as live:
            response = agent.think(question)
            time.sleep(0.1)  # Brief pause before showing response
            live.update(Markdown(response))
        
        stats = agent.get_token_stats()
        
        # For compressed runs, track the actual compressed tokens sent to API
        if agent.compression_enabled and "compression" in stats and stats["compression"]["original"] > 0:
            token_history.append(stats["compression"]["compressed"])
            compression_active.append(True)
        else:
            token_history.append(stats['history'])
            compression_active.append(False)
        
        # Display token stats
        if agent.compression_enabled and "compression" in stats and stats["compression"]["original"] > 0:
            comp = stats["compression"]
            print(f"\n[Tokens - History: {stats['history']} | Compressed: {comp['original']}→{comp['compressed']} ({comp['ratio']:.1f}% saved) | Response: {stats['response']}]")
        else:
            print(f"\n[Tokens - History: {stats['history']} | Response: {stats['response']}]")
        
        print()
    
    return token_history, compression_active


def test_scenario_medium():
    """Scenario 1: Medium conversation (15-20 exchanges)"""
    print_separator("SCENARIO 1: Medium Conversation (15-20 exchanges)")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not set")
        return
    
    # Questions for medium conversation
    questions = [
        "What is Python?",
        "What are the main features of Python?",
        "How do I create a list in Python?",
        "What's the difference between a list and a tuple?",
        "How do I iterate over a list?",
        "What are list comprehensions?",
        "Can you give me an example of a list comprehension?",
        "What are dictionaries in Python?",
        "How do I add items to a dictionary?",
        "What's the difference between a dictionary and a set?",
        "How do I handle exceptions in Python?",
        "What is a try-except block?",
        "Can you show me an example of exception handling?",
        "What are Python decorators?",
        "How do I create a simple decorator?",
    ]
    
    print("Running baseline (no compression)...")
    print("\n" + "="*70)
    print("  BASELINE RUN (No Compression)")
    print("="*70)
    
    console = Console()
    agent_baseline = Agent(api_key=api_key, model="gpt-4o-mini", system_prompt="You are a helpful Python tutor. Keep answers concise.", compression_enabled=False)
    baseline_tokens, _ = run_conversation(agent_baseline, questions, console)
    print(f"\n✓ Baseline complete: {len(baseline_tokens)} exchanges")
    
    print("\n\n" + "="*70)
    print("  COMPRESSED RUN (Compression Enabled)")
    print("="*70)
    
    agent_compressed = Agent(api_key=api_key, model="gpt-4o-mini", system_prompt="You are a helpful Python tutor. Keep answers concise.", compression_enabled=True)
    compressed_tokens, compression_active = run_conversation(agent_compressed, questions, console)
    print(f"\n✓ Compression complete: {len(compressed_tokens)} exchanges")
    
    # Calculate savings (only when compression was actually active)
    savings_percentages = []
    for i in range(len(baseline_tokens)):
        if i < len(compressed_tokens) and compression_active[i]:
            baseline = baseline_tokens[i]
            compressed = compressed_tokens[i]
            savings = ((baseline - compressed) / baseline * 100) if baseline > 0 else 0
            savings_percentages.append(savings)
        else:
            savings_percentages.append(0)  # No compression active
    
    # Display results
    print_comparison_graph(baseline_tokens, compressed_tokens)
    print_savings_graph(savings_percentages)
    print_cost_comparison(baseline_tokens, compressed_tokens)
    print_summary_table(baseline_tokens, compressed_tokens)


def test_scenario_long():
    """Scenario 2: Long conversation (30-40 exchanges)"""
    print_separator("SCENARIO 2: Long Conversation (30-40 exchanges)")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not set")
        return
    
    # Questions for long conversation
    questions = [
        "What is machine learning?",
        "What's the difference between supervised and unsupervised learning?",
        "What is a neural network?",
        "How does backpropagation work?",
        "What is gradient descent?",
        "What are activation functions?",
        "What is the difference between sigmoid and ReLU?",
        "What is overfitting?",
        "How can I prevent overfitting?",
        "What is regularization?",
        "What's the difference between L1 and L2 regularization?",
        "What is cross-validation?",
        "What is a confusion matrix?",
        "What are precision and recall?",
        "What is the F1 score?",
        "What is a decision tree?",
        "How does a random forest work?",
        "What is ensemble learning?",
        "What is boosting?",
        "What's the difference between bagging and boosting?",
        "What is a support vector machine?",
        "What is the kernel trick?",
        "What is dimensionality reduction?",
        "What is PCA?",
        "What is feature engineering?",
        "What is one-hot encoding?",
        "What is normalization?",
        "What's the difference between normalization and standardization?",
        "What is a learning rate?",
        "How do I choose a learning rate?",
    ]
    
    print("Running baseline (no compression)...")
    print("\n" + "="*70)
    print("  BASELINE RUN (No Compression)")
    print("="*70)
    
    console = Console()
    agent_baseline = Agent(api_key=api_key, model="gpt-4o-mini", system_prompt="You are a helpful ML tutor. Keep answers concise.", compression_enabled=False)
    baseline_tokens, _ = run_conversation(agent_baseline, questions, console)
    print(f"\n✓ Baseline complete: {len(baseline_tokens)} exchanges")
    
    print("\n\n" + "="*70)
    print("  COMPRESSED RUN (Compression Enabled)")
    print("="*70)
    
    agent_compressed = Agent(api_key=api_key, model="gpt-4o-mini", system_prompt="You are a helpful ML tutor. Keep answers concise.", compression_enabled=True)
    compressed_tokens, compression_active = run_conversation(agent_compressed, questions, console)
    print(f"\n✓ Compression complete: {len(compressed_tokens)} exchanges")
    
    # Calculate savings (only when compression was actually active)
    savings_percentages = []
    for i in range(len(baseline_tokens)):
        if i < len(compressed_tokens) and compression_active[i]:
            baseline = baseline_tokens[i]
            compressed = compressed_tokens[i]
            savings = ((baseline - compressed) / baseline * 100) if baseline > 0 else 0
            savings_percentages.append(savings)
        else:
            savings_percentages.append(0)  # No compression active
    
    # Display results
    print_comparison_graph(baseline_tokens, compressed_tokens)
    print_savings_graph(savings_percentages)
    print_cost_comparison(baseline_tokens, compressed_tokens)
    print_summary_table(baseline_tokens, compressed_tokens)


def main():
    """Run all comparison scenarios"""
    print("\n" + "="*70)
    print("  CONTEXT COMPRESSION COMPARISON TEST SUITE")
    print("="*70)
    print("\nThis will run conversations with and without compression.")
    print("Each scenario runs twice to compare token usage and costs.\n")
    
    input("Press Enter to start Scenario 1 (Medium conversation)...")
    test_scenario_medium()
    
    # print("\n\n")
    # input("Press Enter to start Scenario 2 (Long conversation)...")
    # test_scenario_long()
    
    print("\n\n" + "="*70)
    print("  ALL SCENARIOS COMPLETE")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
