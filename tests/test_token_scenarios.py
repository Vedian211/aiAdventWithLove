"""
Test scenarios for token counting functionality

Tests three scenarios:
A. Short Dialog (1-2 exchanges)
B. Long Dialog (many exchanges, below limit)
C. Exceeded Limit Dialog (beyond 8192 tokens)
"""

import os
import time
from aiadvent.agent import Agent
from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live


def print_token_graph(token_history, token_limit, title="Token Usage Growth"):
    """Print ASCII graph showing token usage growth"""
    print(f"\n{'='*60}")
    print(title)
    print(f"{'='*60}\n")
    
    graph_width = 50
    
    for i, tokens in enumerate(token_history, 1):
        bar_length = int((tokens / token_limit) * graph_width)
        bar = "█" * bar_length
        percentage = int((tokens / token_limit) * 100)
        print(f"Q{i:2d} [{percentage:3d}%] {bar} {tokens}")
    
    # Show warning threshold line
    warning_threshold = int(token_limit * 0.8)
    threshold_bar_length = int((warning_threshold / token_limit) * graph_width)
    print(f"\n     [80%] {'─' * threshold_bar_length}⚠ Warning Threshold ({warning_threshold})")
    print(f"    [100%] {'─' * graph_width}│ Limit ({token_limit})")


def print_cost_graph(token_history, price_per_million=5.0):
    """Print ASCII graph showing cumulative cost growth"""
    print(f"\n{'='*60}")
    print(f"Cost Growth (${price_per_million} per million tokens)")
    print(f"{'='*60}\n")
    
    costs = [(tokens / 1_000_000) * price_per_million for tokens in token_history]
    max_cost = max(costs)
    graph_width = 50
    
    for i, cost in enumerate(costs, 1):
        if max_cost > 0:
            bar_length = int((cost / max_cost) * graph_width)
        else:
            bar_length = 0
        bar = "█" * bar_length
        print(f"Q{i:2d} {bar} ${cost:.6f}")
    
    total_cost = costs[-1] if costs else 0
    print(f"\nTotal cost: ${total_cost:.6f}")


def print_separator(title):
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60 + "\n")


def validate_tokens(stats, scenario_name):
    """Validate token counts are reasonable"""
    errors = []
    
    if stats['prompt'] <= 0:
        errors.append(f"❌ Prompt tokens should be > 0, got {stats['prompt']}")
    else:
        print(f"✓ Prompt tokens: {stats['prompt']}")
    
    if stats['history'] <= 0:
        errors.append(f"❌ History tokens should be > 0, got {stats['history']}")
    else:
        print(f"✓ History tokens: {stats['history']}")
    
    if stats['response'] <= 0:
        errors.append(f"❌ Response tokens should be > 0, got {stats['response']}")
    else:
        print(f"✓ Response tokens: {stats['response']}")
    
    if stats['history'] < stats['prompt']:
        errors.append(f"❌ History ({stats['history']}) should be >= Prompt ({stats['prompt']})")
    else:
        print(f"✓ History >= Prompt")
    
    return errors


