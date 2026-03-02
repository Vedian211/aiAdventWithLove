# Multi-Layer Memory Model Implementation Plan

## Architecture Overview

The multi-layer memory model introduces three distinct memory layers that work together to provide context-aware, persistent AI assistance:

```
┌─────────────────────────────────────────────────────────────┐
│                         Agent                                │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              MemoryManager (Orchestrator)             │  │
│  │  ┌─────────────┬──────────────┬──────────────────┐   │  │
│  │  │ Short-term  │   Working    │   Long-term      │   │  │
│  │  │   Memory    │    Memory    │    Memory        │   │  │
│  │  └─────────────┴──────────────┴──────────────────┘   │  │
│  └───────────────────────────────────────────────────────┘  │
│                            │                                 │
│                            ▼                                 │
│                    HistoryManager                            │
│                      (SQLite DB)                             │
└─────────────────────────────────────────────────────────────┘
```

### Memory Layers

**1. Short-term Memory (Current Dialog)**
- **Purpose**: Active conversation messages
- **Scope**: Current session only
- **Lifecycle**: Cleared on session end or context limit
- **Storage**: In-memory list (Agent.messages)
- **Existing Component**: Already implemented in Agent class

**2. Working Memory (Current Task Data)**
- **Purpose**: Task-relevant facts, decisions, constraints
- **Scope**: Current session, survives context compression
- **Lifecycle**: Persists until session ends or explicitly cleared
- **Storage**: SQLite (sticky_facts table) + in-memory cache
- **Existing Component**: StickyFactsManager (to be enhanced)

**3. Long-term Memory (Profile, Solutions, Knowledge)**
- **Purpose**: User preferences, learned patterns, successful solutions
- **Scope**: Cross-session, permanent
- **Lifecycle**: Accumulates over time, never auto-deleted
- **Storage**: SQLite (new tables)
- **New Component**: LongTermMemoryManager

---

## Database Schema Modifications

### New Tables

```sql
-- User profile and preferences
CREATE TABLE user_profile (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT UNIQUE NOT NULL,
    value TEXT NOT NULL,
    category TEXT NOT NULL,  -- 'preference', 'context', 'style'
    updated_at INTEGER NOT NULL
);

-- Learned solutions and patterns
CREATE TABLE learned_solutions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    problem_type TEXT NOT NULL,
    solution TEXT NOT NULL,
    context TEXT,
    success_count INTEGER DEFAULT 1,
    last_used INTEGER NOT NULL,
    created_at INTEGER NOT NULL
);

-- Knowledge base entries
CREATE TABLE knowledge_base (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL,
    content TEXT NOT NULL,
    source_session_id INTEGER,
    relevance_score REAL DEFAULT 1.0,
    created_at INTEGER NOT NULL,
    FOREIGN KEY (source_session_id) REFERENCES sessions(id) ON DELETE SET NULL
);

-- Indexes for efficient retrieval
CREATE INDEX idx_profile_category ON user_profile(category);
CREATE INDEX idx_solutions_type ON learned_solutions(problem_type);
CREATE INDEX idx_knowledge_topic ON knowledge_base(topic);
```

### Modified Tables

**sticky_facts** (Working Memory) - No changes needed, already suitable

---

## Component Breakdown

### 1. LongTermMemoryManager (New)
**File**: `src/aiadvent/agent/long_term_memory.py`

**Responsibilities**:
- Store/retrieve user profile data
- Manage learned solutions
- Build knowledge base from conversations
- Provide relevant context for new sessions

**Key Methods**:
```python
class LongTermMemoryManager:
    def __init__(self, history_manager: HistoryManager, client: OpenAI, model: str)
    
    # Profile management
    def save_profile_item(self, key: str, value: str, category: str)
    def get_profile(self, category: str = None) -> dict
    def update_profile_from_conversation(self, messages: list)
    
    # Solutions management
    def save_solution(self, problem_type: str, solution: str, context: str = None)
    def find_similar_solutions(self, problem_description: str, limit: int = 3) -> list
    def increment_solution_success(self, solution_id: int)
    
    # Knowledge base
    def add_knowledge(self, topic: str, content: str, session_id: int = None)
    def search_knowledge(self, query: str, limit: int = 5) -> list
    
    # Context building
    def get_relevant_context(self, current_input: str) -> str
```

