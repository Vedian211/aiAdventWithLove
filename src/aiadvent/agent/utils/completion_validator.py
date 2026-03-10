import json
import re
from typing import Tuple


class CompletionValidator:
    """Validates completion of task stages using AI semantic analysis"""
    
    def __init__(self, client, model="gpt-4o-mini"):
        self.client = client
        self.model = model
    
    def validate_planning_complete(self, ai_response: str) -> Tuple[bool, str]:
        """Check if planning stage is complete"""
        return self._analyze_completion(ai_response, "planning")
    
    def validate_execution_complete(self, ai_response: str) -> Tuple[bool, str]:
        """Check if execution stage is complete"""
        return self._analyze_completion(ai_response, "execution")
    
    def validate_validation_complete(self, ai_response: str) -> Tuple[bool, str]:
        """Check if validation stage is complete"""
        return self._analyze_completion(ai_response, "validation")
    
    def _analyze_completion(self, ai_response: str, stage: str) -> Tuple[bool, str]:
        """Use AI to analyze if stage is complete"""
        if not self.client or not ai_response or not stage:
            return self._fallback_completion_check(ai_response or "", stage or "")
        
        prompt = f"""Analyze if this AI response indicates the {stage} stage is COMPLETE.

AI Response:
{ai_response}

Stage definitions:
- planning: Complete when there's a clear, numbered plan or step-by-step approach
- execution: Complete when actual implementation is shown (code, files, changes made)
- validation: Complete when results are tested/verified or proof of success is provided

Respond with JSON only:
{{
  "complete": true/false,
  "reason": "<brief explanation>"
}}

Be strict - only mark complete if the stage work is actually done."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=100
            )
            
            if not response or not response.choices:
                return self._fallback_completion_check(ai_response, stage)
            
            result = response.choices[0].message.content
            if not result:
                return self._fallback_completion_check(ai_response, stage)
            
            result = result.strip()
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group())
                    complete = data.get("complete", False)
                    reason = data.get("reason", "No reason provided")
                    return bool(complete), str(reason)
                except (json.JSONDecodeError, KeyError):
                    pass
        except Exception:
            pass
        
        return self._fallback_completion_check(ai_response, stage)
    
    def _fallback_completion_check(self, ai_response: str, stage: str) -> Tuple[bool, str]:
        """Fallback keyword-based completion check"""
        if not ai_response or not stage:
            return False, "Missing response or stage information"
        
        lower_response = ai_response.lower()
        
        if stage == "planning":
            # Look for numbered steps or structured plan
            if re.search(r'\d+\.\s', ai_response) or "step" in lower_response:
                return True, "Numbered plan detected"
            return False, "No clear plan structure found"
        
        elif stage == "execution":
            # Look for code blocks or implementation indicators
            if "```" in ai_response or any(kw in lower_response for kw in ["created", "implemented", "modified", "added"]):
                return True, "Implementation detected"
            return False, "No implementation shown"
        
        elif stage == "validation":
            # Look for testing or verification indicators
            if any(kw in lower_response for kw in ["tested", "verified", "works", "successful", "confirmed"]):
                return True, "Validation evidence found"
            return False, "No validation proof provided"
        
        return False, f"Unknown stage: {stage}"