import json
from typing import Dict, List, Optional
from openai import OpenAI


class UserProfile:
    """Manages user profile for personalized AI responses"""
    
    def __init__(self, client: OpenAI, model: str, history_manager=None):
        self.client = client
        self.model = model
        self.history_manager = history_manager
        self.profile_id: Optional[int] = None
        self.name: str = ""
        self.communication_style: str = "casual"
        self.response_format: str = "concise"
        self.language: str = "en"
        self.constraints: List[str] = []
        self.preferences: Dict = {}
        self.domain_expertise: List[str] = []
    
    def create_profile_interactive(self) -> int:
        """Interactive CLI to create profile"""
        print("\n=== Create User Profile ===\n")
        
        self.name = input("Your name: ").strip() or "User"
        
        print("\nCommunication style:")
        print("  1. Formal (professional, structured)")
        print("  2. Casual (friendly, relaxed)")
        print("  3. Technical (precise, detailed)")
        style_choice = input("Choose (1-3) [2]: ").strip() or "2"
        styles = {"1": "formal", "2": "casual", "3": "technical"}
        self.communication_style = styles.get(style_choice, "casual")
        
        print("\nResponse format:")
        print("  1. Concise (brief, to the point)")
        print("  2. Detailed (comprehensive explanations)")
        print("  3. Structured (organized with headers/bullets)")
        format_choice = input("Choose (1-3) [1]: ").strip() or "1"
        formats = {"1": "concise", "2": "detailed", "3": "structured"}
        self.response_format = formats.get(format_choice, "concise")
        
        print("\nLanguage:")
        print("  1. English (en)")
        print("  2. Russian (ru)")
        print("  3. Ukrainian (uk)")
        lang_choice = input("Choose (1-3) [1]: ").strip() or "1"
        languages = {"1": "en", "2": "ru", "3": "uk"}
        self.language = languages.get(lang_choice, "en")
        
        constraints_input = input("\nConstraints (comma-separated, e.g., 'no_code_examples,bullet_points_only'): ").strip()
        self.constraints = [c.strip() for c in constraints_input.split(",") if c.strip()]
        
        expertise_input = input("\nDomain expertise (comma-separated, e.g., 'python,machine_learning'): ").strip()
        self.domain_expertise = [e.strip() for e in expertise_input.split(",") if e.strip()]
        
        emoji_pref = input("\nUse emoji in responses? (y/n) [n]: ").strip().lower()
        self.preferences = {"emoji": emoji_pref == "y"}
        
        if self.history_manager:
            self.profile_id = self.save_profile()
            print(f"\n✓ Profile created with ID: {self.profile_id}")
        
        return self.profile_id
    
    def load_profile(self, profile_id: int) -> bool:
        """Load profile from database"""
        if not self.history_manager:
            return False
        
        profile_data = self.history_manager.load_user_profile(profile_id)
        if not profile_data:
            return False
        
        self.profile_id = profile_data["id"]
        self.name = profile_data["name"]
        self.communication_style = profile_data["communication_style"]
        self.response_format = profile_data["response_format"]
        self.language = profile_data["language"]
        self.constraints = json.loads(profile_data["constraints"]) if profile_data["constraints"] else []
        self.preferences = json.loads(profile_data["preferences"]) if profile_data["preferences"] else {}
        self.domain_expertise = json.loads(profile_data["domain_expertise"]) if profile_data["domain_expertise"] else []
        
        return True
    
    def save_profile(self) -> int:
        """Save profile to database"""
        if not self.history_manager:
            return None
        
        profile_data = self.to_dict()
        
        if self.profile_id:
            self.history_manager.update_user_profile(self.profile_id, profile_data)
            return self.profile_id
        else:
            self.profile_id = self.history_manager.create_user_profile(profile_data)
            return self.profile_id
    
    def update_from_conversation(self, messages: List[Dict]) -> None:
        """Auto-update profile from conversation patterns"""
        # Extract user corrections or style preferences from recent messages
        user_messages = [m for m in messages[-10:] if m.get("role") == "user"]
        
        if not user_messages:
            return
        
        # Simple heuristic: look for style-related keywords
        combined_text = " ".join([m.get("content", "") for m in user_messages]).lower()
        
        if "more formal" in combined_text or "professional" in combined_text:
            self.communication_style = "formal"
        elif "casual" in combined_text or "friendly" in combined_text:
            self.communication_style = "casual"
        
        if "brief" in combined_text or "shorter" in combined_text:
            self.response_format = "concise"
        elif "detailed" in combined_text or "more info" in combined_text:
            self.response_format = "detailed"
    
    def get_system_prompt_enhancement(self) -> str:
        """Generate personalized system prompt addition"""
        enhancements = []
        
        enhancements.append(f"User's name: {self.name}")
        
        # Communication style
        style_prompts = {
            "formal": "Use formal, professional language. Avoid slang and casual expressions.",
            "casual": "Use friendly, conversational tone. Feel free to be relaxed and approachable.",
            "technical": "Use precise technical language. Provide detailed explanations with accuracy."
        }
        enhancements.append(style_prompts.get(self.communication_style, ""))
        
        # Response format
        format_prompts = {
            "concise": "Keep responses brief and to the point. Avoid unnecessary elaboration.",
            "detailed": "Provide comprehensive, detailed explanations. Cover all relevant aspects.",
            "structured": "Organize responses with clear headers, bullet points, and structure."
        }
        enhancements.append(format_prompts.get(self.response_format, ""))
        
        # Language
        if self.language != "en":
            lang_names = {"ru": "Russian", "uk": "Ukrainian"}
            enhancements.append(f"Respond in {lang_names.get(self.language, self.language)}.")
        
        # Constraints
        if "no_code_examples" in self.constraints:
            enhancements.append("Do not include code examples. Explain concepts without code.")
        if "bullet_points_only" in self.constraints:
            enhancements.append("Format all responses as bullet points.")
        if "no_emoji" in self.constraints:
            enhancements.append("Do not use emoji in responses.")
        
        # Preferences
        if self.preferences.get("emoji"):
            enhancements.append("Use relevant emoji to make responses more engaging.")
        
        # Domain expertise
        if self.domain_expertise:
            expertise_str = ", ".join(self.domain_expertise)
            enhancements.append(f"User has expertise in: {expertise_str}. Adjust technical depth accordingly.")
        
        return "\n".join([e for e in enhancements if e])
    
    def to_dict(self) -> Dict:
        """Export profile as dict"""
        return {
            "name": self.name,
            "communication_style": self.communication_style,
            "response_format": self.response_format,
            "language": self.language,
            "constraints": json.dumps(self.constraints),
            "preferences": json.dumps(self.preferences),
            "domain_expertise": json.dumps(self.domain_expertise)
        }
    
    def __str__(self) -> str:
        """String representation of profile"""
        lines = [
            f"Profile ID: {self.profile_id}",
            f"Name: {self.name}",
            f"Style: {self.communication_style}",
            f"Format: {self.response_format}",
            f"Language: {self.language}",
            f"Constraints: {', '.join(self.constraints) if self.constraints else 'None'}",
            f"Preferences: {self.preferences}",
            f"Expertise: {', '.join(self.domain_expertise) if self.domain_expertise else 'None'}"
        ]
        return "\n".join(lines)
