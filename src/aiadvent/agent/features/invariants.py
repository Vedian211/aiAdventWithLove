from datetime import datetime
from typing import List, Dict, Tuple
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
    
    def delete_all_invariants(self, session_id: int):
        """Delete all invariants for a session"""
        self.history_manager._execute(
            "DELETE FROM invariants WHERE session_id = ?",
            (session_id,)
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
        
        # Check if there's a phase sequence invariant
        has_phase_invariant = any('Phase Sequence' in inv.get('title', '') for inv in invariants)
        if not has_phase_invariant:
            # No phase invariant, no violation
            return False, [], None
        
        # Extract current phase from context
        current_phase = None
        if "[Current Phase:" in proposed_solution:
            import re
            match = re.search(r'\[Current Phase: (\w+)\]', proposed_solution)
            if match:
                current_phase = match.group(1)
                # Remove phase marker from user request
                proposed_solution = re.sub(r'\[Current Phase: \w+\]\n\n', '', proposed_solution)
        
        if not current_phase:
            # Can't check without knowing current phase
            return False, [], None
        
        # First, detect what phase the user is requesting
        detection_prompt = f"""Analyze this user request and determine what phase they want to transition to.

USER REQUEST: {proposed_solution}

PHASE KEYWORDS:
- validation: "test", "verify", "validate", "check", "prove"
- execution: "implement", "code", "create", "write", "build", "develop"
- planning: "plan", "design", "outline", "strategy"
- done: "complete", "finish", "done"

Respond with ONLY ONE WORD: planning, execution, validation, done, or none"""
        
        try:
            # Detect requested phase
            response1 = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Detect the phase from keywords. Respond with ONE word only."},
                    {"role": "user", "content": detection_prompt}
                ],
                temperature=0,
                max_tokens=10
            )
            
            requested_phase = response1.choices[0].message.content.strip().lower()
            
            # Check if this is a forbidden transition
            forbidden_transitions = [
                ("planning", "validation"),
                ("validation", "execution")
            ]
            
            is_forbidden = (current_phase, requested_phase) in forbidden_transitions
            
            if is_forbidden:
                if current_phase == "planning" and requested_phase == "validation":
                    explanation = "Cannot test without implementing code first."
                elif current_phase == "validation" and requested_phase == "execution":
                    explanation = "Cannot implement after validation without re-planning first."
                else:
                    explanation = f"Transition from {current_phase} to {requested_phase} is not allowed."
                
                return True, ["Phase Sequence"], explanation
            
            return False, [], None
            
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
    
    def create_phase_sequence_invariant(self, session_id: int) -> int:
        """Create automatic phase sequence invariant for strict workflow enforcement"""
        title = "Strict Phase Sequence"
        description = (
            "ONLY 2 TRANSITIONS ARE FORBIDDEN:\n"
            "\n"
            "1. Planning → Validation\n"
            "   (Cannot test without implementing code first)\n"
            "\n"
            "2. Validation → Execution\n"
            "   (Cannot implement after validation, must return to Planning first)\n"
            "\n"
            "ALL OTHER TRANSITIONS ARE ALLOWED, including:\n"
            "- Planning → Execution (implement the plan)\n"
            "- Execution → Validation (test the code)\n"
            "- Any phase → Planning (refine)\n"
            "- Any phase → Done (satisfied)"
        )
        rationale = "Ensures code is implemented before testing, and changes go through planning."
        
        return self.add_invariant(
            session_id=session_id,
            category='technical',
            title=title,
            description=description,
            rationale=rationale,
            priority='critical'
        )
    
    def has_phase_sequence_invariant(self, session_id: int) -> bool:
        """Check if session has phase sequence invariant"""
        invariants = self.get_invariants(session_id)
        return any(inv['title'] == 'Strict Phase Sequence' for inv in invariants)
