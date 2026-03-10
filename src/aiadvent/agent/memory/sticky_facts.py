from openai import OpenAI
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam
import json


class StickyFactsManager:
    """Manages sticky facts extraction and storage for conversation context"""
    
    def __init__(self, client: OpenAI, model: str):
        self.client = client
        self.model = model
        self.facts = {}
    
    def extract_facts(self, messages: list, token_counter) -> dict:
        """Extract key facts from recent conversation"""
        if len(messages) <= 1:  # Only system prompt
            return self.facts
        
        # Get last 3 exchanges (6 messages: user + assistant pairs)
        recent_messages = []
        for msg in messages[-6:]:
            if msg["role"] != "system":
                recent_messages.append(f"{msg['role']}: {msg['content']}")
        
        if not recent_messages:
            return self.facts
        
        conversation_text = "\n".join(recent_messages)
        current_facts = json.dumps(self.facts, indent=2) if self.facts else "{}"
        
        prompt = f"""You are a fact extraction assistant. Update the facts dictionary based on the conversation.

CURRENT FACTS (MUST PRESERVE AND UPDATE):
{current_facts}

RECENT CONVERSATION:
{conversation_text}

RULES:
1. PRESERVE all existing facts from CURRENT FACTS
2. ADD new facts from the recent conversation
3. UPDATE existing facts if new information contradicts them
4. Use these categories:
   - goal: User's primary objective (string)
   - constraints: Limitations or rules (string or null)
   - preferences: Likes, dislikes, style choices (string or null)
   - decisions: Key conclusions reached (object with key-value pairs)
   - agreements: Mutual agreements (string or null)

5. For "decisions", use an object to store multiple key-value pairs
6. Keep each value concise (1-2 sentences max)

CRITICAL: Return ALL facts (existing + new), not just new ones.

Return ONLY valid JSON, no other text."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    ChatCompletionSystemMessageParam(role="system", content="You extract key facts from conversations and return JSON only."),
                    ChatCompletionUserMessageParam(role="user", content=prompt)
                ],
                temperature=0
            )
            
            content = response.choices[0].message.content.strip()
            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            
            updated_facts = json.loads(content)
            self.facts = updated_facts
            return self.facts
        except:
            return self.facts
    
    def get_facts_prompt(self) -> str:
        """Generate a prompt section with current facts"""
        if not self.facts:
            return ""
        
        facts_text = "\n".join([f"- {k}: {v}" for k, v in self.facts.items() if v])
        return f"\n\nKEY FACTS FROM CONVERSATION:\n{facts_text}"
    
    def reset(self):
        """Clear all facts"""
        self.facts = {}
    
    def get_stats(self) -> dict:
        """Get statistics about stored facts"""
        # Count all facts including nested ones
        total = 0
        for key, value in self.facts.items():
            if value:
                if isinstance(value, dict):
                    total += len(value)
                else:
                    total += 1
        
        return {
            "total_facts": total,
            "facts": self.facts
        }
