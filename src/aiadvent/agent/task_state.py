import re
import json
from typing import Optional


class TaskStateMachine:
    """Tracks agent's task execution state through distinct phases"""
    
    PHASES = ["planning", "execution", "validation", "done"]
    
    def __init__(self, client=None, model="gpt-4o-mini"):
        self.phase = None
        self.step = 0
        self.total_steps = 0
        self.action_description = ""
        self.client = client
        self.model = model
        self.conversation_context = []
    
    def detect_and_update(self, user_message: str = None, ai_response: str = None):
        """Detect phase transitions using AI semantic analysis"""
        if not self.client:
            # Fallback to keyword-based detection
            self._keyword_based_detection(ai_response or "")
            return
        
        # Build context for analysis
        context = ""
        if user_message:
            context += f"User: {user_message}\n"
            self.conversation_context.append({"role": "user", "content": user_message})
        if ai_response:
            context += f"AI: {ai_response}\n"
            self.conversation_context.append({"role": "assistant", "content": ai_response})
        
        # Use AI to determine phase
        phase_analysis = self._analyze_phase_with_ai(context)
        
        if phase_analysis:
            self.phase = phase_analysis.get("phase")
            self.total_steps = phase_analysis.get("total_steps", self.total_steps)
            if phase_analysis.get("increment_step"):
                self.step += 1
            else:
                self.step = phase_analysis.get("step", self.step)
            self.action_description = phase_analysis.get("action", "")[:100]
    
    def _analyze_phase_with_ai(self, context: str) -> Optional[dict]:
        """Use AI to semantically analyze the conversation phase"""
        prompt = f"""Analyze this conversation exchange and determine the CURRENT task phase based ONLY on what was actually discussed.

Current phase: {self.phase or "none"}
Current step: {self.step}/{self.total_steps}

Recent exchange:
{context}

STRICT RULES:
1. ONLY analyze what the user ASKED for and what the AI RESPONDED with
2. DO NOT assume the AI did work that wasn't explicitly shown in the response
3. If AI only created a plan, phase is "planning" - NOT execution
4. If AI only discussed/refined a plan, stay in "planning"
5. If user asks to refine/update/modify the plan, stay in "planning"
6. If user adds new requirements or is not satisfied, go back to "planning"
7. Move to "execution" ONLY when AI shows actual implementation (code, files, changes)
8. Move to "validation" when AI proves/tests results OR user asks to verify
9. Move to "done" ONLY when user confirms completion or AI states task is complete

Phase definitions:
- planning: Creating plan, discussing approach, refining plan, asking for user confirmation, adding new requirements
- execution: Actually implementing (showing code, creating files, making changes)
- validation: Testing, running code, verifying implementation works, proving results
- done: Task confirmed complete by user or AI

Phase transitions:
- planning → execution: User approves plan OR asks to proceed
- execution → validation: AI proves results OR user asks to verify
- validation → planning: User not satisfied OR adds new requirements
- validation → done: User confirms completion

Respond with JSON only:
{{
  "phase": "planning|execution|validation|done",
  "step": <current_step_number>,
  "total_steps": <total_steps_from_plan>,
  "increment_step": false,
  "action": "<what_actually_happened>"
}}

CRITICAL: Be conservative. If unsure between phases, choose the earlier phase."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=150
            )
            
            result = response.choices[0].message.content.strip()
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            print(f"Phase analysis error: {e}")
        
        return None
    
    def _keyword_based_detection(self, response: str):
        """Fallback keyword-based detection"""
        lower_response = response.lower()
        
        # Done phase keywords (check first)
        if any(kw in lower_response for kw in ["completed", "finished", "done", "all set", "successfully implemented"]):
            self.phase = "done"
            self.step = self.total_steps if self.total_steps > 0 else 1
        
        # Validation phase keywords
        elif any(kw in lower_response for kw in ["validating", "verifying", "let me verify", "let me check"]):
            if self.phase != "validation":
                self.phase = "validation"
                self.step = 1
        
        # Planning phase keywords
        elif any(kw in lower_response for kw in ["let me plan", "i'll plan", "planning", "first, i need to", "let's break this down"]):
            if self.phase != "planning":
                self.phase = "planning"
                self.step = 1
                self._extract_steps(response)
        
        # Execution phase keywords
        elif any(kw in lower_response for kw in ["executing", "implementing", "i'll create", "i'll modify", "now i'll"]):
            if self.phase != "execution":
                self.phase = "execution"
                self.step = 1
            else:
                self.step += 1
        
        # Extract action description from first sentence
        sentences = re.split(r'[.!?]\s+', response)
        if sentences:
            self.action_description = sentences[0][:100]
    
    def _extract_steps(self, response: str):
        """Try to extract total steps from numbered lists"""
        # Look for numbered patterns like "1.", "2.", etc.
        numbers = re.findall(r'(?:^|\s)(\d+)\.', response, re.MULTILINE)
        if numbers:
            self.total_steps = max(int(n) for n in numbers)
    
    def get_state(self) -> dict:
        """Get current state as dictionary"""
        return {
            "phase": self.phase,
            "step": self.step,
            "total_steps": self.total_steps,
            "action_description": self.action_description
        }
    
    def get_display(self) -> str:
        """Get formatted state for display"""
        if not self.phase:
            return ""
        
        if self.total_steps > 0:
            return f"[{self.phase.title()} {self.step}/{self.total_steps}]"
        else:
            return f"[{self.phase.title()}]"
    
    def reset(self):
        """Reset state machine"""
        self.phase = None
        self.step = 0
        self.total_steps = 0
        self.action_description = ""
