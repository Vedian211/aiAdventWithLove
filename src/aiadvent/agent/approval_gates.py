import re
from typing import Optional


class ApprovalGates:
    """Manages user approval requirements for state transitions"""
    
    APPROVAL_KEYWORDS = [
        "proceed", "implement", "go ahead", "start", "begin", "execute",
        "yes", "ok", "okay", "continue", "do it", "let's go"
    ]
    
    VALIDATION_KEYWORDS = [
        "test", "verify", "validate", "check", "run", "try", "prove",
        "show me", "demonstrate", "confirm"
    ]
    
    def requires_approval(self, from_state: Optional[str], to_state: str) -> bool:
        """Check if transition requires user approval"""
        # Planning -> execution requires approval
        if from_state == "planning" and to_state == "execution":
            return True
        # Execution -> validation requires approval
        if from_state == "execution" and to_state == "validation":
            return True
        return False
    
    def detect_approval_in_response(self, user_input: str, from_state: Optional[str] = None, to_state: str = None) -> bool:
        """Detect approval keywords in user input based on transition type"""
        if not user_input or not isinstance(user_input, str):
            return False
        
        user_lower = user_input.strip().lower()
        if not user_lower:
            return False
        
        # For execution -> validation, check for validation keywords
        if from_state == "execution" and to_state == "validation":
            for keyword in self.VALIDATION_KEYWORDS:
                if keyword in user_lower:
                    return True
            return False
        
        # For planning -> execution, check for approval keywords
        # Check for explicit approval keywords
        for keyword in self.APPROVAL_KEYWORDS:
            if keyword in user_lower:
                return True
        
        # Check for imperative phrases
        imperative_patterns = [
            r'\b(please\s+)?(go|start|begin|implement|execute|proceed)',
            r'\b(let\'s|lets)\s+(go|start|begin|implement|execute|proceed)',
            r'\b(can\s+you\s+)?(start|begin|implement|execute|proceed)'
        ]
        
        for pattern in imperative_patterns:
            if re.search(pattern, user_lower):
                return True
        
        return False