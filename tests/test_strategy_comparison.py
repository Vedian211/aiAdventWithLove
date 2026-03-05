"""
Context Management Strategy Comparison Test

Compares three strategies for PRD gathering (10-15 messages):
- Strategy A: Sliding Window (compression-based)
- Strategy B: Sticky Facts (key-value memory)
- Strategy C: Branching (checkpoint + explore alternatives)
"""

import os
import json
import time
from aiadvent.agent import Agent
from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live
from rich.spinner import Spinner


PRD_QUESTIONS = [
    "I need to build a task management app",
    "It should support teams of 5-10 people",
    "Users should be able to create tasks, assign them, and track progress",
    "We need both web and mobile versions",
    "What about real-time updates when someone changes a task?",
    "Yes, real-time is important. Also need notifications",
    "For tech stack, we're thinking React for web. What about mobile?",
    "React Native sounds good. What about the backend?",
    "We need it to scale to at least 1000 teams",
    "Security is critical - we'll have sensitive project data",
    "Can you summarize the key requirements so far?",
]

# Branching point 1: Architecture
ARCHITECTURE_CHECKPOINT = "Actually, for architecture - should we use microservices or monolith?"
ARCHITECTURE_BRANCHES = {
    "microservices": [
        "Let's explore microservices. What services would we need?",
        "How would these services communicate?",
        "What about deployment complexity?"
    ],
    "monolith": [
        "Let's explore monolith. How would we structure it?",
        "What are the benefits for our scale?",
        "When should we consider splitting it?"
    ]
}

# Branching point 2: Database
DATABASE_CHECKPOINT = "What about the database? SQL or NoSQL?"
DATABASE_BRANCHES = {
    "sql": [
        "Let's go with SQL. Which one - PostgreSQL or MySQL?",
        "How should we design the schema for tasks and teams?",
        "What about handling relationships between entities?"
    ],
    "nosql": [
        "Let's go with NoSQL. MongoDB or DynamoDB?",
        "How should we structure documents for tasks?",
        "How do we handle relationships in NoSQL?"
    ]
}

FINAL_QUESTION = "Can you give me a final technical specification summary?"


def ask_with_thinking(agent, question, console):
    """Ask question with thinking animation, then return response"""
    spinner = Spinner("dots", text="Thinking...")
    
    with Live(spinner, console=console, refresh_per_second=10) as live:
        response = agent.think(question)
        time.sleep(0.1)  # Brief pause before showing response
        live.update(Markdown(response))
    
    return response


