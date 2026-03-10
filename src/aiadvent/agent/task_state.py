import re
import json
from typing import Optional
from .transition_controller import TransitionController
from .approval_gates import ApprovalGates
from .completion_validator import CompletionValidator


class TaskStateMachine:
    """Tracks agent's task execution state through distinct phases"""
    
    PHASES = ["planning", "execution", "validation", "done"]
    PHASE_MAP = {
        "planning": "planning",
        "execution": "execution", 
        "validation": "validation",
        "done": "done"
    }
    
    def __init__(self, client=None, model="gpt-4o-mini"):
        self.phase = None
        self.step = 0
        self.total_steps = 0
        self.action_description = ""
        self.client = client
        self.model = model
        self.conversation_context = []
        self.max_context_size = 10  # Keep last 10 exchanges
        
        # Initialize transition control components
        self.approval_gates = ApprovalGates()
        self.completion_validator = CompletionValidator(client, model)
        self.transition_controller = TransitionController(self.approval_gates, self.completion_validator)
    
    def detect_and_update(self, user_message: str = None, ai_response: str = None):
        """Detect phase transitions using AI semantic analysis"""
        # Build context for analysis and add to conversation context
        context = ""
        new_messages = []
        
        if user_message:
            context += f"User: {user_message}\n"
            new_messages.append({"role": "user", "content": user_message})
        if ai_response:
            context += f"AI: {ai_response}\n"
            new_messages.append({"role": "assistant", "content": ai_response})
        
        # Add new messages
        self.conversation_context.extend(new_messages)
        
        # Cleanup old context to prevent unbounded growth
        if len(self.conversation_context) > self.max_context_size:
            self.conversation_context = self.conversation_context[-self.max_context_size:]
        
        if not self.client:
            # Fallback to keyword-based detection
            self._keyword_based_detection(ai_response or "")
            return {"allowed": True, "reason": ""}
        
        # Use AI to determine phase
        try:
            phase_analysis = self._analyze_phase_with_ai(context)
        except Exception as e:
            # Fallback to keyword-based detection on AI analysis failure
            self._keyword_based_detection(ai_response or "")
            return {"allowed": True, "reason": f"AI analysis failed, used fallback: {str(e)}"}
        
        if phase_analysis:
            new_phase = phase_analysis.get("phase")
            
            # Update state (no transition validation - handled by invariants)
            if new_phase:
                self.phase = new_phase
            self.total_steps = phase_analysis.get("total_steps", self.total_steps)
            if phase_analysis.get("increment_step"):
                self.step += 1
            else:
                self.step = phase_analysis.get("step", self.step)
            self.action_description = str(phase_analysis.get("action", ""))[:100]
        
        return {"allowed": True, "reason": ""}
    
    def _analyze_phase_with_ai(self, context: str) -> Optional[dict]:
        """Use AI to semantically analyze the conversation phase"""
        if not context or not context.strip():
            return None
        
        prompt = f"""Analyze this conversation exchange and determine what phase the AI is CURRENTLY IN based on what it ACTUALLY DID (not what it suggests doing next).

Current phase: {self.phase or "none"}
Current step: {self.step}/{self.total_steps}

Recent exchange:
{context}

PHASE DETECTION RULES:

Planning Phase:
- AI is creating a plan, discussing approach, outlining steps
- AI is refining requirements, asking clarifying questions
- AI has NOT yet shown any implementation code

Execution Phase:
- AI shows actual code (functions, classes, etc.)
- AI creates or modifies files
- AI is actively implementing the solution
- IGNORE mentions of "next phase" or "we can proceed to" - focus on what AI DID

Validation Phase:
- AI runs tests and shows test output
- AI validates implementation with actual results
- AI proves the code works with examples/output
- NOT just suggesting to test - actually testing

Done Phase:
- Task is confirmed complete by user
- All work is finished and validated

CRITICAL: Determine phase based on what the AI ACTUALLY DID in this response, not what it suggests doing next.

Respond with JSON only:
{{
  "phase": "planning|execution|validation|done",
  "step": <current_step_number>,
  "total_steps": <total_steps_from_plan>,
  "increment_step": false,
  "action": "<what_actually_happened>"
}}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=150
            )
            
            if not response or not response.choices:
                return None
            
            result = response.choices[0].message.content
            if not result:
                return None
            
            result = result.strip()
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group())
                    # Validate required fields
                    if "phase" in data:
                        return data
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            # Re-raise to be caught by caller
            raise e
        
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
        self.conversation_context = []
    
    def get_next_phase(self) -> Optional[str]:
        """Get the next phase in sequence"""
        if not self.phase:
            return "planning"
        
        phase_sequence = {
            "planning": "execution",
            "execution": "validation", 
            "validation": "done",
            "done": "planning"
        }
        return phase_sequence.get(self.phase)
    
    def get_confirmation_prompt(self) -> str:
        """Get prompt asking user to confirm transition to next phase"""
        next_phase = self.get_next_phase()
        if not next_phase:
            return ""
        
        # Show only for planning and execution phases
        if self.phase in ["planning", "execution"]:
            return f"\n\nPlease confirm that everything is ok to proceed to the next phase <{next_phase}>. To confirm type: /approve"
        
        return ""
    
    def transition_to_next_phase(self) -> dict:
        """Transition to next phase and return action to take"""
        next_phase = self.get_next_phase()
        if not next_phase:
            return {"success": False, "error": "No next phase available"}
        
        # Validate transition
        is_valid, error_msg = self.transition_controller.validate_transition(
            self.phase, next_phase
        )
        
        if not is_valid:
            return {"success": False, "error": error_msg}
        
        old_phase = self.phase
        self.phase = next_phase
        
        # Determine action based on transition
        action = None
        if old_phase == "planning" and next_phase == "execution":
            action = "implement_plan"
        elif old_phase == "execution" and next_phase == "validation":
            action = "validate_implementation"
        elif old_phase == "validation" and next_phase == "done":
            action = "task_complete"
        elif old_phase == "done" and next_phase == "planning":
            action = "new_task"
        
        return {
            "success": True,
            "from": old_phase,
            "to": next_phase,
            "action": action
        }
