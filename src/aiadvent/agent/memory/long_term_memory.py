from openai import OpenAI
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam
from ..core import HistoryManager
import json


class LongTermMemoryManager:
    """Manages long-term memory: profile, solutions, knowledge"""
    
    def __init__(self, history_manager: HistoryManager, client: OpenAI, model: str):
        self.history = history_manager
        self.client = client
        self.model = model
    
    def get_profile(self, category: str = None) -> dict:
        """Get user profile"""
        return self.history.load_profile(category)
    
    def update_profile_from_conversation(self, messages: list):
        """Extract profile information from conversation"""
        if len(messages) <= 1:
            return
        
        recent = [f"{m['role']}: {m['content']}" for m in messages[-4:] if m['role'] != 'system']
        if not recent:
            return
        
        conversation_text = "\n".join(recent)
        
        prompt = f"""Extract user preferences and context from this conversation.
Look for: language/framework preferences, role/domain, style preferences.

Conversation:
{conversation_text}

Return JSON: {{"preferences": {{}}, "context": {{}}, "style": {{}}}}
Return ONLY valid JSON."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    ChatCompletionSystemMessageParam(role="system", content="Extract profile data, return JSON only."),
                    ChatCompletionUserMessageParam(role="user", content=prompt)
                ],
                temperature=0
            )
            
            content = response.choices[0].message.content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            
            profile_data = json.loads(content)
            
            for category, items in profile_data.items():
                if items:
                    for key, value in items.items():
                        self.history.save_profile_item(key, value, category)
        except:
            pass
    
    def find_similar_solutions(self, problem_description: str, limit: int = 3) -> list:
        """Find solutions similar to the problem description"""
        keywords = problem_description.lower().split()[:5]
        solutions = []
        
        for keyword in keywords:
            results = self.history.load_solutions(keyword, limit)
            solutions.extend(results)
        
        seen = set()
        unique = []
        for sol in solutions:
            if sol['id'] not in seen:
                seen.add(sol['id'])
                unique.append(sol)
        
        return unique[:limit]
    
    def search_knowledge(self, query: str, limit: int = 5) -> list:
        """Search knowledge base"""
        return self.history.search_knowledge(query, limit)
    
    def get_relevant_context(self, current_input: str) -> str:
        """Build context string from long-term memory"""
        parts = []
        
        profile = self.get_profile()
        if profile:
            lines = []
            for category, items in profile.items():
                for key, value in items.items():
                    lines.append(f"- {key}: {value}")
            if lines:
                parts.append(f"USER PROFILE:\n" + "\n".join(lines))
        
        solutions = self.find_similar_solutions(current_input, limit=3)
        if solutions:
            lines = [f"- {s['problem_type']}: {s['solution']}" for s in solutions]
            parts.append(f"RELEVANT SOLUTIONS:\n" + "\n".join(lines))
        
        knowledge = self.search_knowledge(current_input, limit=3)
        if knowledge:
            lines = [f"- {k['topic']}: {k['content'][:100]}" for k in knowledge]
            parts.append(f"RELEVANT KNOWLEDGE:\n" + "\n".join(lines))
        
        return "\n\n".join(parts) if parts else ""
