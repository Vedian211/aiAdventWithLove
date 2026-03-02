from .long_term_memory import LongTermMemoryManager


class MemoryManager:
    """Orchestrates all memory layers"""
    
    def __init__(self, agent, long_term_memory: LongTermMemoryManager):
        self.agent = agent
        self.long_term = long_term_memory
        self.working_memory = agent.sticky_facts_manager
    
    def process_exchange(self, user_input: str, assistant_response: str):
        """Process conversation exchange and update memories"""
        if self.working_memory:
            self.working_memory.extract_facts(self.agent.messages, self.agent.token_counter)
        
        self.long_term.update_profile_from_conversation(self.agent.messages)
    
    def build_context_for_prompt(self, user_input: str) -> list:
        """Build complete context from all memory layers"""
        messages = []
        
        system_content = self.agent.system_prompt or ""
        
        long_term_context = self.long_term.get_relevant_context(user_input)
        if long_term_context:
            system_content += f"\n\n{long_term_context}"
        
        if self.working_memory:
            facts_context = self.working_memory.get_facts_prompt()
            if facts_context:
                system_content += facts_context
        
        messages.append({"role": "system", "content": system_content})
        
        for msg in self.agent.messages[-6:]:
            if msg["role"] != "system":
                messages.append(msg)
        
        return messages
    
    def get_memory_stats(self) -> dict:
        """Get statistics about all memory layers"""
        stats = {
            "short_term": len([m for m in self.agent.messages if m["role"] != "system"]),
            "working_memory": self.working_memory.get_stats() if self.working_memory else {},
            "long_term": {
                "profile_items": sum(len(items) for items in self.long_term.get_profile().values()),
            }
        }
        return stats
