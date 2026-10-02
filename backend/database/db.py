"""
NeuroSeek AI — Database Layer
SQLite-based persistence with proper schema
"""

import sqlite3
import json
import datetime
from pathlib import Path
from typing import Optional


class Database:
    def __init__(self, db_path: str = "neuroseek.db"):
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                domain_id TEXT DEFAULT 'universal',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT DEFAULT '{}'
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT DEFAULT '{}',
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id TEXT PRIMARY KEY,
                message_id TEXT,
                domain_id TEXT,
                type TEXT NOT NULL,
                correction TEXT,
                context TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learning_memory (
                id TEXT PRIMARY KEY,
                domain_id TEXT,
                memory_type TEXT,
                content TEXT NOT NULL,
                frequency INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()

    def create_conversation(self, conv_id: str, title: str, domain_id: str = "universal") -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO conversations (id, title, domain_id)
                VALUES (?, ?, ?)
            ''', (conv_id, title, domain_id))
            conn.commit()
            return True
        except Exception:
            return False
        finally:
            conn.close()

    def get_conversations(self, limit: int = 50) -> list:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, title, domain_id, created_at, updated_at
            FROM conversations
            ORDER BY updated_at DESC
            LIMIT ?
        ''', (limit,))
        rows = cursor.fetchall()
        conn.close()
        return [
            {"id": r[0], "title": r[1], "domain_id": r[2], "created_at": r[3], "updated_at": r[4]}
            for r in rows
        ]

    def get_conversation(self, conv_id: str) -> Optional[dict]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM conversations WHERE id = ?', (conv_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                "id": row[0], "title": row[1], "domain_id": row[2],
                "created_at": row[3], "updated_at": row[4], "metadata": json.loads(row[5])
            }
        return None

    def update_conversation_title(self, conv_id: str, title: str) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE conversations SET title = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (title, conv_id))
        conn.commit()
        conn.close()
        return True

    def delete_conversation(self, conv_id: str) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM messages WHERE conversation_id = ?', (conv_id,))
        cursor.execute('DELETE FROM conversations WHERE id = ?', (conv_id,))
        conn.commit()
        conn.close()
        return True

    def add_message(self, msg_id: str, conv_id: str, role: str, content: str, metadata: dict = None) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO messages (id, conversation_id, role, content, metadata)
                VALUES (?, ?, ?, ?, ?)
            ''', (msg_id, conv_id, role, content, json.dumps(metadata or {})))
            cursor.execute('''
                UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?
            ''', (conv_id,))
            conn.commit()
            return True
        except Exception:
            return False
        finally:
            conn.close()

    def get_messages(self, conv_id: str) -> list:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, role, content, created_at, metadata
            FROM messages WHERE conversation_id = ?
            ORDER BY created_at ASC
        ''', (conv_id,))
        rows = cursor.fetchall()
        conn.close()
        return [
            {"id": r[0], "role": r[1], "content": r[2], "created_at": r[3], "metadata": json.loads(r[4])}
            for r in rows
        ]

    def add_feedback(self, fb_id: str, message_id: str, domain_id: str, fb_type: str, correction: str = None, context: str = None) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO feedback (id, message_id, domain_id, type, correction, context)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (fb_id, message_id, domain_id, fb_type, correction, context))
        conn.commit()
        conn.close()
        return True

    def get_learning_memory(self, domain_id: str = None) -> list:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        if domain_id:
            cursor.execute('''
                SELECT id, domain_id, memory_type, content, frequency
                FROM learning_memory WHERE domain_id = ?
                ORDER BY frequency DESC
            ''', (domain_id,))
        else:
            cursor.execute('''
                SELECT id, domain_id, memory_type, content, frequency
                FROM learning_memory ORDER BY frequency DESC
            ''')
        rows = cursor.fetchall()
        conn.close()
        return [
            {"id": r[0], "domain_id": r[1], "memory_type": r[2], "content": r[3], "frequency": r[4]}
            for r in rows
        ]

    def add_learning_memory(self, mem_id: str, domain_id: str, memory_type: str, content: str) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO learning_memory (id, domain_id, memory_type, content)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET frequency = frequency + 1, updated_at = CURRENT_TIMESTAMP
        ''', (mem_id, domain_id, memory_type, content))
        conn.commit()
        conn.close()
        return True

    def clear_learning_memory(self) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM learning_memory')
        conn.commit()
        conn.close()
        return True

    def get_setting(self, key: str) -> Optional[str]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None

    def set_setting(self, key: str, value: str) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = CURRENT_TIMESTAMP
        ''', (key, value, value))
        conn.commit()
        conn.close()
        return True

    def search_conversations(self, query: str) -> list:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DISTINCT c.id, c.title, c.domain_id, c.created_at
            FROM conversations c
            JOIN messages m ON c.id = m.conversation_id
            WHERE c.title LIKE ? OR m.content LIKE ?
            ORDER BY c.updated_at DESC LIMIT 20
        ''', (f'%{query}%', f'%{query}%'))
        rows = cursor.fetchall()
        conn.close()
        return [
            {"id": r[0], "title": r[1], "domain_id": r[2], "created_at": r[3]}
            for r in rows
        ]