def run_strategy(strategy_name, strategy_type, questions, console):
    """Run conversation with specific strategy"""
    api_key = os.getenv("OPENAI_API_KEY")
    
    system_prompt = "You are a technical product analyst helping gather requirements for a PRD. Ask clarifying questions and track key decisions."
    
    compression_enabled = strategy_type == "sliding_window"
    
    agent = Agent(
        api_key=api_key,
        model="gpt-4o-mini",
        system_prompt=system_prompt,
        strategy=strategy_type,
        compression_enabled=compression_enabled
    )
    
    console.print(f"\n{'='*70}", style="bold blue")
    console.print(f"  {strategy_name}", style="bold blue")
    console.print(f"{'='*70}\n", style="bold blue")
    
    responses = []
    token_usage = []
    
    # Process initial questions
    for i, question in enumerate(questions):
        console.print(f"\n[Q{i+1}] {question}", style="bold green")
        
        response = ask_with_thinking(agent, question, console)
        responses.append(response)
        print()  # Extra line after response
        
        stats = agent.get_token_stats()
        token_usage.append(stats['history'])
        
        # Show compression info for sliding window
        if strategy_type == "sliding_window" and "compression" in stats and stats["compression"]["original"] > 0:
            comp = stats["compression"]
            console.print(f"\n[Tokens: {stats['history']} | Compressed: {comp['original']}→{comp['compressed']} (saved {comp['ratio']:.0f}%)]", style="dim")
        # Show facts count for sticky facts
        elif strategy_type == "sticky_facts" and "sticky_facts" in stats:
            facts_count = stats["sticky_facts"]["total_facts"]
            console.print(f"\n[Tokens: {stats['history']} | Facts stored: {facts_count}]", style="dim")
        else:
            console.print(f"\n[Tokens: {stats['history']}]", style="dim")
    
    # Architecture questions
    console.print(f"\n[Q{len(responses)+1}] {ARCHITECTURE_CHECKPOINT}", style="bold green")
    response = ask_with_thinking(agent, ARCHITECTURE_CHECKPOINT, console)
    responses.append(response)
    print()
    
    if strategy_type == "branching":
        checkpoint_id = agent.branching_manager.create_checkpoint("Architecture Decision", agent.messages)
        console.print(f"\n[Checkpoint: {checkpoint_id}]", style="yellow")
        
        branch_id = agent.branching_manager.create_branch(checkpoint_id, "Microservices", agent.messages)
        agent.branching_manager.switch_branch(branch_id)
        console.print(f"[Branch: {branch_id} - Microservices]", style="yellow")
    
    # Hardcoded decision: use microservices
    selected_arch = "microservices"
    for q in ARCHITECTURE_BRANCHES[selected_arch]:
        console.print(f"\n[Q{len(responses)+1}] {q}", style="bold green")
        response = ask_with_thinking(agent, q, console)
        responses.append(response)
        print()
        
        stats = agent.get_token_stats()
        token_usage.append(stats['history'])
        
        if strategy_type == "sliding_window" and "compression" in stats and stats["compression"]["original"] > 0:
            comp = stats["compression"]
            console.print(f"\n[Tokens: {stats['history']} | Compressed: {comp['original']}→{comp['compressed']} (saved {comp['ratio']:.0f}%)]", style="dim")
        elif strategy_type == "sticky_facts" and "sticky_facts" in stats:
            facts_count = stats["sticky_facts"]["total_facts"]
            console.print(f"\n[Tokens: {stats['history']} | Facts stored: {facts_count}]", style="dim")
        else:
            console.print(f"\n[Tokens: {stats['history']}]", style="dim")
    
    if strategy_type == "branching":
        console.print(f"\n[User decision: Selected {selected_arch}]", style="cyan")
    
    # Database questions
    console.print(f"\n[Q{len(responses)+1}] {DATABASE_CHECKPOINT}", style="bold green")
    response = ask_with_thinking(agent, DATABASE_CHECKPOINT, console)
    responses.append(response)
    print()
    
    if strategy_type == "branching":
        db_checkpoint_id = agent.branching_manager.create_checkpoint("Database Decision", agent.messages)
        console.print(f"\n[Checkpoint: {db_checkpoint_id}]", style="yellow")
        
        sql_branch_id = agent.branching_manager.create_branch(db_checkpoint_id, "SQL", agent.messages)
        agent.branching_manager.switch_branch(sql_branch_id)
        console.print(f"[Branch: {sql_branch_id} - SQL]", style="yellow")
    
    # Hardcoded decision: use SQL
    selected_db = "sql"
    for q in DATABASE_BRANCHES[selected_db]:
        console.print(f"\n[Q{len(responses)+1}] {q}", style="bold green")
        response = ask_with_thinking(agent, q, console)
        responses.append(response)
        print()
        
        stats = agent.get_token_stats()
        token_usage.append(stats['history'])
        
        if strategy_type == "sliding_window" and "compression" in stats and stats["compression"]["original"] > 0:
            comp = stats["compression"]
            console.print(f"\n[Tokens: {stats['history']} | Compressed: {comp['original']}→{comp['compressed']} (saved {comp['ratio']:.0f}%)]", style="dim")
        elif strategy_type == "sticky_facts" and "sticky_facts" in stats:
            facts_count = stats["sticky_facts"]["total_facts"]
            console.print(f"\n[Tokens: {stats['history']} | Facts stored: {facts_count}]", style="dim")
        else:
            console.print(f"\n[Tokens: {stats['history']}]", style="dim")
    
    if strategy_type == "branching":
        console.print(f"\n[User decision: Selected {selected_db}]", style="cyan")
    
    # Final summary
    console.print(f"\n[Q{len(responses)+1}] {FINAL_QUESTION}", style="bold green")
    response = ask_with_thinking(agent, FINAL_QUESTION, console)
    responses.append(response)
    print()
    
    stats = agent.get_token_stats()
    token_usage.append(stats['history'])
    
    if strategy_type == "sliding_window" and "compression" in stats and stats["compression"]["original"] > 0:
        comp = stats["compression"]
        console.print(f"\n[Tokens: {stats['history']} | Compressed: {comp['original']}→{comp['compressed']} (saved {comp['ratio']:.0f}%)]", style="dim")
    elif strategy_type == "sticky_facts" and "sticky_facts" in stats:
        facts_count = stats["sticky_facts"]["total_facts"]
        console.print(f"\n[Tokens: {stats['history']} | Facts stored: {facts_count}]", style="dim")
    else:
        console.print(f"\n[Tokens: {stats['history']}]", style="dim")
    
    if strategy_type == "branching":
        console.print(f"\n[Final path: {selected_arch} + {selected_db}]", style="cyan")
    
    # Print facts at end for sticky facts strategy
    if strategy_type == "sticky_facts" and agent.sticky_facts_manager:
        console.print(f"\n{'='*70}", style="bold yellow")
        console.print("  EXTRACTED FACTS", style="bold yellow")
        console.print(f"{'='*70}\n", style="bold yellow")
        
        console.print(json.dumps(agent.sticky_facts_manager.facts, indent=2), style="yellow")
    
    return {
        "responses": responses,
        "tokens": token_usage,
        "agent": agent
    }