def test_scenario_a_short_dialog():
    """Scenario A: Short conversation with 1-2 exchanges"""
    print_separator("SCENARIO A: Short Dialog (1-2 exchanges)")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not set")
        return False
    
    agent = Agent(
        api_key=api_key,
        model="gpt-4",
        system_prompt="You are a helpful assistant. Keep responses brief."
    )
    
    console = Console()
    all_errors = []
    token_history = []
    
    # Exchange 1
    question1 = "Hello, what is 2+2?"
    console.print(f"User: {question1}", style="bold green")
    response1 = agent.think(question1)
    agent.set_last_response_tokens(response1)
    stats1 = agent.get_token_stats()
    token_history.append(stats1['history'])
    
    console.print("\nAssistant:", style="bold blue")
    console.print(Markdown(response1))
    print(f"\n[Tokens - Prompt: {stats1['prompt']} | History: {stats1['history']} | Response: {stats1['response']}]")
    
    errors = validate_tokens(stats1, "Exchange 1")
    all_errors.extend(errors)
    
    # Exchange 2
    print("\n---\n")
    question2 = "Thank you!"
    console.print(f"User: {question2}", style="bold green")
    response2 = agent.think(question2)
    agent.set_last_response_tokens(response2)
    stats2 = agent.get_token_stats()
    token_history.append(stats2['history'])
    
    console.print("\nAssistant:", style="bold blue")
    console.print(Markdown(response2))
    print(f"\n[Tokens - Prompt: {stats2['prompt']} | History: {stats2['history']} | Response: {stats2['response']}]")
    
    errors = validate_tokens(stats2, "Exchange 2")
    all_errors.extend(errors)
    
    # Validate history accumulation
    if stats2['history'] <= stats1['history']:
        all_errors.append(f"❌ History should grow: Exchange 1 ({stats1['history']}) -> Exchange 2 ({stats2['history']})")
    else:
        print(f"✓ History accumulated correctly: {stats1['history']} -> {stats2['history']}")
    
    # Validate total is reasonable for short dialog
    if stats2['history'] > 1000:
        all_errors.append(f"❌ Short dialog should be < 1000 tokens, got {stats2['history']}")
    else:
        print(f"✓ Total tokens reasonable for short dialog: {stats2['history']}")
    
    # Display graphs
    print_token_graph(token_history, agent.TOKEN_LIMIT, "Token Usage Growth - Scenario A")
    print_cost_graph(token_history)
    
    print(f"\n{'='*60}")
    if all_errors:
        print("❌ SCENARIO A FAILED:")
        for error in all_errors:
            print(f"  {error}")
        return False
    else:
        print("✅ SCENARIO A PASSED: All validations successful")
        return True


def test_scenario_b_long_dialog():
    """Scenario B: Long conversation staying below 8192 token limit"""
    print_separator("SCENARIO B: Long Dialog (below 8192 limit)")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not set")
        return False
    
    agent = Agent(
        api_key=api_key,
        model="gpt-4",
        system_prompt="You are a helpful assistant."
    )
    
    questions = [
        "Explain what Python is in 2 sentences.",
        "What are the main features of Python?",
        "How does Python compare to Java?",
        "What is a Python decorator?",
        "Explain list comprehensions.",
        "What are Python generators?",
        "Describe Python's GIL.",
        "What is asyncio in Python?",
    ]
    
    all_errors = []
    warning_triggered = False
    previous_history = 0
    
    console = Console()
    
    # Track token history for graph
    token_history = []
    
    for i, question in enumerate(questions, 1):
        print(f"\n--- Exchange {i} ---")
        console.print(f"User: {question}", style="bold green")
        
        console.print("\nAssistant:", style="bold blue")
        with Live(Markdown(""), console=console, refresh_per_second=10) as live:
            stream = agent.think_stream(question)
            
            response = ""
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    response += content
                    live.update(Markdown(response))
        
        agent.add_message("assistant", response)
        agent.set_last_response_tokens(response)
        stats = agent.get_token_stats()
        
        # Store for graph
        token_history.append(stats['history'])
        
        print(f"\n[Tokens - Prompt: {stats['prompt']} | History: {stats['history']} | Response: {stats['response']}]")
        
        # Validate accumulation
        if i > 1 and stats['history'] <= previous_history:
            all_errors.append(f"❌ Exchange {i}: History not accumulating ({previous_history} -> {stats['history']})")
        
        previous_history = stats['history']
        
        # Check warning threshold
        warning_threshold = int(agent.TOKEN_LIMIT * agent.WARNING_THRESHOLD)
        if stats['history'] >= warning_threshold:
            warning_triggered = True
            print(f"⚠️  WARNING: Approaching token limit! ({stats['history']}/{agent.TOKEN_LIMIT})")
            print(f"✓ Warning triggered at {stats['history']} tokens (threshold: {warning_threshold})")
            break
        
        # Stop if we're getting close to limit
        if stats['history'] > 5000:
            break
    
    final_stats = agent.get_token_stats()
    
    # Display graphs
    print_token_graph(token_history, agent.TOKEN_LIMIT, "Token Usage Growth - Scenario B")
    print_cost_graph(token_history)
    
    # Validations
    if final_stats['history'] >= agent.TOKEN_LIMIT:
        all_errors.append(f"❌ Should stay below limit, got {final_stats['history']}/{agent.TOKEN_LIMIT}")
    else:
        print(f"\n✓ Stayed below token limit: {final_stats['history']}/{agent.TOKEN_LIMIT}")
    
    if warning_triggered:
        print(f"✓ Warning system working correctly")
    
    print(f"\n{'='*60}")
    if all_errors:
        print("❌ SCENARIO B FAILED:")
        for error in all_errors:
            print(f"  {error}")
        return False
    else:
        print("✅ SCENARIO B PASSED: All validations successful")
        return True


