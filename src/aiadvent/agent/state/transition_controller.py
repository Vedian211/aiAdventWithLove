from typing import Tuple, Optional


class TransitionController:
    """Controls and validates state transitions in the task state machine"""
    
    ALLOWED_TRANSITIONS = {
        None: ["planning"],
        "planning": ["execution"],
        "execution": ["validation"],
        "validation": ["done"],
        "done": ["planning"]
    }
    
    # Strict sequence enforcement: phases must be completed in order
    STRICT_SEQUENCE = ["planning", "execution", "validation", "done"]
    
    def __init__(self, approval_gates, completion_validator):
        self.approval_gates = approval_gates
        self.completion_validator = completion_validator
    
    def validate_transition(self, from_state: Optional[str], to_state: str, context: dict = None) -> Tuple[bool, str]:
        """Validate if transition is allowed with strict sequence enforcement"""
        if not to_state:
            return False, "Target state cannot be empty"
        
        # Check if target state is in allowed transitions
        allowed_states = self.ALLOWED_TRANSITIONS.get(from_state, [])
        if to_state not in allowed_states:
            # Provide helpful error message about required sequence
            if from_state is None:
                return False, f"Must start with planning phase. Cannot jump directly to {to_state}."
            elif from_state == "planning" and to_state == "validation":
                return False, "Cannot skip execution phase. Must complete: planning → execution → validation"
            elif from_state == "execution" and to_state == "done":
                return False, "Cannot skip validation phase. Must complete: execution → validation → done"
            else:
                return False, f"Invalid transition from {from_state} to {to_state}. Follow the sequence: planning → execution → validation → done"
        
        return True, ""
    
    def execute_transition(self, from_state: Optional[str], to_state: str, user_input: str = "", ai_response: str = "") -> dict:
        """Execute transition with validation and approval checks"""
        # Validate inputs
        if not to_state:
            return {"allowed": False, "reason": "Target state cannot be empty"}
        
        user_input = user_input or ""
        ai_response = ai_response or ""
        
        # Validate transition is allowed
        is_valid, error_msg = self.validate_transition(from_state, to_state)
        if not is_valid:
            return {"allowed": False, "reason": error_msg}
        
        # Check if approval is required
        if self.approval_gates.requires_approval(from_state, to_state):
            if not self.approval_gates.detect_approval_in_response(user_input, from_state, to_state):
                if from_state == "planning" and to_state == "execution":
                    return {"allowed": False, "reason": "User approval required to proceed with implementation. Please confirm with keywords like 'proceed', 'implement', or 'go ahead'."}
                elif from_state == "execution" and to_state == "validation":
                    return {"allowed": False, "reason": "User request required to start validation. Please ask to 'test', 'verify', or 'validate' the implementation."}
                else:
                    return {"allowed": False, "reason": "User approval required to proceed"}
        
        # Check if current stage is complete before transitioning
        if from_state and ai_response and to_state != from_state:
            if from_state == "planning" and to_state == "execution":
                is_complete, reason = self.completion_validator.validate_planning_complete(ai_response)
                if not is_complete:
                    return {"allowed": False, "reason": f"Planning incomplete: {reason}"}
            elif from_state == "execution" and to_state in ["validation", "done"]:
                is_complete, reason = self.completion_validator.validate_execution_complete(ai_response)
                if not is_complete:
                    return {"allowed": False, "reason": f"Execution incomplete: {reason}"}
            elif from_state == "validation" and to_state == "done":
                is_complete, reason = self.completion_validator.validate_validation_complete(ai_response)
                if not is_complete:
                    return {"allowed": False, "reason": f"Validation incomplete: {reason}"}
        
        return {"allowed": True, "reason": ""}