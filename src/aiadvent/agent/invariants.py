import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from openai import OpenAI


class InvariantsManager:
    """Manages invariants - unchangeable constraints that guide AI reasoning"""
    
    def __init__(self, history_manager, client: OpenAI, model: str):
        self.history_manager = history_manager
        self.client = client
        self.model = model
    
    def add_invariant(self, session_id: int, category: str, title: str, 
                     description: str, rationale: str = None, priority: str = 'high') -> int:
        """Add invariant to database"""
        now = int(datetime.now().timestamp())
        cursor = self.history_manager._execute(
            """INSERT INTO invariants 
               (session_id, category, title, description, rationale, priority, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (session_id, category, title, description, rationale, priority, now, now)
        )
        return cursor.lastrowid
    
    def get_invariants(self, session_id: int, category: str = None) -> List[Dict]:
        """Retrieve invariants for session, optionally filtered by category"""
        if category:
            rows = self.history_manager._fetch_all(
                """SELECT id, session_id, category, title, description, rationale, priority, 
                          created_at, updated_at
                   FROM invariants 
                   WHERE session_id = ? AND category = ?
                   ORDER BY priority DESC, created_at ASC""",
                (session_id, category)
            )
        else:
            rows = self.history_manager._fetch_all(
                """SELECT id, session_id, category, title, description, rationale, priority,
                          created_at, updated_at
                   FROM invariants 
                   WHERE session_id = ?
                   ORDER BY priority DESC, created_at ASC""",
                (session_id,)
            )
        
        return [
            {
                'id': row[0],
                'session_id': row[1],
                'category': row[2],
                'title': row[3],
                'description': row[4],
                'rationale': row[5],
                'priority': row[6],
                'created_at': row[7],
                'updated_at': row[8]
            }
            for row in rows
        ]
    
    def delete_invariant(self, invariant_id: int):
        """Remove invariant"""
        self.history_manager._execute(
            "DELETE FROM invariants WHERE id = ?",
            (invariant_id,)
        )
    
    def format_for_prompt(self, session_id: int) -> str:
        """Format all invariants as text for system prompt injection"""
        invariants = self.get_invariants(session_id)
        if not invariants:
            return ""
        
        # Group by category
        by_category = {}
        for inv in invariants:
            cat = inv['category']
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(inv)
        
        # Build prompt text
        lines = ["\n" + "="*60]
        lines.append("INVARIANTS AND CONSTRAINTS")
        lines.append("="*60)
        lines.append("You must respect the following invariants in all responses:")
        lines.append("")
        
        category_names = {
            'architecture': 'ARCHITECTURE',
            'technical': 'TECHNICAL DECISIONS',
            'stack': 'STACK CONSTRAINTS',
            'business': 'BUSINESS RULES'
        }
        
        for cat in ['architecture', 'technical', 'stack', 'business']:
            if cat in by_category:
                lines.append(f"[{category_names[cat]}]")
                for inv in by_category[cat]:
                    priority_marker = "🔴" if inv['priority'] == 'critical' else "🟡" if inv['priority'] == 'high' else "🟢"
                    lines.append(f"{priority_marker} {inv['title']}: {inv['description']}")
                    if inv['rationale']:
                        lines.append(f"   Rationale: {inv['rationale']}")
                lines.append("")
        
        lines.append("IMPORTANT: If a user request conflicts with these invariants:")
        lines.append("1. Clearly explain which invariant(s) would be violated")
        lines.append("2. Explain why the invariant exists (rationale)")
        lines.append("3. Refuse to provide a solution that violates the invariant")
        lines.append("4. Suggest alternative approaches that respect the invariants")
        lines.append("="*60)
        
        return "\n".join(lines)
    
    def check_violation(self, session_id: int, proposed_solution: str) -> Tuple[bool, List[str], str]:
        """Use LLM to check if proposed solution violates any invariants"""
        invariants = self.get_invariants(session_id)
        if not invariants:
            return False, [], None
        
        invariants_text = self.format_for_prompt(session_id)
        
        prompt = f"""{invariants_text}

PROPOSED SOLUTION:
{proposed_solution}

Analyze if this solution violates any invariants. Respond in JSON format:
{{
    "violates": true or false,
    "violated_invariants": ["invariant title 1", "invariant title 2"],
    "explanation": "Detailed explanation of violations"
}}"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an invariant violation detector. Respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0
            )
            
            result = json.loads(response.choices[0].message.content)
            return result.get('violates', False), result.get('violated_invariants', []), result.get('explanation', '')
        except Exception as e:
            print(f"Warning: Violation check failed: {e}")
            return False, [], None
    
    def create_interactive(self, session_id: int) -> int:
        """Interactive CLI for creating invariant"""
        print("\n=== Add Invariant ===\n")
        
        print("Category:")
        print("  1. Architecture (architectural patterns and decisions)")
        print("  2. Technical (technical solutions and approaches)")
        print("  3. Stack (technology stack constraints)")
        print("  4. Business (business rules and compliance)")
        choice = input("Choose (1-4): ").strip()
        
        categories = {'1': 'architecture', '2': 'technical', '3': 'stack', '4': 'business'}
        category = categories.get(choice)
        if not category:
            print("Invalid category")
            return None
        
        title = input("\nTitle: ").strip()
        if not title:
            print("Title is required")
            return None
        
        description = input("Description: ").strip()
        if not description:
            print("Description is required")
            return None
        
        rationale = input("Rationale (why this matters): ").strip() or None
        
        print("\nPriority:")
        print("  1. Critical (never violate)")
        print("  2. High (strongly enforce)")
        print("  3. Medium (prefer to follow)")
        priority_choice = input("Choose (1-3) [2]: ").strip() or "2"
        priorities = {'1': 'critical', '2': 'high', '3': 'medium'}
        priority = priorities.get(priority_choice, 'high')
        
        invariant_id = self.add_invariant(session_id, category, title, description, rationale, priority)
        print(f"\n✓ Invariant added (ID: {invariant_id})")
        
        return invariant_id
