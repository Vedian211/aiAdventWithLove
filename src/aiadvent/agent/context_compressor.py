from openai import OpenAI
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam, ChatCompletionAssistantMessageParam


class ContextCompressor:
    """Compresses conversation history by keeping recent messages and summarizing older ones"""
    
    def __init__(self, client: OpenAI, model: str, recent_window_size: int = 14, summary_batch_size: int = 14):
        self.client = client
        self.model = model
        self.recent_window_size = recent_window_size  # Number of messages (not exchanges)
        self.summary_batch_size = summary_batch_size  # Number of messages per batch
        self.summaries = []
        self.tokens_saved = 0
        self.original_tokens = 0
        self.compressed_tokens = 0
    
    def compress(self, messages: list, token_counter) -> list:
        """Compress message history using hybrid window strategy"""
        # Skip system prompt
        system_messages = [m for m in messages if m["role"] == "system"]
        conversation_messages = [m for m in messages if m["role"] != "system"]
        
        # If conversation is short, no compression needed
        if len(conversation_messages) <= self.recent_window_size:
            return messages
        
        # Split into old (to summarize) and recent (keep full)
        old_messages = conversation_messages[:-self.recent_window_size]
        recent_messages = conversation_messages[-self.recent_window_size:]
        
        # Count original tokens
        self.original_tokens = token_counter.count_messages(messages)
        
        # Generate summary for old messages if not already done
        # Summarize all old messages in one batch if we haven't summarized yet
        if old_messages and not self.summaries:
            summary = self._generate_summary(old_messages)
            self.summaries.append(summary)
        elif len(old_messages) > len(self.summaries) * self.summary_batch_size:
            # Add more summaries for additional batches
            batches_needed = (len(old_messages) // self.summary_batch_size) - len(self.summaries)
            for i in range(batches_needed):
                start_idx = len(self.summaries) * self.summary_batch_size
                end_idx = start_idx + self.summary_batch_size
                batch = old_messages[start_idx:end_idx]
                if batch:  # Only summarize if batch is not empty
                    summary = self._generate_summary(batch)
                    self.summaries.append(summary)
        
        # Build compressed message list
        compressed = system_messages.copy()
        
        # Add summaries
        if self.summaries:
            summary_text = " ".join(self.summaries)
            compressed.append(ChatCompletionSystemMessageParam(
                role="system",
                content=f"Previous conversation summary: {summary_text}"
            ))
        
        # Add recent messages
        compressed.extend(recent_messages)
        
        # Count compressed tokens
        self.compressed_tokens = token_counter.count_messages(compressed)
        self.tokens_saved = self.original_tokens - self.compressed_tokens
        
        return compressed
    
    def _generate_summary(self, messages: list) -> str:
        """Generate concise summary of message batch"""
        # Format messages for summarization
        conversation_text = ""
        for msg in messages:
            role = msg["role"].capitalize()
            conversation_text += f"{role}: {msg['content']}\n"
        
        summary_prompt = [
            ChatCompletionSystemMessageParam(
                role="system",
                content="Summarize the following conversation concisely, capturing key points, decisions, and context. Keep it under 100 tokens."
            ),
            ChatCompletionUserMessageParam(
                role="user",
                content=conversation_text
            )
        ]
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=summary_prompt,
            max_tokens=100
        )
        
        return response.choices[0].message.content.strip()
    
    def get_stats(self) -> dict:
        """Get compression statistics"""
        if self.original_tokens == 0:
            return {
                "original": 0,
                "compressed": 0,
                "saved": 0,
                "ratio": 0
            }
        
        ratio = (self.tokens_saved / self.original_tokens) * 100 if self.original_tokens > 0 else 0
        
        return {
            "original": self.original_tokens,
            "compressed": self.compressed_tokens,
            "saved": self.tokens_saved,
            "ratio": ratio
        }
    
    def reset(self):
        """Reset compression state"""
        self.summaries = []
        self.tokens_saved = 0
        self.original_tokens = 0
        self.compressed_tokens = 0
