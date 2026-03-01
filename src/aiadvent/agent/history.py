import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional


class HistoryManager:
    """Manages conversation history persistence using SQLite"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            history_dir = Path(__file__).parent.parent / "history"
            history_dir.mkdir(exist_ok=True)
            db_path = str(history_dir / "conversations.db")
        
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            # Enable foreign keys
            conn.execute("PRAGMA foreign_keys = ON")
            
            # Sessions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    model TEXT NOT NULL,
                    system_prompt TEXT,
                    created_at INTEGER NOT NULL,
                    last_updated INTEGER NOT NULL,
                    total_tokens INTEGER DEFAULT 0,
                    message_count INTEGER DEFAULT 0
                )
            """)
            
            # Messages table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    sequence INTEGER NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    token_count INTEGER,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
                    UNIQUE(session_id, sequence)
                )
            """)
            
            # Sticky facts table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sticky_facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    category TEXT NOT NULL,
                    key TEXT,
                    value TEXT NOT NULL,
                    updated_at INTEGER NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                )
            """)
            
            # Checkpoints table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    checkpoint_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    message_index INTEGER NOT NULL,
                    created_at INTEGER NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
                    UNIQUE(session_id, checkpoint_id)
                )
            """)
            
            # Branches table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS branches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    branch_id TEXT NOT NULL,
                    checkpoint_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT 0,
                    created_at INTEGER NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
                    UNIQUE(session_id, branch_id)
                )
            """)
            
            # Branch messages table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS branch_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    branch_id TEXT NOT NULL,
                    sequence INTEGER NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    token_count INTEGER,
                    UNIQUE(branch_id, sequence)
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, sequence)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_facts_session ON sticky_facts(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_updated ON sessions(last_updated DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_checkpoints_session ON checkpoints(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_branches_session ON branches(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_branch_messages ON branch_messages(branch_id, sequence)")
            
            conn.commit()
    
    def create_session(self, name: str, strategy: str, model: str, system_prompt: str = None) -> int:
        """Create a new session and return its ID"""
        now = int(datetime.now().timestamp())
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.execute(
                "INSERT INTO sessions (name, strategy, model, system_prompt, created_at, last_updated) VALUES (?, ?, ?, ?, ?, ?)",
                (name, strategy, model, system_prompt, now, now)
            )
            conn.commit()
            return cursor.lastrowid
    
    def save_message(self, session_id: int, role: str, content: str, token_count: int = None):
        """Save a message to the session"""
        now = int(datetime.now().timestamp())
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            
            # Get next sequence number
            cursor = conn.execute(
                "SELECT COALESCE(MAX(sequence), -1) + 1 FROM messages WHERE session_id = ?",
                (session_id,)
            )
            sequence = cursor.fetchone()[0]
            
            conn.execute(
                "INSERT INTO messages (session_id, sequence, role, content, timestamp, token_count) VALUES (?, ?, ?, ?, ?, ?)",
                (session_id, sequence, role, content, now, token_count)
            )
            
            # Update session stats
            conn.execute(
                "UPDATE sessions SET last_updated = ?, message_count = message_count + 1, total_tokens = total_tokens + ? WHERE id = ?",
                (now, token_count or 0, session_id)
            )
            conn.commit()
    
    def load_session(self, session_id: int) -> Optional[Dict]:
        """Load session metadata and all messages"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.row_factory = sqlite3.Row
            
            session = conn.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
            
            if not session:
                return None
            
            messages = conn.execute(
                "SELECT role, content, timestamp, token_count FROM messages WHERE session_id = ? ORDER BY sequence",
                (session_id,)
            ).fetchall()
            
            return {
                "id": session["id"],
                "name": session["name"],
                "strategy": session["strategy"],
                "model": session["model"],
                "system_prompt": session["system_prompt"],
                "created_at": session["created_at"],
                "last_updated": session["last_updated"],
                "total_tokens": session["total_tokens"],
                "message_count": session["message_count"],
                "messages": [dict(msg) for msg in messages]
            }
    
    def list_sessions(self) -> List[Dict]:
        """List all sessions ordered by last updated"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            sessions = conn.execute(
                "SELECT id, name, strategy, model, created_at, last_updated, message_count, total_tokens FROM sessions ORDER BY last_updated DESC"
            ).fetchall()
            
            return [dict(session) for session in sessions]
    
    def delete_session(self, session_id: int):
        """Delete a session and all its related data (cascades automatically)"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            conn.commit()
    
    def update_session_name(self, session_id: int, name: str):
        """Update session name"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE sessions SET name = ? WHERE id = ?", (name, session_id))
            conn.commit()
    
    def save_sticky_facts(self, session_id: int, facts: dict):
        """Save sticky facts for a session"""
        now = int(datetime.now().timestamp())
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            
            # Clear existing facts for this session
            conn.execute("DELETE FROM sticky_facts WHERE session_id = ?", (session_id,))
            
            # Insert new facts
            for category, value in facts.items():
                if value:
                    if isinstance(value, dict):
                        # Store nested dict items
                        for key, val in value.items():
                            conn.execute(
                                "INSERT INTO sticky_facts (session_id, category, key, value, updated_at) VALUES (?, ?, ?, ?, ?)",
                                (session_id, category, key, str(val), now)
                            )
                    else:
                        # Store simple value
                        conn.execute(
                            "INSERT INTO sticky_facts (session_id, category, key, value, updated_at) VALUES (?, ?, ?, ?, ?)",
                            (session_id, category, None, str(value), now)
                        )
            
            conn.commit()
    
    def load_sticky_facts(self, session_id: int) -> dict:
        """Load sticky facts for a session"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT category, key, value FROM sticky_facts WHERE session_id = ?",
                (session_id,)
            ).fetchall()
            
            facts = {}
            for row in rows:
                category = row["category"]
                key = row["key"]
                value = row["value"]
                
                if key:
                    # Nested dict
                    if category not in facts:
                        facts[category] = {}
                    facts[category][key] = value
                else:
                    # Simple value
                    facts[category] = value
            
            return facts
    
    def save_checkpoint(self, session_id: int, checkpoint_id: str, name: str, message_index: int):
        """Save a checkpoint"""
        now = int(datetime.now().timestamp())
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute(
                "INSERT INTO checkpoints (session_id, checkpoint_id, name, message_index, created_at) VALUES (?, ?, ?, ?, ?)",
                (session_id, checkpoint_id, name, message_index, now)
            )
            conn.commit()
    
    def load_checkpoints(self, session_id: int) -> List[Dict]:
        """Load all checkpoints for a session"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT checkpoint_id, name, message_index, created_at FROM checkpoints WHERE session_id = ? ORDER BY created_at",
                (session_id,)
            ).fetchall()
            
            return [dict(row) for row in rows]
    
    def save_branch(self, session_id: int, branch_id: str, checkpoint_id: str, name: str, is_active: bool = False):
        """Save a branch"""
        now = int(datetime.now().timestamp())
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            
            # Deactivate all branches if this one is active
            if is_active:
                conn.execute("UPDATE branches SET is_active = 0 WHERE session_id = ?", (session_id,))
            
            conn.execute(
                "INSERT INTO branches (session_id, branch_id, checkpoint_id, name, is_active, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (session_id, branch_id, checkpoint_id, name, is_active, now)
            )
            conn.commit()
    
    def load_branches(self, session_id: int) -> List[Dict]:
        """Load all branches for a session"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT branch_id, checkpoint_id, name, is_active, created_at FROM branches WHERE session_id = ? ORDER BY created_at",
                (session_id,)
            ).fetchall()
            
            return [dict(row) for row in rows]
    
    def set_active_branch(self, session_id: int, branch_id: str):
        """Set a branch as active"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("UPDATE branches SET is_active = 0 WHERE session_id = ?", (session_id,))
            conn.execute("UPDATE branches SET is_active = 1 WHERE session_id = ? AND branch_id = ?", (session_id, branch_id))
            conn.commit()
    
    def save_branch_message(self, branch_id: str, sequence: int, role: str, content: str, token_count: int = None):
        """Save a message to a branch"""
        now = int(datetime.now().timestamp())
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO branch_messages (branch_id, sequence, role, content, timestamp, token_count) VALUES (?, ?, ?, ?, ?, ?)",
                (branch_id, sequence, role, content, now, token_count)
            )
            conn.commit()
    
    def load_branch_messages(self, branch_id: str) -> List[Dict]:
        """Load all messages for a branch"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT role, content, timestamp, token_count FROM branch_messages WHERE branch_id = ? ORDER BY sequence",
                (branch_id,)
            ).fetchall()
            
            return [dict(row) for row in rows]
