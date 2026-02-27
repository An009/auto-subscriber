import sqlite3
from typing import List, Dict, Any
from .logger import logger

class Database:
    def __init__(self, db_path="results.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS jobs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        url TEXT NOT NULL,
                        status TEXT,
                        attempts INTEGER DEFAULT 0,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        error TEXT
                    )
                ''')
                conn.commit()
        except Exception as e:
            logger.error(f"Database initialization failed: {e}", exc_info=True)

    def insert_or_update_job(self, url: str, status: str, attempts: int, error: str = ""):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT id FROM jobs WHERE url = ?', (url,))
                row = cursor.fetchone()
                if row:
                    cursor.execute('''
                        UPDATE jobs SET status = ?, attempts = ?, error = ?, timestamp = CURRENT_TIMESTAMP
                        WHERE url = ?
                    ''', (status, attempts, error, url))
                else:
                    cursor.execute('''
                        INSERT INTO jobs (url, status, attempts, error)
                        VALUES (?, ?, ?, ?)
                    ''', (url, status, attempts, error))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to update job {url}: {e}", exc_info=True)

    def get_all_jobs(self) -> List[Dict[str, Any]]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM jobs ORDER BY timestamp DESC')
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to fetch jobs: {e}", exc_info=True)
            return []