def analyze_quality(responses):
    """Analyze response quality with quick win metrics"""
    final_summary = responses[-1]
    
    # 1. Context Retention Score - key facts from early questions
    key_facts = {
        "team size": ["5-10", "team"],
        "real-time": ["real-time", "realtime"],
        "notifications": ["notification"],
        "react": ["react"],
        "mobile": ["mobile"],
        "scale": ["1000", "scale"],
        "security": ["security", "secure"],
        "microservices": ["microservice"],
        "sql": ["sql", "postgres", "mysql"]
    }
    
    facts_retained = 0
    fact_details = {}
    for fact_name, keywords in key_facts.items():
        found = any(kw.lower() in final_summary.lower() for kw in keywords)
        fact_details[fact_name] = found
        if found:
            facts_retained += 1
    
    retention_score = (facts_retained / len(key_facts)) * 100
    
    # 2. Completeness Score - required PRD sections
    required_sections = {
        "goal": ["task management", "app", "application"],
        "features": ["task", "assign", "track", "progress"],
        "tech_stack": ["react", "native", "backend"],
        "scale": ["scale", "1000", "team"],
        "security": ["security", "secure"],
        "architecture": ["microservice", "monolith", "architecture"],
        "database": ["database", "sql", "nosql", "postgres", "mysql"]
    }
    
    sections_covered = 0
    section_details = {}
    for section, keywords in required_sections.items():
        found = any(kw.lower() in final_summary.lower() for kw in keywords)
        section_details[section] = found
        if found:
            sections_covered += 1
    
    completeness_score = (sections_covered / len(required_sections)) * 100
    
    # 3. Specificity Score - concrete vs generic terms
    specific_terms = ["react native", "postgres", "mysql", "microservice", "websocket", "jwt", "api", "rest", "graphql"]
    generic_terms = ["database", "backend", "frontend", "server", "client"]
    
    specific_count = sum(1 for term in specific_terms if term.lower() in final_summary.lower())
    generic_count = sum(1 for term in generic_terms if term.lower() in final_summary.lower())
    
    specificity_score = (specific_count / (specific_count + generic_count) * 100) if (specific_count + generic_count) > 0 else 0
    
    return {
        "retention_score": retention_score,
        "retention_details": fact_details,
        "completeness_score": completeness_score,
        "completeness_details": section_details,
        "specificity_score": specificity_score,
        "specific_terms": specific_count,
        "generic_terms": generic_count,
        "summary_length": len(final_summary)
    }


