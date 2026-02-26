from openai import OpenAI
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam, ChatCompletionAssistantMessageParam
import tiktoken
from .history import HistoryManager
from .token_counter import TokenCounter
from .context_compressor import ContextCompressor


class Agent:
    """AI Agent that encapsulates OpenAI API interactions and maintains conversation state"""
    
    TOKEN_LIMIT = 8192
    WARNING_THRESHOLD = 0.8
    
    def __init__(self, api_key: str, model: str = "gpt-4", system_prompt: str = None, compression_enabled: bool = False):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.system_prompt = system_prompt
        self.messages = []
        self.encoding = tiktoken.get_encoding("cl100k_base")
        self.token_counter = TokenCounter()
        self.total_tokens_used = 0
        self.session_id = None
        self.history_manager = HistoryManager()
        
        # Compression
        self.compression_enabled = compression_enabled
        self.compressor = ContextCompressor(self.client, self.model) if compression_enabled else None
        
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
    
    def think_stream(self, user_input: str):
        """Process user input and generate streaming response"""
        # Count prompt tokens
        self.last_prompt_tokens = self.token_counter.count_message(user_input)
        
        self.add_message("user", user_input)
        
        # Get messages to send (compressed or full)
        messages_to_send = self.messages
        if self.compression_enabled and self.compressor:
            messages_to_send = self.compressor.compress(self.messages, self.token_counter)
            self.last_compression_stats = self.compressor.get_stats()
        
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
        
        # Get messages to send (compressed or full)
        messages_to_send = self.messages
        if self.compression_enabled and self.compressor:
            messages_to_send = self.compressor.compress(self.messages, self.token_counter)
            self.last_compression_stats = self.compressor.get_stats()
        
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
    
    def respond(self, user_input: str) -> str:
        """Public interface for getting agent response"""
        return self.think(user_input)
    
    def create_session(self, name: str) -> int:
        """Create a new session in database"""
        self.session_id = self.history_manager.create_session(
            name=name,
            model=self.model,
            system_prompt=self.system_prompt
        )
        return self.session_id
    
    def save_message_to_db(self, role: str, content: str):
        """Save a message to the database if session exists"""
        if self.session_id:
            self.history_manager.save_message(self.session_id, role, content)
    
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
        
        return stats
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