### 2. MemoryManager (New - Orchestrator)
**File**: `src/aiadvent/agent/memory_manager.py`

**Responsibilities**:
- Coordinate all three memory layers
- Decide what data goes into which layer
- Build unified context for AI responses
- Handle memory lifecycle

**Key Methods**:
```python
class MemoryManager:
    def __init__(self, agent, long_term_memory: LongTermMemoryManager)
    
    def process_exchange(self, user_input: str, assistant_response: str)
    def build_context_for_prompt(self, user_input: str) -> list
    def classify_and_store(self, content: str, content_type: str)
    def get_memory_stats(self) -> dict
```

### 3. Agent (Modified)
**File**: `src/aiadvent/agent/agent.py`

**Changes**:
- Add `memory_manager` attribute
- Integrate memory context into `_prepare_messages()`
- Add memory-aware strategy option
- Expose memory management commands

**New Methods**:
```python
def enable_memory_layers(self, enabled: bool = True)
def get_memory_context(self, user_input: str) -> str
```

### 4. HistoryManager (Modified)
**File**: `src/aiadvent/agent/history.py`

**Changes**:
- Add schema initialization for new tables
- Add methods for long-term memory CRUD operations

**New Methods**:
```python
def save_profile_item(self, key: str, value: str, category: str)
def load_profile(self, category: str = None) -> dict
def save_solution(self, problem_type: str, solution: str, context: str = None) -> int
def load_solutions(self, problem_type: str = None) -> list
def save_knowledge(self, topic: str, content: str, session_id: int = None)
def search_knowledge(self, query: str, limit: int = 5) -> list
```

---

## Implementation Sequence

### Phase 1: Database Foundation
1. **Modify HistoryManager._init_db()** - Add new tables
2. **Add CRUD methods** - Implement basic storage/retrieval
3. **Test database operations** - Verify schema and operations

### Phase 2: Long-term Memory Manager
1. **Create LongTermMemoryManager class** - Basic structure
2. **Implement profile management** - Store/retrieve user data
3. **Implement solutions management** - Store/retrieve patterns
4. **Implement knowledge base** - Store/retrieve learned info
5. **Add context building** - Generate relevant context strings

### Phase 3: Memory Orchestration
1. **Create MemoryManager class** - Coordinate layers
2. **Implement classification logic** - Route data to correct layer
3. **Implement context building** - Combine all layers
4. **Add lifecycle management** - Handle memory transitions

### Phase 4: Agent Integration
1. **Add memory_manager to Agent** - Initialize in __init__
2. **Modify _prepare_messages()** - Inject memory context
3. **Add memory strategy** - New strategy option
4. **Update CLI commands** - Expose memory features

### Phase 5: Testing & Validation
1. **Unit tests** - Each memory layer independently
2. **Integration tests** - Memory flow across layers
3. **Scenario tests** - Real-world usage patterns
4. **Performance tests** - Token usage, retrieval speed

---

## Data Classification Logic

### Short-term Memory (Automatic)
- All user/assistant messages
- No classification needed
- Managed by existing Agent.messages

### Working Memory (Extracted)
**Triggers**: After each exchange
**Content**:
- Current task goal
- Active constraints
- Temporary decisions
- Session-specific context

**Classification Rules**:
- Contains task-specific keywords (goal, constraint, requirement)
- References current conversation
- Temporary relevance (this session only)

### Long-term Memory (Learned)
**Triggers**: 
- End of session (batch processing)
- Explicit user command (/remember, /learn)
- Pattern detection (repeated topics)

**Content**:
- User preferences (language, style, tools)
- Successful solutions (problem-solution pairs)
- Domain knowledge (facts, concepts)
- Interaction patterns

