from openai import OpenAI
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam, ChatCompletionAssistantMessageParam
import tiktoken
import asyncio
from typing import Optional, List, Dict, Any
from .core import HistoryManager
from .utils import TokenCounter
from .memory import ContextCompressor, StickyFactsManager, BranchingManager, LongTermMemoryManager, MemoryManager
from .features import UserProfile, InvariantsManager
from .state import TaskStateMachine
from .mcp import MCPClient
from .mcp.config import MCPServerConfig


class Agent:
    """AI Agent that encapsulates OpenAI API interactions and maintains conversation state"""
    
    TOKEN_LIMIT = 5000
    WARNING_THRESHOLD = 0.8
    
    def __init__(self, api_key: str, model: str = "gpt-4o-mini", system_prompt: str = None, compression_enabled: bool = False, strategy: str = "sliding_window", mcp_server_config: Optional[MCPServerConfig] = None, mcp_server_configs: Optional[List[MCPServerConfig]] = None):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.system_prompt = system_prompt
        self.messages = []
        self.encoding = tiktoken.get_encoding("cl100k_base")
        self.token_counter = TokenCounter()
        self.total_tokens_used = 0
        self.session_id = None
        self.history_manager = HistoryManager()
        self.strategy = strategy
        
        # User profile
        self.user_profile = None
        self.profile_id = None
        
        # Task state machine
        self.task_state = TaskStateMachine(self.client, self.model)
        # Set default phase to planning
        self.task_state.phase = "planning"
        
        # Invariants
        self.invariants_manager = InvariantsManager(self.history_manager, self.client, self.model)
        
        # Compression (sliding window)
        self.compression_enabled = compression_enabled
        self.compressor = ContextCompressor(self.client, self.model) if compression_enabled else None
        
        # Sticky facts
        self.sticky_facts_manager = StickyFactsManager(self.client, self.model) if strategy == "sticky_facts" else None
        
        # Branching
        self.branching_manager = BranchingManager(self.history_manager, None) if strategy == "branching" else None
        
        # Memory layers
        if strategy == "memory_layers":
            self.long_term_memory = LongTermMemoryManager(self.history_manager, self.client, self.model)
            self.sticky_facts_manager = StickyFactsManager(self.client, self.model)
            self.memory_manager = MemoryManager(self, self.long_term_memory)
        else:
            self.long_term_memory = None
            self.memory_manager = None
        
        # MCP integration - support multiple servers
        self.mcp_clients: Dict[str, MCPClient] = {}
        self.mcp_tools: List[Dict[str, Any]] = []
        
        # Legacy single server support
        if mcp_server_config:
            self.mcp_server_configs = [mcp_server_config]
        elif mcp_server_configs:
            self.mcp_server_configs = mcp_server_configs
        else:
            self.mcp_server_configs = []
        
        # Token tracking for last exchange
        self.last_prompt_tokens = 0
        self.last_response_tokens = 0
        self.last_history_tokens = 0
        self.last_compression_stats = None
        
        if system_prompt:
            self.messages.append(ChatCompletionSystemMessageParam(
                role="system",
                content=system_prompt
            ))
    
    async def init_mcp(self) -> None:
        """Initialize MCP connections and retrieve tools. Must be called explicitly."""
        if not self.mcp_server_configs:
            raise RuntimeError("No MCP server configs provided")
        await self._init_mcp_connections()
    
    async def _init_mcp_connections(self) -> None:
        """Initialize all MCP connections and retrieve tools."""
        for config in self.mcp_server_configs:
            try:
                client = MCPClient()
                await client.connect_stdio(
                    command=config.command,
                    args=config.args,
                    env=config.env
                )
                
                # Get server name from command/args
                server_name = config.args[1] if len(config.args) > 1 else config.command
                self.mcp_clients[server_name] = client
                
                # Retrieve and merge tools
                tools = await client.list_tools()
                self.mcp_tools.extend(tools)
                
            except Exception as e:
                print(f"Warning: Failed to initialize MCP connection for {config.command}: {e}")
    
    @property
    def mcp_client(self) -> Optional[MCPClient]:
        """Legacy property for backward compatibility. Returns first client."""
        if self.mcp_clients:
            return list(self.mcp_clients.values())[0]
        return None
    
    def get_mcp_tools(self) -> List[Dict[str, Any]]:
        """Get list of available MCP tools."""
        return self.mcp_tools
    
    async def call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call an MCP tool with given arguments.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Dictionary of arguments for the tool
            
        Returns:
            Tool execution result
        """
        if not self.mcp_clients:
            raise RuntimeError("MCP clients not initialized. Call init_mcp() first.")
        
        # Find which client has this tool
        for client in self.mcp_clients.values():
            try:
                result = await client.call_tool(tool_name, arguments)
                return result
            except Exception:
                continue
        
        raise RuntimeError(f"Tool '{tool_name}' not found in any MCP server")
    
    def add_message(self, role: str, content: str):
        """Add a message to conversation history"""
        if role == "user":
            self.messages.append(ChatCompletionUserMessageParam(role="user", content=content))
        elif role == "assistant":
            self.messages.append(ChatCompletionAssistantMessageParam(role="assistant", content=content))
    
    def count_tokens(self) -> int:
        """Count total tokens in current conversation"""
        total = 0
        for message in self.messages:
            total += len(self.encoding.encode(message["content"]))
        return total
    
    def check_token_limit(self) -> tuple[bool, int]:
        """Check if token count exceeds warning threshold. Returns (is_warning, token_count)"""
        token_count = self.count_tokens()
        is_warning = token_count >= self.TOKEN_LIMIT * self.WARNING_THRESHOLD
        return is_warning, token_count
    
    def clear_history(self):
        """Clear conversation history, keeping only system prompt"""
        self.messages = []
        if self.system_prompt:
            self.messages.append(ChatCompletionSystemMessageParam(
                role="system",
                content=self.system_prompt
            ))
        
        # Reset compressor if enabled
        if self.compression_enabled and self.compressor:
            self.compressor.reset()
        
        # Reset sticky facts if enabled
        if self.sticky_facts_manager:
            self.sticky_facts_manager.reset()
        
        # Reset branching if enabled
        if self.branching_manager:
            self.branching_manager.reset()
        
        # Reset task state
        self.task_state.reset()
    
    def think_stream(self, user_input: str):
        """Process user input and generate streaming response"""
        # Count prompt tokens
        self.last_prompt_tokens = self.token_counter.count_message(user_input)
        
        self.add_message("user", user_input)
        
        # Get messages to send based on strategy
        messages_to_send = self._prepare_messages()
        
        # Count full history tokens (before response)
        self.last_history_tokens = self.token_counter.count_messages(self.messages)
        
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages_to_send,
            stream=True,
            stream_options={"include_usage": True}
        )
        
        return stream
    
    def think(self, user_input: str, skip_phase_detection: bool = False) -> str:
        """Process user input and generate response using OpenAI API"""
        # Count prompt tokens
        self.last_prompt_tokens = self.token_counter.count_message(user_input)
        
        self.add_message("user", user_input)
        
        # Check for invariant violations if session has invariants
        if self.session_id:
            invariants = self.invariants_manager.get_invariants(self.session_id)
            if invariants:
                # Build context for violation check (include current phase)
                context = user_input
                if self.task_state.phase:
                    context = f"[Current Phase: {self.task_state.phase}]\n\n{user_input}"
                
                violates, violated_list, explanation = self.invariants_manager.check_violation(
                    self.session_id, context
                )
                if violates:
                    # Generate refusal response
                    refusal_message = self._generate_invariant_refusal(violated_list, explanation)
                    self.add_message("assistant", refusal_message)
                    self.set_last_response_tokens(refusal_message)
                    return refusal_message
        
        # Get messages to send based on strategy
        messages_to_send = self._prepare_messages()
        
        # Count full history tokens (before response)
        self.last_history_tokens = self.token_counter.count_messages(self.messages)
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages_to_send
        )
        
        assistant_message = response.choices[0].message.content
        
        # Add confirmation prompt at the end
        confirmation_prompt = self.task_state.get_confirmation_prompt()
        if confirmation_prompt:
            assistant_message += confirmation_prompt
        
        self.add_message("assistant", assistant_message)
        
        # Update task state with both user input and AI response (unless skipped)
        if not skip_phase_detection:
            self.task_state.detect_and_update(user_input, assistant_message)
            if self.session_id:
                self.history_manager.save_task_state(self.session_id, self.task_state.get_state())
        
        # Count response tokens
        self.set_last_response_tokens(assistant_message)
        
        # Update memories if using memory layers
        if self.memory_manager:
            self.memory_manager.process_exchange(user_input, assistant_message)
        
        return assistant_message
    
    def handle_phase_transition(self) -> str:
        """Handle transition to next phase and generate appropriate prompt"""
        result = self.task_state.transition_to_next_phase()
        
        if not result["success"]:
            return f"⚠️ Cannot transition: {result['error']}"
        
        # Save state
        if self.session_id:
            self.history_manager.save_task_state(self.session_id, self.task_state.get_state())
        
        # Generate prompt based on action
        action = result.get("action")
        
        if action == "implement_plan":
            prompt = "Now implement the plan. Provide the complete code implementation based on our discussion. Show all files and code needed."
        elif action == "validate_implementation":
            prompt = "Now validate the implementation. Run tests and verify that the code works correctly. Show the test results."
        elif action == "task_complete":
            message = "✓ Task complete! Feel free to ask any new questions."
            confirmation_prompt = self.task_state.get_confirmation_prompt()
            return message + confirmation_prompt if confirmation_prompt else message
        elif action == "new_task":
            message = "✓ Ready for a new task. What would you like to work on?"
            confirmation_prompt = self.task_state.get_confirmation_prompt()
            return message + confirmation_prompt if confirmation_prompt else message
        else:
            return f"✓ Transitioned to {result['to']} phase."
        
        # Call AI with the generated prompt (skip auto phase detection)
        return self.think(prompt, skip_phase_detection=True)
    
    def _prepare_messages(self):
        """Prepare messages based on active strategy"""
        # Memory layers strategy
        if self.memory_manager:
            return self.memory_manager.build_context_for_prompt(
                self.messages[-1]["content"] if self.messages and self.messages[-1]["role"] != "system" else ""
            )
        
        # Sticky facts strategy
        if self.sticky_facts_manager:
            # Extract facts from conversation
            self.sticky_facts_manager.extract_facts(self.messages, self.token_counter)
            
            # Build context: system prompt + facts + last N messages
            messages = []
            
            # Add system prompt with facts
            if self.system_prompt:
                facts_prompt = self.sticky_facts_manager.get_facts_prompt()
                enhanced_prompt = self.system_prompt + facts_prompt
                messages.append(ChatCompletionSystemMessageParam(
                    role="system",
                    content=enhanced_prompt
                ))
            
            # Add last 6 messages (3 exchanges)
            for msg in self.messages[-6:]:
                if msg["role"] != "system":
                    messages.append(msg)
            
            return messages
        
        # Branching strategy
        if self.branching_manager:
            # Update current branch with latest messages
            self.branching_manager.update_current_branch(self.messages)
            return self.messages
        
        # Sliding window strategy (compression)
        if self.compression_enabled and self.compressor:
            messages = self.compressor.compress(self.messages, self.token_counter)
            self.last_compression_stats = self.compressor.get_stats()
            return messages
        
        # Default: return all messages
        return self.messages
    
    def respond(self, user_input: str) -> str:
        """Public interface for getting agent response"""
        return self.think(user_input)
    
    def create_session(self, name: str) -> int:
        """Create a new session in database"""
        self.session_id = self.history_manager.create_session(
            name=name,
            strategy=self.strategy,
            model=self.model,
            system_prompt=self.system_prompt
        )
        
        # Update branching manager with session_id
        if self.branching_manager:
            self.branching_manager.session_id = self.session_id
        
        return self.session_id
    
    def save_message_to_db(self, role: str, content: str, token_count: int = None):
        """Save a message to the database if session exists"""
        if self.session_id:
            self.history_manager.save_message(self.session_id, role, content, token_count)
    
    def load_session(self, session_id: int) -> bool:
        """Load a session from database and restore agent state"""
        session_data = self.history_manager.load_session(session_id)
        if not session_data:
            return False
        
        self.session_id = session_id
        self.model = session_data["model"]
        self.system_prompt = session_data["system_prompt"]
        self.messages = []
        
        # Restore system prompt
        if self.system_prompt:
            self.messages.append(ChatCompletionSystemMessageParam(
                role="system",
                content=self.system_prompt
            ))
        
        # Restore conversation messages
        for msg in session_data["messages"]:
            if msg["role"] == "user":
                self.messages.append(ChatCompletionUserMessageParam(
                    role="user",
                    content=msg["content"]
                ))
            elif msg["role"] == "assistant":
                self.messages.append(ChatCompletionAssistantMessageParam(
                    role="assistant",
                    content=msg["content"]
                ))
        
        # Restore facts if using sticky facts strategy
        if self.strategy == "sticky_facts" and self.sticky_facts_manager:
            facts = self.history_manager.load_sticky_facts(session_id)
            if facts:
                self.sticky_facts_manager.facts = facts
        
        # Restore branching if using branching strategy
        if self.strategy == "branching" and self.branching_manager:
            self.branching_manager.session_id = session_id
            self.branching_manager.load_from_db(self.messages)
            
            # If there's an active branch, switch to it
            if self.branching_manager.current_branch:
                branch_messages = self.branching_manager.switch_branch(self.branching_manager.current_branch)
                if branch_messages:
                    self.messages = branch_messages
        
        # Restore task state
        task_state_data = self.history_manager.load_task_state(session_id)
        if task_state_data:
            self.task_state.phase = task_state_data.get("phase")
            self.task_state.step = task_state_data.get("step", 0)
            self.task_state.total_steps = task_state_data.get("total_steps", 0)
            self.task_state.action_description = task_state_data.get("action_description", "")
        
        # Rebuild system prompt with invariants
        self._rebuild_system_prompt()
        
        return True
    
    def list_sessions(self):
        """List all available sessions"""
        return self.history_manager.list_sessions()
    
    def set_last_response_tokens(self, response_content: str):
        """Set token count for last response"""
        self.last_response_tokens = self.token_counter.count_message(response_content)
    
    def get_token_stats(self) -> dict:
        """Get token statistics for last exchange"""
        stats = {
            "prompt": self.last_prompt_tokens,
            "history": self.last_history_tokens,
            "response": self.last_response_tokens
        }
        
        if self.compression_enabled and self.last_compression_stats:
            stats["compression"] = self.last_compression_stats
        
        if self.sticky_facts_manager:
            stats["sticky_facts"] = self.sticky_facts_manager.get_stats()
        
        if self.branching_manager:
            stats["branching"] = self.branching_manager.get_stats()
        
        return stats
    
    def generate_session_title(self) -> str:
        """Generate a concise title for the conversation based on first exchange"""
        # Only use first user message for title generation
        first_user_msg = None
        for msg in self.messages:
            if msg["role"] == "user":
                first_user_msg = msg["content"]
                break
        
        if not first_user_msg:
            return "New Chat"
        
        # Create a minimal prompt for title generation
        title_prompt = [
            ChatCompletionSystemMessageParam(
                role="system",
                content="Generate a concise 2-5 word title for a conversation that starts with this user message. Reply with ONLY the title, no quotes or punctuation."
            ),
            ChatCompletionUserMessageParam(
                role="user",
                content=first_user_msg
            )
        ]
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=title_prompt,
                max_tokens=20
            )
            title = response.choices[0].message.content.strip()
            # Clean up any quotes or extra formatting
            title = title.strip('"\'.,!?')
            return title if title else "New Chat"
        except:
            return "New Chat"
    
    def update_session_name(self, name: str):
        """Update the current session's name"""
        if self.session_id:
            self.history_manager.update_session_name(self.session_id, name)
    
    def save_facts(self):
        """Save current facts to database"""
        if self.session_id and self.sticky_facts_manager:
            self.history_manager.save_sticky_facts(self.session_id, self.sticky_facts_manager.facts)
    
    def toggle_compression(self, enabled: bool):
        """Enable or disable compression"""
        self.compression_enabled = enabled
        if enabled and not self.compressor:
            self.compressor = ContextCompressor(self.client, self.model)
        elif not enabled and self.compressor:
            self.compressor.reset()
    
    def get_compression_stats(self) -> dict:
        """Get current compression statistics"""
        if self.compressor:
            return self.compressor.get_stats()
        return None
    
    def set_user_profile(self, profile_id: int) -> bool:
        """Load and activate user profile"""
        profile = UserProfile(self.client, self.model, self.history_manager)
        if profile.load_profile(profile_id):
            self.user_profile = profile
            self.profile_id = profile_id
            
            # Link profile to current session
            if self.session_id:
                self.history_manager.link_session_to_profile(self.session_id, profile_id)
            
            # Rebuild system prompt with profile
            self._rebuild_system_prompt()
            return True
        return False
    
    def _rebuild_system_prompt(self):
        """Rebuild system prompt with profile enhancements and invariants"""
        # Remove old system message if exists
        if self.messages and self.messages[0].get("role") == "system":
            self.messages.pop(0)
        
        # Build new system prompt
        base_prompt = self.system_prompt or "You are a helpful AI assistant."
        
        # Add profile enhancements
        if self.user_profile:
            profile_enhancement = self.user_profile.get_system_prompt_enhancement()
            base_prompt = f"{base_prompt}\n\n=== User Personalization ===\n{profile_enhancement}"
        
        # Add invariants
        if self.session_id:
            invariants_text = self.invariants_manager.format_for_prompt(self.session_id)
            if invariants_text:
                base_prompt += invariants_text
        
        # Insert at beginning
        self.messages.insert(0, ChatCompletionSystemMessageParam(
            role="system",
            content=base_prompt
        ))
    
    def _generate_invariant_refusal(self, violated_invariants: list, explanation: str) -> str:
        """Generate a refusal message when invariants are violated"""
        # For phase sequence violations, use a brief, clear format
        if any("Phase" in inv or "Sequence" in inv for inv in violated_invariants):
            return f"⚠️ {explanation}"
        
        # For other invariants, use the standard format
        message = "❌ **Cannot proceed - Invariant Violation**\n\n"
        message += f"Your request conflicts with the following invariant(s):\n"
        for inv in violated_invariants:
            message += f"- {inv}\n"
        message += f"\n**Explanation:**\n{explanation}\n\n"
        message += "Please modify your request to respect these constraints, or use `/invariants delete` to remove the invariant if it's no longer needed."
        return message
