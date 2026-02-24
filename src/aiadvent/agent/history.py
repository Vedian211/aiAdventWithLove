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
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    model TEXT NOT NULL,
                    system_prompt TEXT,
                    last_updated TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                )
            """)
            conn.commit()
    
    def create_session(self, name: str, model: str, system_prompt: str = None) -> int:
        """Create a new session and return its ID"""
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO sessions (name, created_at, model, system_prompt, last_updated) VALUES (?, ?, ?, ?, ?)",
                (name, now, model, system_prompt, now)
            )
            conn.commit()
            return cursor.lastrowid
    
    def save_message(self, session_id: int, role: str, content: str):
        """Save a message to the session"""
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO messages (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                (session_id, role, content, now)
            )
            conn.execute(
                "UPDATE sessions SET last_updated = ? WHERE id = ?",
                (now, session_id)
            )
            conn.commit()
    
    def load_session(self, session_id: int) -> Optional[Dict]:
        """Load session metadata and all messages"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            session = conn.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
            
            if not session:
                return None
            
            messages = conn.execute(
                "SELECT role, content, timestamp FROM messages WHERE session_id = ? ORDER BY id",
                (session_id,)
            ).fetchall()
            
            return {
                "id": session["id"],
                "name": session["name"],
                "created_at": session["created_at"],
                "model": session["model"],
                "system_prompt": session["system_prompt"],
                "last_updated": session["last_updated"],
                "messages": [dict(msg) for msg in messages]
            }
    
    def list_sessions(self) -> List[Dict]:
        """List all sessions ordered by last updated"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            sessions = conn.execute(
                "SELECT id, name, created_at, last_updated, model FROM sessions ORDER BY last_updated DESC"
            ).fetchall()
            
            return [dict(session) for session in sessions]
    
    def delete_session(self, session_id: int):
        """Delete a session and all its messages"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            conn.commit()
    
    def update_session_name(self, session_id: int, name: str):
        """Update session name"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE sessions SET name = ? WHERE id = ?", (name, session_id))
            conn.commit()