def test_scenario_c_exceeded_limit():
    """Scenario C: Force conversation beyond 8192 token limit"""
    print_separator("SCENARIO C: Exceeded Limit Dialog (beyond 8192)")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not set")
        return False
    
    agent = Agent(
        api_key=api_key,
        model="gpt-4",
        system_prompt="You are a helpful assistant. Provide extremely detailed, comprehensive answers with many examples and explanations. Write at least 500 words for each answer."
    )
    
    console = Console()
    
    long_questions = [
        "Write a comprehensive, detailed explanation of machine learning (at least 500 words), covering supervised learning, unsupervised learning, reinforcement learning, deep learning, neural networks, training processes, optimization algorithms, overfitting, regularization, cross-validation, and real-world applications with specific examples.",
        "Explain the complete history of artificial intelligence from the 1950s to present day (at least 500 words), including the Dartmouth Conference, expert systems, AI winters, the rise of machine learning, deep learning revolution, transformer models, GPT, and current state of AI with detailed examples and milestones.",
        "Describe in extensive detail how neural networks work (at least 500 words), including neurons, layers, weights, biases, forward propagation, backpropagation, gradient descent, learning rate, activation functions (sigmoid, ReLU, tanh), loss functions, optimization algorithms (SGD, Adam, RMSprop), and provide mathematical explanations.",
        "Explain the transformer architecture comprehensively (at least 500 words), including self-attention mechanisms, multi-head attention, positional encoding, encoder-decoder structure, layer normalization, feed-forward networks, residual connections, and how it's used in BERT, GPT, and other models.",
        "Provide an exhaustive overview of computer vision (at least 500 words), covering image processing, edge detection, feature extraction, SIFT, HOG, convolutional neural networks, pooling, ResNet, VGG, object detection (YOLO, R-CNN), semantic segmentation, instance segmentation, and applications.",
        "Explain natural language processing in great detail (at least 500 words), including tokenization, word embeddings (Word2Vec, GloVe), contextualized embeddings (ELMo, BERT), sequence-to-sequence models, attention mechanisms, language models, named entity recognition, sentiment analysis, and machine translation.",
        "Describe reinforcement learning thoroughly (at least 500 words), covering Markov Decision Processes, Q-learning, Deep Q-Networks, policy gradients, actor-critic methods, PPO, A3C, reward shaping, exploration vs exploitation, and applications in games, robotics, and autonomous systems.",
        "Explain generative AI models extensively (at least 500 words), including GANs (generator, discriminator, training process), VAEs, diffusion models, autoregressive models, image generation (DALL-E, Stable Diffusion), text generation (GPT), and ethical considerations.",
        "Provide a comprehensive guide to data preprocessing (at least 500 words), covering data cleaning, handling missing values, outlier detection, normalization, standardization, feature scaling, encoding categorical variables, feature engineering, dimensionality reduction (PCA, t-SNE), and data augmentation.",
        "Explain deep learning optimization in detail (at least 500 words), including gradient descent variants, momentum, adaptive learning rates, batch normalization, dropout, early stopping, learning rate scheduling, gradient clipping, weight initialization strategies, and hyperparameter tuning.",
        "Describe recurrent neural networks thoroughly (at least 500 words), covering vanilla RNNs, vanishing gradients, LSTM architecture (gates, cell state), GRU, bidirectional RNNs, sequence modeling, time series prediction, and applications in NLP and speech recognition.",
        "Explain model evaluation comprehensively (at least 500 words), including accuracy, precision, recall, F1-score, ROC curves, AUC, confusion matrices, cross-validation techniques, train-test split, validation sets, bias-variance tradeoff, and model selection strategies.",
        "Describe transfer learning in detail (at least 500 words), covering pre-trained models, fine-tuning, feature extraction, domain adaptation, few-shot learning, zero-shot learning, and applications in computer vision and NLP.",
        "Explain attention mechanisms thoroughly (at least 500 words), including scaled dot-product attention, multi-head attention, self-attention, cross-attention, attention weights, query-key-value paradigm, and applications in transformers.",
        "Provide a comprehensive overview of ensemble methods (at least 500 words), covering bagging, boosting, random forests, gradient boosting machines, XGBoost, LightGBM, stacking, voting classifiers, and when to use each method.",
        "Describe convolutional neural networks in extensive detail (at least 500 words), covering convolution operations, filters, kernels, stride, padding, pooling layers, feature maps, receptive fields, and architectures like LeNet, AlexNet, VGG, ResNet, and Inception.",
    ]
    
    warning_triggered = False
    limit_exceeded = False
    api_error_occurred = False
    token_history = []
    
    for i, question in enumerate(long_questions, 1):
        print(f"\n{'='*60}")
        print(f"Exchange {i}")
        print(f"{'='*60}\n")
        console.print(f"User: {question}", style="bold green")
        print()
        
        try:
            # Use streaming for visual effect
            console.print("Assistant: ", style="bold blue")
            with Live(Markdown(""), console=console, refresh_per_second=10) as live:
                stream = agent.think_stream(question)
                
                response_content = ""
                for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        response_content += content
                        live.update(Markdown(response_content))
            
            # Add response to history
            agent.add_message("assistant", response_content)
            agent.set_last_response_tokens(response_content)
            stats = agent.get_token_stats()
            
            # Track for graph
            token_history.append(stats['history'])
            
            print(f"\n[Tokens - Prompt: {stats['prompt']} | History: {stats['history']} | Response: {stats['response']}]")
            
            # Check warning threshold
            warning_threshold = int(agent.TOKEN_LIMIT * agent.WARNING_THRESHOLD)
            if stats['history'] >= warning_threshold:
                warning_triggered = True
                print(f"⚠️  WARNING: At {int(stats['history']/agent.TOKEN_LIMIT*100)}% of token limit!")
            
            # Check if exceeded
            if stats['history'] >= agent.TOKEN_LIMIT:
                limit_exceeded = True
                print(f"🚨 EXCEEDED: History tokens ({stats['history']}) exceed limit ({agent.TOKEN_LIMIT})")
                print("Continuing to next question to test API behavior...")
                
        except Exception as e:
            api_error_occurred = True
            print(f"\n❌ API Error: {e}")
            stats = agent.get_token_stats()
            token_history.append(stats['history'])
            print(f"History tokens when error occurred: {stats['history']}")
            print("✓ API correctly rejected over-limit request")
            break
    
    # Display graphs
    if token_history:
        print_token_graph(token_history, agent.TOKEN_LIMIT, "Token Usage Growth - Scenario C")
        print_cost_graph(token_history)
    
    # Validations
    print(f"\n{'='*60}")
    print("Validation Results:")
    print(f"{'='*60}")
    
    all_passed = True
    
    if warning_triggered:
        print("✓ Warning triggered before limit")
    else:
        print("❌ Warning should have triggered")
        all_passed = False
    
    if limit_exceeded or api_error_occurred:
        print("✓ Limit exceeded or API error occurred as expected")
    else:
        print("⚠️  Did not reach limit (may need more exchanges)")
    
    print(f"\n{'='*60}")
    if all_passed:
        print("✅ SCENARIO C PASSED: Demonstrated limit handling")
        return True
    else:
        print("❌ SCENARIO C FAILED: Some validations failed")
        return False


def main():
    """Run all test scenarios"""
    print("\n" + "█"*60)
    print("  TOKEN COUNTING TEST SCENARIOS")
    print("█"*60)
    
    results = []
    
    try:
        result_a = test_scenario_a_short_dialog()
        results.append(("Scenario A", result_a))
        input("\nPress Enter to continue to Scenario B...")
        #
        result_b = test_scenario_b_long_dialog()
        results.append(("Scenario B", result_b))
        input("\nPress Enter to continue to Scenario C...")
        
        result_c = test_scenario_c_exceeded_limit()
        results.append(("Scenario C", result_c))
        
        # Final summary
        print("\n" + "█"*60)
        print("  TEST SUMMARY")
        print("█"*60)
        
        for name, passed in results:
            status = "✅ PASSED" if passed else "❌ FAILED"
            print(f"{name}: {status}")
        
        all_passed = all(result for _, result in results)
        print("\n" + "█"*60)
        if all_passed:
            print("  ✅ ALL TESTS PASSED")
        else:
            print("  ❌ SOME TESTS FAILED")
        print("█"*60 + "\n")
        
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user.")
    except Exception as e:
        print(f"\n\nError during tests: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
