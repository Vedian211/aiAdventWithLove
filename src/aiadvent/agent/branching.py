import json
from typing import List, Dict, Optional
from datetime import datetime


class BranchingManager:
    """Manages conversation branches and checkpoints with database persistence"""
    
    def __init__(self, history_manager=None, session_id=None):
        self.history_manager = history_manager
        self.session_id = session_id
        self.checkpoints = {}  # {checkpoint_id: {"name": str, "message_index": int}}
        self.branches = {}  # {branch_id: {"checkpoint_id": str, "name": str, "messages": list}}
        self.current_branch = None
        self.checkpoint_counter = 0
        self.branch_counter = 0
        self.branch_saved_count = {}  # Track how many messages saved per branch
    
    def create_checkpoint(self, name: str, messages: list) -> str:
        """Create a checkpoint at current conversation state"""
        self.checkpoint_counter += 1
        timestamp = int(datetime.now().timestamp() * 1000)  # milliseconds
        checkpoint_id = f"cp_{self.checkpoint_counter}_{timestamp}"
        message_index = len(messages)
        
        self.checkpoints[checkpoint_id] = {
            "name": name,
            "message_index": message_index
        }
        
        # Save to database
        if self.history_manager and self.session_id:
            self.history_manager.save_checkpoint(self.session_id, checkpoint_id, name, message_index)
        
        return checkpoint_id
    
    def create_branch(self, checkpoint_id: str, name: str, base_messages: list) -> str:
        """Create a new branch from a checkpoint"""
        if checkpoint_id not in self.checkpoints:
            return None
        
        self.branch_counter += 1
        timestamp = int(datetime.now().timestamp() * 1000)  # milliseconds
        branch_id = f"br_{self.branch_counter}_{timestamp}"
        
        checkpoint = self.checkpoints[checkpoint_id]
        # Store only messages up to checkpoint
        branch_messages = base_messages[:checkpoint["message_index"]].copy()
        
        self.branches[branch_id] = {
            "checkpoint_id": checkpoint_id,
            "name": name,
            "messages": branch_messages
        }
        
        # Initialize saved count for this branch
        self.branch_saved_count[branch_id] = 0
        
        # Save to database
        if self.history_manager and self.session_id:
            self.history_manager.save_branch(self.session_id, branch_id, checkpoint_id, name, is_active=False)
        
        return branch_id
    
    def switch_branch(self, branch_id: str) -> Optional[list]:
        """Switch to a different branch and return its messages"""
        if branch_id not in self.branches:
            return None
        
        self.current_branch = branch_id
        
        # Update active branch in database
        if self.history_manager and self.session_id:
            self.history_manager.set_active_branch(self.session_id, branch_id)
        
        return self.branches[branch_id]["messages"].copy()
    
    def update_current_branch(self, messages: list):
        """Update messages in current branch"""
        if self.current_branch and self.current_branch in self.branches:
            old_messages = self.branches[self.current_branch]["messages"]
            old_len = len(old_messages)
            self.branches[self.current_branch]["messages"] = messages.copy()
            
            # Save new messages to database (only the ones after checkpoint)
            if self.history_manager and len(messages) > old_len:
                checkpoint_id = self.branches[self.current_branch]["checkpoint_id"]
                checkpoint_index = self.checkpoints[checkpoint_id]["message_index"]
                
                # Get current saved count for this branch
                saved_count = self.branch_saved_count.get(self.current_branch, 0)
                
                # Save only new messages
                for i in range(old_len, len(messages)):
                    if i >= checkpoint_index:
                        msg = messages[i]
                        self.history_manager.save_branch_message(
                            self.current_branch,
                            saved_count,
                            msg["role"],
                            msg["content"]
                        )
                        saved_count += 1
                
                # Update saved count
                self.branch_saved_count[self.current_branch] = saved_count
    
    def list_checkpoints(self) -> List[Dict]:
        """List all checkpoints"""
        return [
            {"id": cp_id, "name": data["name"], "message_count": data["message_index"]}
            for cp_id, data in self.checkpoints.items()
        ]
    
    def list_branches(self, checkpoint_id: str = None) -> List[Dict]:
        """List all branches, optionally filtered by checkpoint"""
        result = []
        for br_id, data in self.branches.items():
            if checkpoint_id is None or data["checkpoint_id"] == checkpoint_id:
                # Calculate messages added after checkpoint
                checkpoint_index = self.checkpoints[data["checkpoint_id"]]["message_index"]
                messages_after_checkpoint = len(data["messages"]) - checkpoint_index
                
                result.append({
                    "id": br_id,
                    "name": data["name"],
                    "checkpoint_id": data["checkpoint_id"],
                    "message_count": messages_after_checkpoint,
                    "active": br_id == self.current_branch
                })
        return result
    
    def get_stats(self) -> dict:
        """Get branching statistics"""
        return {
            "checkpoints": len(self.checkpoints),
            "branches": len(self.branches),
            "current_branch": self.current_branch
        }
    
    def reset(self):
        """Clear all branches and checkpoints"""
        self.checkpoints = {}
        self.branches = {}
        self.current_branch = None
        self.checkpoint_counter = 0
        self.branch_counter = 0
        self.branch_saved_count = {}
    
    def load_from_db(self, base_messages: list):
        """Load checkpoints and branches from database"""
        if not self.history_manager or not self.session_id:
            return
        
        # Load checkpoints
        checkpoints_data = self.history_manager.load_checkpoints(self.session_id)
        for cp in checkpoints_data:
            self.checkpoints[cp["checkpoint_id"]] = {
                "name": cp["name"],
                "message_index": cp["message_index"]
            }
            # Update counter
            cp_num = int(cp["checkpoint_id"].split("_")[1])
            self.checkpoint_counter = max(self.checkpoint_counter, cp_num)
        
        # Load branches
        branches_data = self.history_manager.load_branches(self.session_id)
        for br in branches_data:
            branch_id = br["branch_id"]
            checkpoint_id = br["checkpoint_id"]
            
            if checkpoint_id in self.checkpoints:
                checkpoint_index = self.checkpoints[checkpoint_id]["message_index"]
                
                # Start with messages up to checkpoint
                branch_messages = base_messages[:checkpoint_index].copy()
                
                # Add branch-specific messages
                branch_msgs = self.history_manager.load_branch_messages(branch_id)
                for msg in branch_msgs:
                    if msg["role"] == "user":
                        from openai.types.chat import ChatCompletionUserMessageParam
                        branch_messages.append(ChatCompletionUserMessageParam(
                            role="user",
                            content=msg["content"]
                        ))
                    elif msg["role"] == "assistant":
                        from openai.types.chat import ChatCompletionAssistantMessageParam
                        branch_messages.append(ChatCompletionAssistantMessageParam(
                            role="assistant",
                            content=msg["content"]
                        ))
                
                self.branches[branch_id] = {
                    "checkpoint_id": checkpoint_id,
                    "name": br["name"],
                    "messages": branch_messages
                }
                
                if br["is_active"]:
                    self.current_branch = branch_id
                
                # Update counter
                br_num = int(branch_id.split("_")[1])
                self.branch_counter = max(self.branch_counter, br_num)

