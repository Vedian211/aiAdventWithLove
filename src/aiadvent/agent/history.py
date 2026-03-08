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
            
            # User profile table (long-term memory)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_profile (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE NOT NULL,
                    value TEXT NOT NULL,
                    category TEXT NOT NULL,
                    updated_at INTEGER NOT NULL
                )
            """)
            
            # Learned solutions table (long-term memory)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS learned_solutions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    problem_type TEXT NOT NULL,
                    solution TEXT NOT NULL,
                    context TEXT,
                    success_count INTEGER DEFAULT 1,
                    last_used INTEGER NOT NULL,
                    created_at INTEGER NOT NULL
                )
            """)
            
            # Knowledge base table (long-term memory)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_base (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source_session_id INTEGER,
                    relevance_score REAL DEFAULT 1.0,
                    created_at INTEGER NOT NULL,
                    FOREIGN KEY (source_session_id) REFERENCES sessions(id) ON DELETE SET NULL
                )
            """)
            
            # User profiles table (personalization)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    communication_style TEXT,
                    response_format TEXT,
                    language TEXT,
                    constraints TEXT,
                    preferences TEXT,
                    domain_expertise TEXT,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                )
            """)
            
            # Session-profile link table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS session_profiles (
                    session_id INTEGER NOT NULL,
                    profile_id INTEGER NOT NULL,
                    PRIMARY KEY (session_id),
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
                    FOREIGN KEY (profile_id) REFERENCES user_profiles(id) ON DELETE CASCADE
                )
            """)
            
            # Task states table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS task_states (
                    session_id INTEGER NOT NULL,
                    phase TEXT,
                    step INTEGER DEFAULT 0,
                    total_steps INTEGER DEFAULT 0,
                    action_description TEXT,
                    updated_at INTEGER NOT NULL,
                    PRIMARY KEY (session_id),
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                )
            """)
            
            # Invariants table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS invariants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    category TEXT NOT NULL CHECK(category IN ('architecture', 'technical', 'stack', 'business')),
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    rationale TEXT,
                    priority TEXT DEFAULT 'high' CHECK(priority IN ('critical', 'high', 'medium')),
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, sequence)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_facts_session ON sticky_facts(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_updated ON sessions(last_updated DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_checkpoints_session ON checkpoints(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_branches_session ON branches(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_branch_messages ON branch_messages(branch_id, sequence)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_profile_category ON user_profile(category)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_solutions_type ON learned_solutions(problem_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_topic ON knowledge_base(topic)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_invariants_session ON invariants(session_id, category)")
            
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
    
    # Long-term memory methods
    
    def save_profile_item(self, key: str, value: str, category: str):
        """Save a user profile item"""
        now = int(datetime.now().timestamp())
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO user_profile (key, value, category, updated_at) VALUES (?, ?, ?, ?)",
                (key, value, category, now)
            )
            conn.commit()
    
    def load_profile(self, category: str = None) -> dict:
        """Load user profile, optionally filtered by category"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if category:
                rows = conn.execute("SELECT key, value, category FROM user_profile WHERE category = ?", (category,)).fetchall()
            else:
                rows = conn.execute("SELECT key, value, category FROM user_profile").fetchall()
            
            profile = {}
            for row in rows:
                cat = row["category"]
                if cat not in profile:
                    profile[cat] = {}
                profile[cat][row["key"]] = row["value"]
            return profile
    
    def save_solution(self, problem_type: str, solution: str, context: str = None) -> int:
        """Save a learned solution"""
        now = int(datetime.now().timestamp())
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO learned_solutions (problem_type, solution, context, last_used, created_at) VALUES (?, ?, ?, ?, ?)",
                (problem_type, solution, context, now, now)
            )
            conn.commit()
            return cursor.lastrowid
    
    def load_solutions(self, problem_type: str = None, limit: int = 10) -> list:
        """Load learned solutions, optionally filtered by problem type"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if problem_type:
                rows = conn.execute(
                    "SELECT * FROM learned_solutions WHERE problem_type LIKE ? ORDER BY success_count DESC, last_used DESC LIMIT ?",
                    (f"%{problem_type}%", limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM learned_solutions ORDER BY success_count DESC, last_used DESC LIMIT ?",
                    (limit,)
                ).fetchall()
            return [dict(row) for row in rows]
    
    def save_knowledge(self, topic: str, content: str, session_id: int = None):
        """Save knowledge base entry"""
        now = int(datetime.now().timestamp())
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO knowledge_base (topic, content, source_session_id, created_at) VALUES (?, ?, ?, ?)",
                (topic, content, session_id, now)
            )
            conn.commit()
    
    def search_knowledge(self, query: str, limit: int = 5) -> list:
        """Search knowledge base by query"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM knowledge_base WHERE topic LIKE ? OR content LIKE ? ORDER BY relevance_score DESC LIMIT ?",
                (f"%{query}%", f"%{query}%", limit)
            ).fetchall()
            return [dict(row) for row in rows]
    
    def create_user_profile(self, profile_data: dict) -> int:
        """Create a new user profile and return its ID"""
        now = int(datetime.now().timestamp())
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """INSERT INTO user_profiles 
                (name, communication_style, response_format, language, constraints, preferences, domain_expertise, created_at, updated_at) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (profile_data["name"], profile_data["communication_style"], profile_data["response_format"],
                 profile_data["language"], profile_data["constraints"], profile_data["preferences"],
                 profile_data["domain_expertise"], now, now)
            )
            conn.commit()
            return cursor.lastrowid
    
    def load_user_profile(self, profile_id: int) -> Optional[dict]:
        """Load user profile by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM user_profiles WHERE id = ?", (profile_id,)).fetchone()
            return dict(row) if row else None
    
    def update_user_profile(self, profile_id: int, profile_data: dict):
        """Update existing user profile"""
        now = int(datetime.now().timestamp())
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """UPDATE user_profiles SET 
                name = ?, communication_style = ?, response_format = ?, language = ?, 
                constraints = ?, preferences = ?, domain_expertise = ?, updated_at = ?
                WHERE id = ?""",
                (profile_data["name"], profile_data["communication_style"], profile_data["response_format"],
                 profile_data["language"], profile_data["constraints"], profile_data["preferences"],
                 profile_data["domain_expertise"], now, profile_id)
            )
            conn.commit()
    
    def list_user_profiles(self) -> list:
        """List all user profiles"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM user_profiles ORDER BY updated_at DESC").fetchall()
            return [dict(row) for row in rows]
    
    def link_session_to_profile(self, session_id: int, profile_id: int):
        """Link a session to a user profile"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute(
                "INSERT OR REPLACE INTO session_profiles (session_id, profile_id) VALUES (?, ?)",
                (session_id, profile_id)
            )
            conn.commit()
    
    def get_session_profile(self, session_id: int) -> Optional[int]:
        """Get profile ID linked to a session"""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT profile_id FROM session_profiles WHERE session_id = ?", (session_id,)).fetchone()
            return row[0] if row else None
    
    def delete_all_profiles(self):
        """Delete all user profiles"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("DELETE FROM user_profiles")
            conn.commit()
    
    def save_task_state(self, session_id: int, state: dict):
        """Save task state for a session"""
        now = int(datetime.now().timestamp())
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute(
                """INSERT OR REPLACE INTO task_states 
                (session_id, phase, step, total_steps, action_description, updated_at) 
                VALUES (?, ?, ?, ?, ?, ?)""",
                (session_id, state.get("phase"), state.get("step", 0), 
                 state.get("total_steps", 0), state.get("action_description", ""), now)
            )
            conn.commit()
    
    def load_task_state(self, session_id: int) -> Optional[dict]:
        """Load task state for a session"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT phase, step, total_steps, action_description FROM task_states WHERE session_id = ?",
                (session_id,)
            ).fetchone()
            return dict(row) if row else None
    
    def _execute(self, query: str, params: tuple = ()):
        """Execute a query and return cursor"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            cursor = conn.execute(query, params)
            conn.commit()
            return cursor
    
    def _fetch_all(self, query: str, params: tuple = ()):
        """Fetch all rows from a query"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, params)
            return cursor.fetchall()
