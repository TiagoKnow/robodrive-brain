import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MemorySystem:
    """Sistema de memória persistente com SQLite"""

    def __init__(self, db_path: str = "data/memories.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_database()

    def _init_database(self):
        """Inicializa tabelas SQLite"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS conversations
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           timestamp
                           DATETIME
                           DEFAULT
                           CURRENT_TIMESTAMP,
                           user_message
                           TEXT,
                           robot_response
                           TEXT,
                           context_tags
                           TEXT
                       )
                       ''')

        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS persons
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           name
                           TEXT
                           UNIQUE,
                           role
                           TEXT,
                           characteristics
                           TEXT,
                           first_seen
                           DATETIME,
                           last_seen
                           DATETIME
                       )
                       ''')

        cursor.execute('''
                       CREATE TABLE IF NOT EXISTS facts
                       (
                           id
                           INTEGER
                           PRIMARY
                           KEY
                           AUTOINCREMENT,
                           fact
                           TEXT
                           UNIQUE,
                           category
                           TEXT,
                           learned_at
                           DATETIME
                           DEFAULT
                           CURRENT_TIMESTAMP,
                           confidence
                           FLOAT
                           DEFAULT
                           1.0
                       )
                       ''')

        conn.commit()
        conn.close()
        logger.info(f"Banco de dados inicializado em: {self.db_path}")

    def save_conversation(self, user_message: str, robot_response: str, tags: List[str] = None):
        """Salva uma conversa"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        tags_str = json.dumps(tags) if tags else None

        cursor.execute('''
                       INSERT INTO conversations (user_message, robot_response, context_tags)
                       VALUES (?, ?, ?)
                       ''', (user_message, robot_response, tags_str))

        conn.commit()
        conn.close()
        logger.debug(f"Conversa salva: {user_message[:50]}...")

    def get_recent_context(self, limit: int = 10) -> List[Dict]:
        """Recupera conversas recentes para contexto"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
                       SELECT user_message, robot_response, timestamp
                       FROM conversations
                       ORDER BY timestamp DESC
                           LIMIT ?
                       ''', (limit,))

        rows = cursor.fetchall()
        conn.close()

        context = []
        for row in reversed(rows):
            context.append({"role": "user", "content": row[0]})
            context.append({"role": "assistant", "content": row[1]})

        return context

    def learn_person(self, name: str, characteristics: str, role: str = "visitante"):
        """Aprende sobre uma pessoa"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.now().isoformat()

        cursor.execute('''
            INSERT OR REPLACE INTO persons (name, role, characteristics, first_seen, last_seen)
            VALUES (?, ?, ?, COALESCE((SELECT first_seen FROM persons WHERE name=?), ?), ?)
        ''', (name.lower(), role, characteristics, name.lower(), now, now))

        conn.commit()
        conn.close()
        logger.info(f"Aprendi sobre {name}: {characteristics}")
        self.learn_fact(f"{name} é {role}", "persona")

    def learn_fact(self, fact: str, category: str = "geral"):
        """Aprende um fato novo"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                           INSERT
                           OR IGNORE INTO facts (fact, category)
                VALUES (?, ?)
                           ''', (fact, category))
            conn.commit()
            if cursor.rowcount > 0:
                logger.info(f"Fato aprendido: {fact}")
        except Exception as e:
            logger.error(f"Erro ao aprender fato: {e}")
        finally:
            conn.close()

    def get_all_facts(self) -> List[str]:
        """Recupera todos os fatos aprendidos"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT fact FROM facts ORDER BY learned_at DESC')
        rows = cursor.fetchall()
        conn.close()

        return [row[0] for row in rows]

    def get_known_persons(self) -> Dict:
        """Recupera pessoas conhecidas"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT name, role, characteristics FROM persons')
        rows = cursor.fetchall()
        conn.close()

        persons = {}
        for name, role, char in rows:
            persons[name] = {"role": role, "characteristics": char}

        return persons