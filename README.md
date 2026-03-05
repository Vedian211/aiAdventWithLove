# AI Advent With Love

An advanced AI conversational agent with memory management, context optimization, and task tracking capabilities.

## Prerequisites

- Python 3.8+
- Virtual environment (recommended)

## Setup

### 1. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -e .
```

### 3. Set Environment Variables
```bash
export OPENAI_API_KEY='your-openai-api-key-here'
```

## Usage

The project provides three main CLI tools:

### Agent (Main Interactive CLI)
```bash
agent
```
Interactive conversational agent with session management, profiles, and memory strategies.

### Ask AI (Simple Query Tool)
```bash
ask-ai
```
Simple CLI for one-off questions with strategy selection:
- `-p1`: Simple API call
- `-p2`: Step-by-step solving
- `-p3`: Auto-prompt optimization
- `-p4`: Group of experts (parallel)
- `-t <value>`: Set temperature (0-2)

### Compare Models
```bash
compare-models
```
Compare responses from different AI models side-by-side.

## Features

### Session Management

The agent supports persistent conversation sessions:

- **Create Sessions**: Start new conversations with different contexts
- **Load Sessions**: Resume previous conversations with full history
- **Switch Sessions**: Move between different conversation threads
- **Delete Sessions**: Remove unwanted sessions

Sessions are stored in SQLite database (`src/aiadvent/history/conversations.db`) and persist across restarts.

### Memory Strategies

The agent supports multiple memory management strategies to handle context window limits:

#### 1. Sliding Window (Default)
- Keeps recent messages in full detail
- Optionally compresses older messages into summaries
- Toggle compression: `/compression [on|off|status]`

#### 2. Sticky Facts
- Extracts and preserves key facts from conversations
- Facts persist across context window resets
- View stored facts: `/facts`
- Categories: goal, constraints, preferences, decisions, agreements

#### 3. Branching
- Create checkpoints at any point in conversation
- Branch from checkpoints to explore alternatives
- Switch between branches without losing history
- Commands:
  - `/checkpoint <name>` - Create checkpoint
  - `/checkpoint` - List checkpoints
  - `/branch` - List branches
  - `/branch create <checkpoint_id>` - Create branch
  - `/branch switch <branch_id>` - Switch branch

#### 4. Memory Layers
- Combines long-term memory with sticky facts
- Automatically extracts user profile information
- Stores solutions and knowledge across sessions

### Token Counting
The agent tracks and displays token usage for each conversation exchange:

- **Prompt Tokens**: Tokens in the current user message
- **History Tokens**: Total tokens in the full conversation history (including system prompt, all messages)
- **Response Tokens**: Tokens in the AI model's response

After each response, you'll see:
```
[Tokens - Prompt: 15 | History: 342 | Response: 87]
```

### Model Configuration
- **Model**: gpt-4o-mini (5,000 token context window)
- **Warning Threshold**: 80% (4,000 tokens)
- When approaching the limit, use `/clear` to reset conversation history

### Available Commands

The agent CLI supports the following commands:

**General:**
- `/help` - Show help message with all commands
- `/exit` or `/quit` - Exit the session
- `/clear` - Clear conversation history
- `/state` - Show current task state
- `/sessions` - Switch to another session
- `/delete` - Delete a session

**Personalization:**
- `/profile create` - Create new user profile
- `/profile list` - List all profiles
- `/profile switch <id>` - Switch to different profile
- `/profile show` - Show current profile settings
- `/profile clear` - Delete all profiles

**Strategy-Specific Commands:**
- Sliding Window: `/compression [on|off|status]`
- Sticky Facts: `/facts`
- Branching: `/checkpoint`, `/branch` (see Branching section above)

### Testing Token Counting
Run test scenarios to validate token counting:
```bash
python tests/test_token_scenarios.py
```

**Test Scenarios:**
- **Scenario A**: Short dialog (1-2 exchanges) - validates basic counting
- **Scenario B**: Long dialog (below 8K limit) - validates accumulation and warnings
- **Scenario C**: Exceeded limit - demonstrates API behavior when limit exceeded

## User Personalization

The agent supports user profiles for personalized AI responses. Profiles allow you to customize:

- **Communication Style**: Formal, casual, or technical
- **Response Format**: Concise, detailed, or structured
- **Language**: English, Russian, or Ukrainian
- **Constraints**: Custom rules (e.g., no code examples, bullet points only)
- **Preferences**: Additional settings (e.g., emoji usage)
- **Domain Expertise**: Your areas of expertise for adjusted technical depth

### Profile Commands

Create and manage profiles using these commands:

```bash
/profile create       # Create a new profile interactively
/profile list         # List all available profiles
/profile switch <id>  # Switch to a different profile
/profile show         # Display current profile settings
```

### Profile Selection

When starting a session:
1. Select or create a conversation session
2. Choose a user profile (or skip to use default)
3. The profile automatically enhances the AI's system prompt

Profiles are linked to sessions and persist across restarts.

### Testing Personalization

Run test scenarios to validate personalization:
```bash
python tests/test_personalization.py
```

**Test Scenarios:**
- **Formal vs Casual**: Compare response styles
- **Language Preference**: Test Russian language responses
- **Constraints**: Verify no-code and bullet-point constraints
- **Persistence**: Validate profile loading across sessions

## Task State Machine

The agent includes a Task State Machine that tracks task execution progress through distinct phases:

### States
- **planning** - Agent is analyzing requirements and creating a plan
- **execution** - Agent is actively executing the plan
- **validation** - Agent is verifying results
- **done** - Task completed

### Features
- **Automatic Detection**: State transitions are detected from agent responses
- **Progress Display**: Current state shown in CLI prompt (e.g., `[Planning 2/5] >`)
- **Persistence**: State survives session restarts
- **Pause/Resume**: Continue tasks without re-explaining previous steps

### Commands

```bash
/state    # Display current task state
```

### State Display

The CLI prompt shows the current state:
```
[15%] [Execution 2/5] >    # With step count
[15%] [Validation] >       # Without step count
[15%] >                    # No active task
```

### Testing Task State

Run test scenarios to validate task state machine:
```bash
python tests/test_task_state.py
```

**Test Scenarios:**
- **State Progression**: Validates transitions through all phases
- **Persistence**: Verifies state survives session restarts
- **Pause and Resume**: Tests resuming without repetition
- **Display Format**: Validates state display formatting
