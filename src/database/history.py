import os
import sqlite3
from typing import List, Dict, Any, Tuple
from datetime import datetime

class QueryHistoryManager:
    """Manages persistence of generated query logs and saved favorite queries in a dedicated SQLite database."""
    
    def __init__(self, db_path: str = "sample_data/app_history.db"):
        self.db_path = db_path
        # Ensure directories exist
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """Initializes tables for schema logs and favorite queries."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # History log table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS query_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt TEXT NOT NULL,
                sql_query TEXT,
                success INTEGER, -- 1 for True, 0 for False
                execution_time_ms REAL,
                row_count INTEGER,
                error_message TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """)

            # Saved queries (favorites) table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS saved_queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                prompt TEXT NOT NULL,
                sql_query TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """)
            conn.commit()

    def log_query(self, prompt: str, sql_query: str, success: bool, 
                  execution_time_ms: float, row_count: int, error_message: str = None) -> None:
        """Logs a query execution entry to the history database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO query_history (prompt, sql_query, success, execution_time_ms, row_count, error_message, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (prompt, sql_query, 1 if success else 0, execution_time_ms, row_count, error_message, datetime.now().isoformat()))
            conn.commit()

    def get_recent_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieves a list of recent queries from the database logs."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
            SELECT id, prompt, sql_query, success, execution_time_ms, row_count, error_message, timestamp 
            FROM query_history 
            ORDER BY id DESC 
            LIMIT ?
            """, (limit,))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def save_favorite(self, name: str, prompt: str, sql_query: str) -> None:
        """Saves a query as a named favorite for easy retrieval."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO saved_queries (name, prompt, sql_query)
            VALUES (?, ?, ?)
            """, (name, prompt, sql_query))
            conn.commit()

    def get_favorites(self) -> List[Dict[str, Any]]:
        """Retrieves all saved favorite queries."""
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, prompt, sql_query, timestamp FROM saved_queries ORDER BY id DESC")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def delete_favorite(self, fav_id: int) -> None:
        """Deletes a favorite query by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM saved_queries WHERE id = ?", (fav_id,))
            conn.commit()
            
    def clear_history(self) -> None:
        """Clears all query history records."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM query_history")
            conn.commit()