**Classification Rules**:
- User explicitly states preference ("I prefer...", "Always use...")
- Solution marked as successful
- Information requested to be remembered
- Topic appears across multiple sessions

---

## Retrieval Mechanisms

### Short-term Memory
**When**: Every response
**How**: Direct access to Agent.messages
**Limit**: Last N messages or token limit

### Working Memory
**When**: Every response (if strategy enabled)
**How**: StickyFactsManager.get_facts_prompt()
**Limit**: All current facts (typically < 500 tokens)

### Long-term Memory
**When**: Session start + relevant queries
**How**: 
1. Semantic search on user input
2. Retrieve top K relevant items
3. Format as context string
**Limit**: Top 3-5 items (< 1000 tokens)

### Combined Context Structure
```
[System Prompt]
[Long-term Context: Profile + Relevant Solutions + Knowledge]
[Working Memory: Current Task Facts]
[Short-term: Recent Messages]
[Current User Input]
```

---

## Migration Path

### Step 1: Non-breaking Addition
- Add new tables without modifying existing ones
- Add LongTermMemoryManager as optional component
- Add MemoryManager as optional orchestrator
- Existing strategies continue to work unchanged

### Step 2: Opt-in Strategy
- Add "memory_layers" strategy option
- Users explicitly enable: `--strategy memory_layers`
- Existing sessions unaffected

### Step 3: Gradual Enhancement
- Existing sticky_facts data remains valid
- Can migrate sticky_facts to working memory format
- No data loss or breaking changes

---

## Testing Approach

### Unit Tests

**test_long_term_memory.py**
```python
def test_profile_storage_retrieval()
def test_solution_storage_retrieval()
def test_knowledge_base_storage_retrieval()
def test_context_building()
```

**test_memory_manager.py**
```python
def test_data_classification()
def test_context_building_all_layers()
def test_memory_lifecycle()
```

### Integration Tests

**test_memory_integration.py**
```python
def test_memory_flow_across_layers()
def test_session_persistence()
def test_cross_session_learning()
```

### Scenario Tests

**test_memory_scenarios.py**
```python
def test_scenario_user_preference_learning()
def test_scenario_solution_reuse()
def test_scenario_knowledge_accumulation()
def test_scenario_context_compression_with_memory()
```

**Test Scenarios**:

**Scenario A: User Preference Learning**
1. Session 1: User states "I prefer Python over JavaScript"
2. Session 2: User asks for code example
3. Verify: Agent suggests Python without asking

**Scenario B: Solution Reuse**
1. Session 1: User solves a specific problem
2. Session 2: User encounters similar problem
3. Verify: Agent suggests previous solution

**Scenario C: Knowledge Accumulation**
1. Session 1: User teaches agent about domain concept
2. Session 2: User references concept
3. Verify: Agent recalls and applies knowledge

**Scenario D: Memory + Compression**
1. Long conversation exceeding token limit
2. Compression triggered
3. Verify: Working memory preserved, long-term memory accessible

---

## Example Usage Scenarios

### Scenario 1: First-time User
```python
agent = Agent(api_key=key, strategy="memory_layers")
agent.create_session("First Chat")

# User: "I'm a Python developer working on web APIs"
# System: Stores in long-term profile
# - preference: Python
# - context: web APIs

# User: "Help me design a REST endpoint"
# System: Uses profile context + provides Python examples
```

### Scenario 2: Returning User
```python
agent = Agent(api_key=key, strategy="memory_layers")
agent.create_session("API Design")

# System loads long-term memory:
# - Profile: Python developer, web APIs
# - Previous solutions: REST endpoint patterns

# User: "I need to add authentication"
# System: Suggests Python-based auth solutions
# References previous API design patterns
```

### Scenario 3: Task Continuation
```python
# Session 1
agent.respond("I'm building a user management system")
# Working memory: goal = "user management system"

agent.respond("It needs role-based access control")
# Working memory: constraint = "RBAC required"

# Session 2 (new session, same user)
# Long-term memory: Previous project = user management with RBAC
# System can reference previous work
```

---

## Token Budget Management

