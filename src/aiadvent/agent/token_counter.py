import tiktoken


class TokenCounter:
    """Handles token counting for messages and conversations"""
    
    def __init__(self, encoding_name: str = "cl100k_base"):
        self.encoding = tiktoken.get_encoding(encoding_name)
    
    def count_message(self, content: str) -> int:
        """Count tokens in a single message"""
        return len(self.encoding.encode(content))
    
    def count_messages(self, messages: list) -> int:
        """Count tokens in full message history (as sent to API)"""
        total = 0
        for message in messages:
            # Add tokens for message content
            total += len(self.encoding.encode(message["content"]))
            # Add overhead per message (role, formatting)
            total += 4
        # Add overhead for message list
        total += 2
        return total
