## AI Implementation Prompt: Task State Machine for AI Agent

### Context
You are working with an AI conversational agent built in Python that uses OpenAI's API. The agent currently supports multiple conversation management strategies (sliding window, sticky facts,
branching) and maintains conversation history in SQLite. The main components are:

- Agent class (src/aiadvent/agent/agent.py) - Core agent logic
- HistoryManager class (src/aiadvent/agent/history.py) - Database persistence
- CLI module (src/aiadvent/agent/cli.py) - User interface

### Requirement
Implement a Task State Machine that tracks the agent's current state during task execution. The state machine should formalize task progression through distinct phases.

### State Machine Specification

States (phases):
1. planning - Agent is analyzing requirements and creating a plan
2. execution - Agent is actively executing the plan
3. validation - Agent is verifying results
4. done - Task completed

State Properties:
- Current phase (planning/execution/validation/done)
- Current step number within the phase
- Expected action description

Required Functionality:
1. Track state transitions automatically as the agent processes tasks
2. Support pausing at any phase and resuming without re-explaining previous steps
3. Display current state to the user (e.g., "[Planning: Step 2/5] Analyzing requirements...")
4. Persist state to database so it survives session restarts
5. Allow manual state inspection via CLI command (e.g., /state)

### Implementation Requirements

Minimal code approach:
- Create a new TaskStateMachine class in src/aiadvent/agent/task_state.py
- Add state tracking fields: phase, step, total_steps, action_description
- Add database table task_states to HistoryManager with columns: session_id, phase, step, total_steps, action_description, updated_at
- Integrate state machine into Agent class
- Add /state command to CLI to display current state
- Add state indicator to CLI prompt (e.g., [Planning 2/5] >)

State Transitions:
- Detect phase transitions by analyzing agent responses for keywords (e.g., "let me plan", "executing", "validating", "completed")
- Update state after each agent response
- Save state to database after each update

Testing:
- Create tests/test_task_state.py with scenarios:
  - Test state progression through all phases
  - Test pause and resume without repetition
  - Test state persistence across session restarts

### Expected Outcome
An agent that maintains formalized task state, displays progress clearly, and can pause/resume tasks efficiently without losing context or repeating explanations.