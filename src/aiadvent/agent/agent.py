from openai import OpenAI
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam, ChatCompletionAssistantMessageParam
import tiktoken
from .history import HistoryManager
from .token_counter import TokenCounter
from .context_compressor import ContextCompressor
from .sticky_facts import StickyFactsManager
from .branching import BranchingManager


class Agent:
    """AI Agent that encapsulates OpenAI API interactions and maintains conversation state"""
    
    TOKEN_LIMIT = 5000
    WARNING_THRESHOLD = 0.8
    
    def __init__(self, api_key: str, model: str = "gpt-4o-mini", system_prompt: str = None, compression_enabled: bool = False, strategy: str = "sliding_window"):
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
        
        # Compression (sliding window)
        self.compression_enabled = compression_enabled
        self.compressor = ContextCompressor(self.client, self.model) if compression_enabled else None
        
        # Sticky facts
        self.sticky_facts_manager = StickyFactsManager(self.client, self.model) if strategy == "sticky_facts" else None
        
        # Branching
        self.branching_manager = BranchingManager(self.history_manager, None) if strategy == "branching" else None
        
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
    
    def think(self, user_input: str) -> str:
        """Process user input and generate response using OpenAI API"""
        # Count prompt tokens
        self.last_prompt_tokens = self.token_counter.count_message(user_input)
        
        self.add_message("user", user_input)
        
        # Get messages to send based on strategy
        messages_to_send = self._prepare_messages()
        
        # Count full history tokens (before response)
        self.last_history_tokens = self.token_counter.count_messages(self.messages)
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages_to_send
        )
        
        assistant_message = response.choices[0].message.content
        self.add_message("assistant", assistant_message)
        
        # Count response tokens
        self.set_last_response_tokens(assistant_message)
        
        return assistant_message
    
    def _prepare_messages(self):
        """Prepare messages based on active strategy"""
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