### Memory Layer Token Allocation
- **Short-term**: 2000-3000 tokens (recent messages)
- **Working memory**: 300-500 tokens (current facts)
- **Long-term context**: 500-1000 tokens (relevant history)
- **System prompt**: 200-500 tokens
- **Response buffer**: 1000-2000 tokens

**Total**: ~4000-7000 tokens (within 8K limit)

### Optimization Strategies
1. **Prioritize recent over old** in short-term
2. **Limit working memory** to 10-15 facts max
3. **Top-K retrieval** for long-term (3-5 items)
4. **Compress long-term context** using summaries
5. **Dynamic allocation** based on query complexity

---

## CLI Commands (Future Enhancement)

```bash
# Memory management
/memory status              # Show all memory layers
/memory clear working       # Clear working memory
/memory clear short         # Clear short-term (current /clear)
/remember <fact>            # Explicitly store in long-term
/forget <topic>             # Remove from long-term
/profile                    # Show user profile
/solutions                  # List learned solutions
/knowledge <topic>          # Search knowledge base
```

---

## Success Metrics

### Functional Metrics
- ✅ Data correctly classified into appropriate layers
- ✅ Memory persists across sessions
- ✅ Relevant context retrieved for queries
- ✅ No data loss during migrations

### Performance Metrics
- ✅ Context building < 100ms
- ✅ Memory retrieval < 50ms
- ✅ Token usage within limits
- ✅ Database queries < 10ms

### Quality Metrics
- ✅ Agent responses use relevant memory
- ✅ User preferences consistently applied
- ✅ Solutions reused appropriately
- ✅ Knowledge accumulates over time

---

## Implementation Checklist

### Phase 1: Database Foundation
- [ ] Add new tables to HistoryManager._init_db()
- [ ] Implement save_profile_item()
- [ ] Implement load_profile()
- [ ] Implement save_solution()
- [ ] Implement load_solutions()
- [ ] Implement save_knowledge()
- [ ] Implement search_knowledge()
- [ ] Write database unit tests

### Phase 2: Long-term Memory Manager
- [ ] Create long_term_memory.py
- [ ] Implement LongTermMemoryManager.__init__()
- [ ] Implement profile management methods
- [ ] Implement solutions management methods
- [ ] Implement knowledge base methods
- [ ] Implement get_relevant_context()
- [ ] Write LongTermMemoryManager unit tests

### Phase 3: Memory Orchestration
- [ ] Create memory_manager.py
- [ ] Implement MemoryManager.__init__()
- [ ] Implement process_exchange()
- [ ] Implement build_context_for_prompt()
- [ ] Implement classify_and_store()
- [ ] Implement get_memory_stats()
- [ ] Write MemoryManager unit tests

### Phase 4: Agent Integration
- [ ] Add memory_manager to Agent.__init__()
- [ ] Modify _prepare_messages() for memory strategy
- [ ] Add enable_memory_layers() method
- [ ] Add get_memory_context() method
- [ ] Update create_session() for memory initialization
- [ ] Update load_session() for memory restoration
- [ ] Write Agent integration tests

### Phase 5: Testing & Validation
- [ ] Write test_memory_integration.py
- [ ] Write test_memory_scenarios.py
- [ ] Test Scenario A: User Preference Learning
- [ ] Test Scenario B: Solution Reuse
- [ ] Test Scenario C: Knowledge Accumulation
- [ ] Test Scenario D: Memory + Compression
- [ ] Performance testing
- [ ] Token usage validation

---

## Next Steps

1. **Review this plan** - Ensure alignment with requirements
2. **Start Phase 1** - Database foundation (lowest risk)
3. **Iterate incrementally** - Test each phase before proceeding
4. **Gather feedback** - Adjust based on real usage
5. **Document usage** - Update README with memory features

---

## Notes

- **Reuse existing components**: StickyFactsManager becomes working memory
- **Minimal changes**: Existing strategies unaffected
- **Clear separation**: Each layer has distinct purpose and lifecycle
- **Testable**: Each component can be tested independently
- **Extensible**: Easy to add new memory types or retrieval methods