def print_comparison_report(results):
    """Print structured comparison report"""
    print("\n" + "="*70)
    print("  COMPARISON REPORT: Context Management Strategies")
    print("="*70)
    
    print("\n## 1. Context Retention Score (Key Facts in Final Summary)\n")
    print(f"{'Strategy':<25} {'Score':<10} {'Facts Retained'}")
    print("-" * 70)
    for name, data in results.items():
        quality = data["quality"]
        score = quality["retention_score"]
        retained = sum(1 for v in quality["retention_details"].values() if v)
        total = len(quality["retention_details"])
        print(f"{name:<25} {score:>5.1f}%     {retained}/{total}")
    
    print("\n## 2. Completeness Score (PRD Sections Covered)\n")
    print(f"{'Strategy':<25} {'Score':<10} {'Sections Covered'}")
    print("-" * 70)
    for name, data in results.items():
        quality = data["quality"]
        score = quality["completeness_score"]
        covered = sum(1 for v in quality["completeness_details"].values() if v)
        total = len(quality["completeness_details"])
        print(f"{name:<25} {score:>5.1f}%     {covered}/{total}")
    
    print("\n## 3. Specificity Score (Concrete vs Generic Terms)\n")
    print(f"{'Strategy':<25} {'Score':<10} {'Specific':<12} {'Generic'}")
    print("-" * 70)
    for name, data in results.items():
        quality = data["quality"]
        score = quality["specificity_score"]
        specific = quality["specific_terms"]
        generic = quality["generic_terms"]
        print(f"{name:<25} {score:>5.1f}%     {specific:<12} {generic}")
    
    print("\n## 4. Token Usage Efficiency\n")
    print(f"{'Strategy':<25} {'Total Tokens':<15} {'Avg/Exchange'}")
    print("-" * 70)
    for name, data in results.items():
        total = sum(data["tokens"])
        avg = total / len(data["tokens"]) if data["tokens"] else 0
        print(f"{name:<25} {total:<15} {avg:.1f}")
    
    print("\n## 5. Detailed Fact Retention\n")
    # Get all fact names
    fact_names = list(next(iter(results.values()))["quality"]["retention_details"].keys())
    print(f"{'Fact':<20} ", end="")
    for name in results.keys():
        short_name = name.split("(")[1].rstrip(")")
        print(f"{short_name:<15}", end="")
    print()
    print("-" * 70)
    
    for fact in fact_names:
        print(f"{fact:<20} ", end="")
        for name, data in results.items():
            retained = data["quality"]["retention_details"][fact]
            symbol = "✓" if retained else "✗"
            print(f"{symbol:<15}", end="")
        print()
    
    print("\n## 6. PRD Section Coverage\n")
    section_names = list(next(iter(results.values()))["quality"]["completeness_details"].keys())
    print(f"{'Section':<20} ", end="")
    for name in results.keys():
        short_name = name.split("(")[1].rstrip(")")
        print(f"{short_name:<15}", end="")
    print()
    print("-" * 70)
    
    for section in section_names:
        print(f"{section:<20} ", end="")
        for name, data in results.items():
            covered = data["quality"]["completeness_details"][section]
            symbol = "✓" if covered else "✗"
            print(f"{symbol:<15}", end="")
        print()
    
    print("\n## 7. Overall Summary\n")
    print(f"{'Strategy':<25} {'Retention':<12} {'Complete':<12} {'Specific':<12} {'Tokens'}")
    print("-" * 70)
    for name, data in results.items():
        quality = data["quality"]
        retention = f"{quality['retention_score']:.0f}%"
        completeness = f"{quality['completeness_score']:.0f}%"
        specificity = f"{quality['specificity_score']:.0f}%"
        tokens = sum(data["tokens"])
        print(f"{name:<25} {retention:<12} {completeness:<12} {specificity:<12} {tokens}")
    
    print("\n" + "="*70)


def main():
    console = Console()
    
    console.print("\n" + "="*70, style="bold")
    console.print("  CONTEXT MANAGEMENT STRATEGY COMPARISON", style="bold")
    console.print("  Scenario: PRD Gathering (10-15 messages)", style="bold")
    console.print("="*70 + "\n", style="bold")
    
    results = {}
    
    # Strategy A: Sliding Window
    input("\nPress Enter to test Strategy A: Sliding Window...")
    results["Strategy A (Sliding)"] = run_strategy(
        "Strategy A: Sliding Window",
        "sliding_window",
        PRD_QUESTIONS,
        console
    )
    results["Strategy A (Sliding)"]["quality"] = analyze_quality(results["Strategy A (Sliding)"]["responses"])

    # Strategy B: Sticky Facts
    input("\nPress Enter to test Strategy B: Sticky Facts...")
    results["Strategy B (Sticky)"] = run_strategy(
        "Strategy B: Sticky Facts",
        "sticky_facts",
        PRD_QUESTIONS,
        console
    )
    results["Strategy B (Sticky)"]["quality"] = analyze_quality(results["Strategy B (Sticky)"]["responses"])
    
    # Strategy C: Branching
    input("\nPress Enter to test Strategy C: Branching...")
    results["Strategy C (Branch)"] = run_strategy(
        "Strategy C: Branching",
        "branching",
        PRD_QUESTIONS,
        console
    )
    results["Strategy C (Branch)"]["quality"] = analyze_quality(results["Strategy C (Branch)"]["responses"])
    
    # Print comparison report
    print_comparison_report(results)
    
    console.print("\n✓ All strategies tested. Review the comparison report above.", style="bold green")


if __name__ == "__main__":
    main()
